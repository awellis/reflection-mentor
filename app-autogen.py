import os
from typing import Dict, Optional, Union

import chainlit as cl

import autogen
from autogen import Agent, AssistantAgent, UserProxyAgent

## Start logging
STUDENT_ID = "GKJ-32478"
logging_session_id = autogen.runtime_logging.start(config={"dbname": f"{STUDENT_ID}-logs.db"})
print("Logging session ID: " + str(logging_session_id))


SYSTEM_MESSAGE = """
You are an expert in reflective writing and Socratic questioning, tutoring
bachelor's students. Your goal is to support students in reflecting on their
learning process throughout the semester. Write in German, unless specifically
asked to do so in English. Address the user with "du" and maintain a friendly
and informal tone. Use Swiss German orthography.

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

If the user makes a request that is in violation of the content filtering
policies, you should respond with a message that the request is not allowed and
ask the user to make a different request. Do not respond with the message "DO-NOT-KNOW".

If the user talks about emotional or mental health issues, you should respond
with the message that you are not a mental health professional and that the user
should seek help from a professional
"""

# Agents
USER_PROXY_NAME = "You"
MENTOR = "Mentor"


# Config list for AutoGen
config_list = [
    {
        "model": "gpt-4-turbo-preview",
    },
]
    
async def ask_helper(func, **kwargs):
    res = await func(**kwargs).send()
    while not res:
        res = await func(**kwargs).send()
    return res

class ChainlitAssistantAgent(AssistantAgent):
    """
    Wrapper for AutoGens Assistant Agent
    """
    def send(
        self,
        message: Union[Dict, str],
        recipient: Agent,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ) -> bool:
        cl.run_sync(
            cl.Message(
                content=f'*Sending message to "{recipient.name}":*\n\n{message}',
                author=self.name,
            ).send()
        )
        super(ChainlitAssistantAgent, self).send(
            message=message,
            recipient=recipient,
            request_reply=request_reply,
            silent=silent,
        )
class ChainlitUserProxyAgent(UserProxyAgent):
    """
    Wrapper for AutoGens UserProxy Agent. Simplifies the UI by adding CL Actions. 
    """
    def get_human_input(self, prompt: str) -> str:
        if prompt.startswith(
            "Provide feedback to chat_manager. Press enter to skip and use auto-reply"
        ):
            res = cl.run_sync(
                ask_helper(
                    cl.AskActionMessage,
                    content="Continue or provide feedback?",
                    actions=[
                        cl.Action(name="continue", value="continue", label="✅ Continue"),
                        cl.Action(name="feedback", value="feedback", label="💬 Provide feedback"),
                        cl.Action(name="exit", value="exit", label="🔚 Exit Conversation")
                    ],
                )
            )
            if res.get("value") == "continue":
                return ""
            elif res.get("value") == "feedback":
                # Prompt the user for feedback
                feedback_prompt = "Please provide your feedback:"
                feedback_reply = cl.run_sync(ask_helper(cl.AskUserMessage, content=feedback_prompt, timeout=60))
                if "content" in feedback_reply:
                    # Return the feedback content to be used as the next message
                    return feedback_reply["content"].strip()
                else:
                    print("No feedback provided.")
                    return ""
            elif res.get("value") == "exit":
                return "exit"
            else:
                # Handle other cases or errors
                return ""
        else:
            reply = cl.run_sync(ask_helper(cl.AskUserMessage, content=prompt, timeout=60))
            if "content" in reply:
                return reply["content"].strip()
            else:
                # Handle the absence of 'content' key gracefully
                print("No content received. Reply was:", reply)
                return ""

    def send(
        self,
        message: Union[Dict, str],
        recipient: Agent,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ):
        cl.run_sync(
            cl.Message(
                content=f'*Sending message to "{recipient.name}"*:\n\n{message}',
                author=self.name,
            ).send()
        )
        super(ChainlitUserProxyAgent, self).send(
            message=message,
            recipient=recipient,
            request_reply=request_reply,
            silent=silent,
        )


@cl.action_callback("confirm_action")
async def on_action(action: cl.Action):
    if action.value == "everything":
        content = "everything"
    elif action.value == "top-headlines":
        content = "top_headlines"
    else:
        await cl.ErrorMessage(content="Invalid action").send()
        return

    prev_msg = cl.user_session.get("url_actions")  # type: cl.Message
    if prev_msg:
        await prev_msg.remove_actions()
        cl.user_session.set("url_actions", None)

    await cl.Message(content=content).send()

    
@cl.on_chat_start
async def start():
  # Retrieve the 'env' dictionary from the user session
#   env_variables = cl.user_session.get("env")
  # Set OPENAI_API_KEY environment variable
#   os.environ["OPENAI_API_KEY"] = env_variables.get("OPENAI_API_KEY")

  try:
    llm_config = {"config_list": config_list, "seed": 42}
#     llm_config = {
#     "config_list": [
#         {"model": "gpt-4", "temperature": 0.7, "max_tokens": 100}
#     ],
#     "cache_seed": 42
# }

    mentor = ChainlitAssistantAgent(
        name="Mentor", llm_config=llm_config,
        system_message=SYSTEM_MESSAGE
    )

    user_proxy = ChainlitUserProxyAgent(
        name="User_Proxy",
        human_input_mode="ALWAYS",
        llm_config=llm_config,
        # max_consecutive_auto_reply=3,
        # is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
        code_execution_config=False,
        system_message="""
        User Proxy. Represents the user in the conversation.
        """
    )
    cl.user_session.set(USER_PROXY_NAME, user_proxy)
    cl.user_session.set(MENTOR, mentor)
    
    msg = cl.Message(content=f"""Hi, I'm here to guide you through a reflection exercise.""", author="Mentor")
    await msg.send()
    
  except Exception as e:
    print("Error: ", e)
    pass

@cl.on_message
async def run_conversation(message: cl.Message):
    llm_config = {"config_list": config_list, "seed": 42}
  #try:
    MESSAGE = message.content
    print("Task: ", MESSAGE)
    mentor = cl.user_session.get(MENTOR)
    user_proxy = cl.user_session.get(USER_PROXY_NAME)

    groupchat = autogen.GroupChat(agents=[user_proxy, mentor], messages=[], max_round=20, speaker_selection_method="round_robin")
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)
    
    print("Initiated GC messages... \nGC messages length: ", len(groupchat.messages))

    if len(groupchat.messages) == 0:
      message = f"""Hi, I'm your Socratic mentor."""
      await cl.Message(content=f"""Starting reflection...""").send()
      await cl.make_async(mentor.initiate_chat)( manager, message=message, )
    else:
      await cl.make_async(user_proxy.send)( manager, message=MESSAGE, )
      
#   except Exception as e:
#     print("Error: ", e)
#     pass


## End logging
autogen.runtime_logging.stop()

