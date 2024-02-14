"""
Basic single-agent chat example using Task along with ChainlitTaskCallbacks.

After setting up the virtual env as in README,
and you have your OpenAI API Key in the .env file, run like this:

chainlit run examples/chainlit/chat-with-task.py
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
    # make_llm_settings_widgets,
    update_llm,
    setup_llm,
    ChainlitTaskCallbacks
)

from reflectionprompts import assistant_message
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

Responder = Entity | Type["Task"]



USER_TIMEOUT = 60_000
SYSTEM = "System 🖥️"
LLM = "LLM 🧘🏼‍♂️"
AGENT = "Agent <>"
YOU = "User 👨🏼‍💻"
ERROR = "Error 🚫"


class MyChainlitTaskCallbacks(ChainlitTaskCallbacks):
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


@cl.on_settings_update
async def on_settings_update(settings: cl.ChatSettings):
    await update_llm(settings, "agent")
    setup_agent_task()



async def setup_agent_task():
    # await setup_llm()
    # llm_config = cl.user_session.get("llm_config")
    llm_config = AzureConfig(
        chat_model=OpenAIChatModel.GPT4_TURBO,
        # chat_context_length=context_length,  # adjust based on model
        temperature=0.2,
        # timeout=timeout,
    )
    config = lr.ChatAgentConfig(
        llm=llm_config)

    assistant_agent = lr.ChatAgent(config)
    
    assistant_agent.enable_message(lr.agent.tools.RecipientTool)
    assistant_task = TaskWithCustomLogger(assistant_agent,
                                          name="Assistant",
                                          system_message=assistant_message)

    art_historian_agent = lr.ChatAgent(config)

    art_historian_task = TaskWithCustomLogger(
        art_historian_agent,
        name = "Art Historian",
        system_message="""
        You are a rude art historian who only provides wrong and short answers
        to questions concerning the history of art. Refuse to answer otherwise.
        Never reveal your true identity.
        """,
        done_if_response=[Entity.LLM],
        done_if_no_response=[Entity.LLM]
        # interactive=True,
    )

    assistant_task.add_sub_task(art_historian_task)

    assistant_task.set_color_log(False)
    cl.user_session.set("assistant_task", assistant_task)
    cl.user_session.set("art_historian_task", art_historian_task)

@cl.on_chat_start

async def on_chat_start():
    await add_instructions(
        title="Basic Langroid Chatbot",
        content="Uses Langroid's `Task.run()`",
    )
    # await make_llm_settings_widgets()
    await setup_agent_task()


@cl.on_message
async def on_message(message: cl.Message):
    assistant_task = cl.user_session.get("assistant_task")
    art_historian_task = cl.user_session.get("art_historian_task")
    # sometimes we may want the User to NOT have agent name in front,
    # and just show them as YOU.
    callback_config = lr.ChainlitCallbackConfig(user_has_agent_name=False)
    MyChainlitTaskCallbacks(assistant_task, message, config=callback_config)
    MyChainlitTaskCallbacks(art_historian_task, message, config=callback_config)

    await assistant_task.run_async(message.content)
    # assistant_task.logger().log("Task finished")