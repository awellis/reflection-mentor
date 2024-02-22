"""
Basic single-agent chat using ChainlitTaskCallbacks.
"""

from datetime import datetime
import logging

from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    cast,
)

import langroid as lr
import chainlit as cl
from langroid.agent.callbacks.chainlit import (
    add_instructions,
    ChainlitTaskCallbacks
)

from langroid.agent.base import Agent
from langroid.agent import Task
from langroid.agent.chat_agent import ChatAgent
from langroid.agent.chat_document import (
    ChatDocLoggerFields,
    ChatDocMetaData,
    ChatDocument,
)
from langroid.language_models.openai_gpt import OpenAIChatModel
from langroid.language_models.azure_openai import AzureConfig
from langroid.mytypes import Entity
from langroid.parsing.json import extract_top_level_json
from langroid.utils.configuration import settings
from langroid.utils.constants import DONE, NO_ANSWER, PASS, PASS_TO, SEND_TO, USER_QUIT
from langroid.utils.logging import RichFileLogger, setup_file_logger

# from reflectionprompts import (
#     mentor_message
# )
# from chainlitintegration import TaskWithCustomLogger, CustomChainlitTaskCallbacks

from textwrap import dedent

settings.debug = True

mentor_message = """
You are an expert in reflective writing and Socratic questioning, tutoring
bachelor's students. Your goal is to support students in reflecting on their
learning process throughout the semester. Write in English, unless specifically
asked to write in German. If using German, address the user with "du" and maintain a friendly
and informal tone. Always use 'ss' instead of 'ß'.

Start conversations with a greeting and a question regarding the topic of the
student's current lecture.

Do not let yourself be drawn into content explanations. Do not let yourself be
drawn into discussion about topics outside the learning process. 

Follow these principles to foster the learning process: 
- Ask open-ended questions to stimulate thinking. 
- Clarify key terms to ensure a shared understanding. 
- Encourage the provision of examples and evidence. 
- Challenge reasoning and encourage reevaluation of beliefs. 
- Summarize discussions and derive conclusions. 
- Reflect on the dialogue's effectiveness.

Adapt your strategy based on the student's responses: 
- For short "yes/no" answers, use targeted questions to deepen thinking. 
- For longer responses, switch to exploratory mode to promote creative writing.

Conversation plan: 
- Identify the topic with the student. 
- Support the student's self-assessment of their understanding. 
- Prepare for the next session.

Always encourage or correct based on the student's behavior (e.g., good
preparation, active listening, avoiding distractions).

Avoid long answers or content
explanations, focusing instead on the learning process. Keep the conversation
going with questions until the user says "exit."

Here are some example questions to guide the conversation. Do not use these verbatim, but adapt them to the specific context of the conversation.

## Checking understanding

- How well did you understand the topic? 
- Can you identify what was most difficult to understand? 
- Why was it more difficult for you?
- Was it easy to focus on the lecture or did you get distracted? 
- What distracted you?
- What are the learning goals for this class?
- Can you summarize the learning goals?
- What additional material would be helpful to study this topic? 
- How can you make sure you get access to these materials?

## Preparation for next session

- How will you prepare for the next lecture? 
- Will you change anything in the way you prepare for lectures?

## Toolbox of actions to use in conversation
Use the following to categorize the student's answers. You should encourage good
behaviour and discourage bad behaviour.

### Good student behavior:
#### Preparation phase
- read the notes from last week
- read the texts that were assigned
- read the slides before the lecture
- familiarize with key concepts if not addressed in the readings
- generate questions based on the pre-reading
- prepare your devices (print slides or download them)
- be in class early

#### Lecture phase
- listen actively, focus on the lecture, check your understanding of what is being said, think critically of what is being said
- pay attention to where the teacher is pointing to
- think about implications or applications
- if you get confused, ask the teacher or peers (afterwards)
- take notes, highlight important information
- think about connections, integrate new knowledge in your existing knowledge

#### Evaluation phase
- ask yourself if you could answer the learning objectives
- ask yourself if you understood the content, or if you need more information
- discuss the topic with friends, try to summarize what you’ve learned

### Bad student behavior:
#### Preparation phase
- don't know where to go
- having downloaded the wrong slides
- not reading the assigned texts


#### Lecture phase
- use social media or reading the news all the time
- listen only when it interests you
- playing games
- focusing on tics of the lecturer
- daydreaming
- talking to neighbors about unrelated stuff
- arriving late and/or leaving early

#### Evaluation phase
- no evaluation happens
- lack of evaluative questions

If the user talks about emotional or mental health issues, you should respond
with the message that you are not a mental health professional and that the user
should seek help from a professional.
"""

# If the user makes a request that is harmful, you should respond with a message that the request is not allowed and
# ask the user to make a different request.

Responder = Entity | Type["Task"]

USER_TIMEOUT = 60_000
SYSTEM = "System 🖥️"
LLM = "Mentor 🧘🏼‍♂️"
AGENT = "Agent <>"
YOU = "You"
ERROR = "Error 🚫"

class CustomChainlitTaskCallbacks(ChainlitTaskCallbacks):
    def _entity_name(
        self, entity: str, tool: bool = False, cached: bool = False
    ) -> str:
        """Construct name of entity to display as Author of a step"""
        tool_indicator = " =>  🛠️" if tool else ""
        cached = "(cached)" if cached else ""
        match entity:
            case "llm":
                model = self.agent.llm.config.chat_model
                return (
                    # self.agent.config.name + f"({LLM} {tool_indicator}){cached}"
                    self.agent.config.name
                )
            case "agent":
                return self.agent.config.name + f"({AGENT})"
            case "user":
                if self.config.user_has_agent_name:
                    return self.agent.config.name + f"({YOU})"
                else:
                    return YOU
            case _:
                return self.agent.config.name + f"({entity})"

