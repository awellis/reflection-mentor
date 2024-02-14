from openai import AsyncOpenAI

from chainlit.playground.providers import ChatOpenAI
import chainlit as cl

client = AsyncOpenAI(api_key="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")

template = "Hello, {name}!"
inputs = {"name": "John"}

settings = {
    "model": "gpt-3.5-turbo",
    "temperature": 0,
    # ... more settings
}


@cl.step(type="llm")
async def call_llm():
    generation = cl.ChatGeneration(
        provider=ChatOpenAI.id,
        inputs=inputs,
        settings=settings,
        messages=[
            cl.GenerationMessage(
                template=template, formatted=template.format(**inputs), role="assistant"
            ),
        ],
    )

    # Make the call to OpenAI
    response = await client.chat.completions.create(
        messages=[m.to_openai() for m in generation.messages], **settings
    )

    generation.completion = response.choices[0].message.content

    # Add the generation to the current step
    cl.context.current_step.generation = generation

    return generation.completion


@cl.on_chat_start
async def start():
    await call_llm()
