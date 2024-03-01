from operator import itemgetter

from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import Runnable, RunnablePassthrough, RunnableLambda
from langchain.schema.runnable.config import RunnableConfig
from langchain.memory import ConversationBufferMemory

from chainlit.types import ThreadDict
import chainlit as cl

from messagelogger import (
    setup_file_logger,
    LogMessage, 
    StudentLogMessage,
    MentorLogMessage
)

import json
# from datetime import datetime

SESSION_ID = "FJISMZ3242"


def setup_runnable():
    memory = cl.user_session.get("memory")
    model = AzureChatOpenAI(temperature = 0.2,
                            streaming=True,
                            # azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                            openai_api_version="2024-02-15-preview",
                            azure_deployment="gpt-4-32k",
                            )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a haiku writer. Ask me what to write about."),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{question}"),
        ]
    )

    runnable = (
        RunnablePassthrough.assign(
            history=RunnableLambda(memory.load_memory_variables) | itemgetter("history")
        )
        | prompt
        | model
        | StrOutputParser()
    )
    cl.user_session.set("runnable", runnable)


# @cl.password_auth_callback
# def auth():
#     return cl.User(identifier="test")


@cl.on_chat_start
async def on_chat_start():
    # logging.basicConfig(filename='logs/log_file.log', level=logging.INFO,
    # format='%(asctime)s - %(message)s')
    logger = setup_file_logger(SESSION_ID, f"logs/{SESSION_ID}.log", log_format=True)

    cl.user_session.set("memory", ConversationBufferMemory(return_messages=True))
    cl.user_session.set("logger", logger)

    setup_runnable()
    
    # memory = cl.user_session.get("memory")  # type: ConversationBufferMemory
    # print(memory.chat_memory)
    msg = cl.Message(content=f"Hi, how can I help you?", disable_feedback=True)
    await msg.send()


# @cl.on_chat_resume
# async def on_chat_resume(thread: ThreadDict):
#     memory = ConversationBufferMemory(return_messages=True)
#     root_messages = [m for m in thread["steps"] if m["parentId"] == None]
#     for message in root_messages:
#         if message["type"] == "USER_MESSAGE":
#             memory.chat_memory.add_user_message(message["output"])
#         else:
#             memory.chat_memory.add_ai_message(message["output"])

#     cl.user_session.set("memory", memory)

#     setup_runnable()


@cl.on_message
async def on_message(message: cl.Message):
    memory = cl.user_session.get("memory")
    runnable = cl.user_session.get("runnable")
    logger = cl.user_session.get("logger")

    # logger.student(message.content)

    res = cl.Message(content="")

    async for chunk in runnable.astream(
        {"question": message.content},
        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        await res.stream_token(chunk)

    await res.send()
    # logger.mentor(res.content)

    memory.chat_memory.add_user_message(message.content)
    memory.chat_memory.add_ai_message(res.content)
    # print(memory.chat_memory)
    # log_str = memory.to_json()
    # logger.student(message.content)
    # logger.mentor(res.content)
    
    # logger.debug(log_str)

    #TODO: use pydantic subclasses
    
    student_log_message = StudentLogMessage(
        # sender="student",
        message=message.content,
        # timestamp=datetime.now().isoformat()
    )
    logger.info(student_log_message.json())

    mentor_log_message = MentorLogMessage(
        # sender="mentor",
        message=res.content,  # Assuming res.content is a variable, replace it accordingly
        # timestamp=datetime.now().isoformat()
        )
    logger.info(mentor_log_message.json())