class TaskWithCustomLogger(Task):
    def init(self, msg: None | str | ChatDocument = None) -> ChatDocument | None:
        """
        Initialize the task, with an optional message to start the conversation.
        Initializes `self.pending_message` and `self.pending_sender`.
        Args:
            msg (str|ChatDocument): optional message to start the conversation.

        Returns:
            (ChatDocument|None): the initialized `self.pending_message`.
            Currently not used in the code, but provided for convenience.
        """
        self.pending_sender = Entity.USER
        if isinstance(msg, str):
            self.pending_message = ChatDocument(
                content=msg,
                metadata=ChatDocMetaData(
                    sender=Entity.USER,
                ),
            )
        else:
            self.pending_message = msg
            if self.pending_message is not None and self.caller is not None:
                # msg may have come from `caller`, so we pretend this is from
                # the CURRENT task's USER entity
                self.pending_message.metadata.sender = Entity.USER

        self._show_pending_message_if_debug()

        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d-%H-%M-%S")

        if self.caller is not None and self.caller.logger is not None:
            self.logger = self.caller.logger
        else:
            self.logger = RichFileLogger(f"logs/{timestamp}-{self.name}.log", color=self.color_log)

        if self.caller is not None and self.caller.tsv_logger is not None:
            self.tsv_logger = self.caller.tsv_logger
        else:
            self.tsv_logger = setup_file_logger("tsv_logger", f"logs/{timestamp}-{self.name}.tsv")
            header = ChatDocLoggerFields().tsv_header()
            self.tsv_logger.info(f" \tTask\tResponder\t{header}")

        self.log_message(Entity.USER, self.pending_message)
        return self.pending_message

    def log_message(
        self,
        resp: Responder,
        msg: ChatDocument | None = None,
        mark: bool = False,
    ) -> None:
        """
        Log current pending message, and related state, for lineage/debugging purposes.

        Args:
            resp (Responder): Responder that generated the `msg`
            msg (ChatDocument, optional): Message to log. Defaults to None.
            mark (bool, optional): Whether to mark the message as the final result of
                a `task.step()` call. Defaults to False.
        """
        default_values = ChatDocLoggerFields().dict().values()
        msg_str_tsv = "\t".join(str(v) for v in default_values)
        if msg is not None:
            msg_str_tsv = msg.tsv_str()

        mark_str = "*" if mark else " "
        
        task_name = self.name if self.name != "" else "root"
        resp_color = "white" if mark else "red"
        resp_str = f"[{resp_color}] {resp} [/{resp_color}]"

        if msg is None:
            msg_str = f"{mark_str}({task_name}) {resp_str}"
        else:
            color = {
                Entity.LLM: "limegreen",
                Entity.USER: "steelblue",
                Entity.AGENT: "red",
                Entity.SYSTEM: "magenta",
            }[msg.metadata.sender]
            f = msg.log_fields()
            tool_type = f.tool_type.rjust(6)
            tool_name = f.tool.rjust(10)
            tool_str = f"{tool_type}({tool_name})" if tool_name != "" else ""
            sender = f"[{color}]" + str(f.sender_entity).rjust(10) + f"[/{color}]"
            sender_name = f.sender_name.rjust(10)
            recipient = "=>" + str(f.recipient).rjust(10)
            block = "X " + str(f.block or "").rjust(10)
            content = f"[{color}]{f.content}[/{color}]"
            msg_str = (
                f"{mark_str}({task_name}) "
                f"{resp_str} {sender}({sender_name}) "
                f"({recipient}) ({block}) {tool_str} {content}"
            )

        if self.logger is not None:
            self.logger.log(msg_str)
        if self.tsv_logger is not None:
            resp_str = str(resp)
            self.tsv_logger.info(f"{mark_str}\t{task_name}\t{resp_str}\t{msg_str_tsv}")


@cl.on_chat_start
async def on_chat_start():
    # await add_instructions(
    #     title="Single-Agent Reflection Chat",
    #     content=dedent("Hello...")
    # )

    llm_config = AzureConfig(
        chat_model=OpenAIChatModel.GPT4_TURBO,
        temperature=0.3,
    )
    config = lr.ChatAgentConfig(
        llm=llm_config)

    mentor_agent = lr.ChatAgent(config)
    mentor_task = TaskWithCustomLogger(
        mentor_agent,
        name="Mentor",
        system_message=mentor_message,
        interactive=True
    )

    mentor_task.set_color_log(False)

    cl.user_session.set("mentor_task", mentor_task)

    callback_config = lr.ChainlitCallbackConfig(user_has_agent_name=False)
    CustomChainlitTaskCallbacks(mentor_task, config=callback_config)
    await mentor_task.run_async()
    
@cl.on_message
async def on_message(message: cl.Message):
    mentor_task = cl.user_session.get("mentor_task")

    callback_config = lr.ChainlitCallbackConfig(user_has_agent_name=False)
    
    tasks = [
        mentor_task 
        ]

    for task in tasks:
        CustomChainlitTaskCallbacks(task, message, config=callback_config)

    await mentor_task.run_async(message.content)
    