"""
Basic single-agent chat example, without streaming.

After setting up the virtual env as in README,
and you have your OpenAI API Key in the .env file, run like this:

chainlit run examples/chainlit/chat.py
"""

import chainlit as cl
from langroid import ChatAgent, ChatAgentConfig


@cl.on_chat_start
async def on_chat_start():
    sys_msg = "You are a rude and unhelpful assistant. Be concise in your answers."
    config = ChatAgentConfig(
        system_message=sys_msg,
    ) 
    agent = ChatAgent(config)
    cl.user_session.set("agent", agent) 
    
    res = await cl.AskActionMessage(
    content="Pick an action!",
    actions=[
        cl.Action(name="continue", value="continue", label="✅ Continue"),
        cl.Action(name="cancel", value="cancel", label="❌ Cancel"),
    ],
    ).send()

    if res and res.get("value") == "continue":
        await cl.Message(
            content="Continue!",
        ).send()

    res2 = await cl.AskUserMessage(content="What is your name?", timeout=30).send()
    if res2:
        await cl.Message(
            content=f"Your name is: {res2['content']}.\nChainlit installation is working!\nYou can now start building your own chainlit apps!",
        ).send()          

    settings = await cl.ChatSettings(
        [
            Switch(id="Streaming", label="OpenAI - Stream Tokens", initial=True),
        ]
    ).send()
    value = settings["Streaming"]

    fig = go.Figure(
        data=[go.Bar(y=[2, 1, 3])],
        layout_title_text="An example figure",
    )
    elements = [cl.Plotly(name="chart", figure=fig, display="inline")]

    await cl.Message(content="This message has a chart", elements=elements).send()

@cl.on_message
async def on_message(message: cl.Message):
    agent: ChatAgent = cl.user_session.get("agent")
    msg = cl.Message(content="")

    response = await agent.llm_response_async(message.content)
    msg.content = response.content
    await msg.send()

    content = message.content
    print("message content:", content)


@cl.on_chat_end
def end():
    print("goodbye", cl.user_session.get("id"))