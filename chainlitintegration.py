from datetime import datetime
import logging

from langroid.agent.base import Agent
from langroid.agent import Task
from langroid.agent.callbacks.chainlit import ChainlitTaskCallbacks
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


USER_TIMEOUT = 60_000
SYSTEM = "System 🖥️"
LLM = "LLM 🧘🏼‍♂️"
AGENT = "Agent <>"
YOU = "User 👨🏼‍💻"
ERROR = "Error 🚫"

