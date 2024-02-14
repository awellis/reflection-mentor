"""
Use Langroid to detect problematic emotional content.

Run as follows:
python examples/emotion-detection.py
"""

import typer

import langroid as lr

app = typer.Typer()

lr.utils.logging.setup_colored_logging()
    
NO_ANSWER = lr.utils.constants.NO_ANSWER

def chat() -> None:
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
        system_message="""
        You will have a conversation with the user. Start by asking the user
        what they would like to talk about.
        However, you should only talk about positive things, and you you do talk
        about negative feelings. Therefore, you first send the message to the
        emotion detector agent, and only respond to the user if the emotion
        detector says it's ok to respond.
        """,
        llm_delegate=True,
        single_round=False
    )
    emotion_detector_agent = lr.ChatAgent(config)
    emotion_detector_task = lr.Task(
        emotion_detector_agent,
        name="Emotion detector",
        system_message="""
        You will receive a message, and you have to detect if it is about negative feelings.
        If detect negative feelings, return the message "NEGATIVE EMOTION
        DETECTED". If you can't detect negative feelings, return the message "OK".
        """,
        llm_delegate=False,
        single_round=True
        )
    processor_task.add_sub_task(emotion_detector_task)
    processor_task.run()


@app.command()
def main(
        debug: bool = typer.Option(False, "--debug", "-d", help="debug mode"),
        no_stream: bool = typer.Option(False, "--nostream", "-ns", help="no streaming"),
        nocache: bool = typer.Option(False, "--nocache", "-nc", help="don't use cache"),
) -> None:
    lr.utils.configuration.set_global(
        lr.utils.configuration.Settings(
            debug=debug,
            cache=not nocache,
            stream=not no_stream,
        )
    )
    chat()

if __name__ == "__main__":
    app()
