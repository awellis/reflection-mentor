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

from langroid.agent.base import Agent
from langroid.agent import Task
from langroid.agent.chat_agent import ChatAgent

from langroid.language_models.openai_gpt import OpenAIChatModel
from langroid.language_models.azure_openai import AzureConfig
from langroid.mytypes import Entity
from langroid.parsing.json import extract_top_level_json
from langroid.utils.configuration import settings
from langroid.utils.constants import DONE, NO_ANSWER, PASS, PASS_TO, SEND_TO, USER_QUIT
from langroid.utils.logging import RichFileLogger, setup_file_logger

from callbacks import TaskWithCustomLogger, CustomChainlitTaskCallbacks

from reflectionprompts import (
    mentor_message
)

from textwrap import dedent

settings.debug = True

callback_config = lr.ChainlitCallbackConfig(user_has_agent_name=False)

Responder = Entity | Type["Task"]

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
        interactive=True,
        done_if_no_response=[Entity.LLM]
    )

    mentor_task.set_color_log(False)

    cl.user_session.set("mentor_task", mentor_task)

    CustomChainlitTaskCallbacks(mentor_task, config=callback_config)
    await mentor_task.run_async()
    
@cl.on_message
async def on_message(message: cl.Message):
    mentor_task = cl.user_session.get("mentor_task")
    
    tasks = [
        mentor_task 
        ]

    for task in tasks:
        CustomChainlitTaskCallbacks(task, message, config=callback_config)

    await mentor_task.run_async(message.content)
    