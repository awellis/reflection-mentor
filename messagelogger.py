import os
import logging
from datetime import datetime

from pydantic import BaseModel, Field

class LogMessage(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    sender: str
    message: str

class StudentLogMessage(LogMessage):
    sender: str = "student"
    message: str

class MentorLogMessage(LogMessage):
    sender: str = "mentor"
    message: str


# from functools import partial, partialmethod

# logging.MENTOR = 4
# logging.addLevelName(logging.MENTOR, 'MENTOR')
# logging.Logger.mentor = partialmethod(logging.Logger.log, logging.MENTOR)
# logging.mentor = partial(logging.log, logging.MENTOR)

# logging.STUDENT = 5
# logging.addLevelName(logging.STUDENT, 'STUDENT')
# logging.Logger.student = partialmethod(logging.Logger.log, logging.STUDENT)
# logging.student = partial(logging.log, logging.STUDENT)


def setup_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """
    Set up a logger of module `name` at a desired level.
    Args:
        name: module name
        level: desired logging level
    Returns:
        logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

def setup_file_logger(
    name: str,
    filename: str,
    append: bool = False,
    log_format: bool = False,
    propagate: bool = False,
) -> logging.Logger:
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    file_mode = "a" if append else "w"
    logger = setup_logger(name)
    handler = logging.FileHandler(filename, mode=file_mode)
    handler.setLevel(logging.DEBUG)
    if log_format:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    else:
        formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = propagate
    return logger
