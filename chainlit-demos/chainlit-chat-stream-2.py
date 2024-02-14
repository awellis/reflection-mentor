import chainlit as cl
import langroid as lr 
from langroid.utils.configuration import settings
import re
import sys
import asyncio

settings.stream = True

class ContinuousCaptureStream:
    """
    Capture stdout in a stream.
    This allows capturing of streaming output that would normally be printed to stdout,
    e.g. streaming tokens coming from OpenAI's API.
    """
    def __init__(self):
        self.content = ""
        self.new_content_event = asyncio.Event()
        self.is_finished = False  # Flag to indicate completion

    def write(self, data):
        self.content += data
        self.new_content_event.set()

    def flush(self):
        pass

    async def get_new_content(self):
        await self.new_content_event.wait()
        self.new_content_event.clear()
        new_content, self.content = self.content, ""
        return new_content

    def set_finished(self):
        self.is_finished = True
        self.new_content_event.set()

def strip_ansi_codes(text):
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9A\x9C-\x9F]|[\x1A-\x1C\x1E-\x1F])+\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

@cl.on_chat_start
async def on_chat_start():
    # sys_msg = """
    # You will have a conversation with the user. Always start by asking the user
    # what they would like to talk about.
    # However, you should only talk about positive things; do not talk
    # about negative feelings. If the user wants to discuss negative feelings,
    # respond by saying that you cannot provide help.
    # """
    sys_msg = """
    You are a rude and unhelpful assistant. Always speak like a medieval
    peasant. If you think the user is talking about negative feelings, send the
    message to the emotion detector agent.
    """
    sys_msg_2 = """
    You are an emotion detector. You will receive a message, and you have to
    detect if it is about negative feelings. It it is, return the message: NEGATIVE.
    """
    config = lr.ChatAgentConfig(
        llm = lr.language_models.OpenAIGPTConfig(
            chat_model = lr.language_models.OpenAIChatModel.GPT4,
        ),
        vecdb=None
    )
    processor_agent = lr.ChatAgent(config)
    processor_task = lr.Task(
        processor_agent,
        name="Processor",
        system_message=sys_msg,
        llm_delegate=True,
        single_round=False
    )
    emotion_agent = lr.ChatAgent(config)
    emotion_task = lr.Task(
        emotion_agent,
        name="EmotionDetector",
        system_message=sys_msg_2,
        llm_delegate=True,
        single_round=False
    )
    processor_task.add_sub_task(emotion_task)
    cl.user_session.set("processor_task", processor_task)

@cl.on_message
async def on_message(message: cl.Message):
    processor_task: lr.Task = cl.user_session.get("processor_task")
    msg = cl.Message(content="")
    await msg.send()

    capture_stream = ContinuousCaptureStream()
    original_stdout = sys.stdout
    sys.stdout = capture_stream

    # Run response() in a separate thread or as a non-blocking call
    asyncio.create_task(run_response(processor_task, message, capture_stream))

    while not capture_stream.is_finished:
        new_output = await capture_stream.get_new_content()
        new_output = strip_ansi_codes(new_output)
        if new_output:
            await msg.stream_token(new_output)

 # Restore original stdout when done
    sys.stdout = original_stdout

    await msg.update()

async def run_response(task: lr.Task, message: cl.Message, stream):
    msg = task.run(message.content)
    await task.responders_async(msg) 
    stream.set_finished()
