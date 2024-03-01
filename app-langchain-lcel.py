from operator import itemgetter

from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory

from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable, RunnableLambda, RunnablePassthrough
from langchain.schema.runnable.config import RunnableConfig



import chainlit as cl

from reflectionprompts import (
    mentor_message
)

@cl.on_chat_start


async def on_chat_start():
    memory = ConversationBufferMemory(return_messages=True)
    memory.load_memory_variables({}) 
    model = ChatOpenAI(streaming=True, temperature=0.2)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful but slighly creepy assistant.",
            ),
            ("human", "{question}"),
        ]
    )
    runnable = (RunnablePassthrough.assign(
        history=RunnableLambda(memory.load_memory_variables) | itemgetter("history")
        )
        | prompt | model | StrOutputParser()
    )
    cl.user_session.set("runnable", runnable)
    cl.user_session.set("memory", memory)


@cl.on_message
async def on_message(message: cl.Message):
    runnable = cl.user_session.get("runnable") 
    memory = cl.user_session.get("memory")

    print("The user sent: ", message.content)
    msg = cl.Message(content="")

    async for chunk in runnable.astream(
        {"question": message.content},
        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        await msg.stream_token(chunk)
    print(msg.content)
    inputs = {"input": message.content}
    memory.save_context(inputs, {"output": msg.content})
    await msg.send()
