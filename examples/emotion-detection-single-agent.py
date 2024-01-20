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
        about negative feelings. If the user wants to discuss negative feelings,
        tell the user that you cannot provide help.
        """,
        llm_delegate=True,
        single_round=False
    )
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
