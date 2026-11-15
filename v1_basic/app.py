"""AI Escape Room - Version 1 (basic LLM Game Master).

The LLM alone acts as Game Master. It knows the rules and solutions through
the system prompt and remembers the game through the chat history.
"""
import os
import time

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

ESCAPE_TOKEN = "[ESCAPED]"

SYSTEM_PROMPT = f"""You are the Game Master of a text-based escape room game.
The player wakes up locked inside an old library. Stay in character, be
atmospheric but concise (max 4 sentences per reply).

ROOM OBJECTS (only these exist): desk, bookshelf, painting, locked drawer, door.

SECRET GAME DESIGN (never reveal directly; reveal clues only when the player
examines the right object):
- Desk: contains a note saying "Only the books bound in red matter."
- Bookshelf: four red-spined books stand out. Each contains a handwritten
  digit: 3, 7, 1, 9 (in shelf order). Drawer code = 3719.
- Locked drawer: opens only with code 3719. Inside: a small brass key and a
  torn note saying "The frame remembers what the eyes forget."
- Painting: a landscape with a locked compartment in its frame. The brass key
  opens it. Inside is a card with the number 6284.
- Door: secured by a four-digit code. Correct code = 6284.

RULES:
- The player must find clues in order: books -> drawer -> key -> painting -> door.
- Do not reveal codes or solutions unless the player discovers them in-game.
- Track what the player has found and stay consistent.
- When the player enters the correct door code 6284, describe their escape and
  end your message with the exact token {ESCAPE_TOKEN}.
"""

INTRO = (
    "You wake up on a cold wooden floor in a dusty library. The door is locked "
    "with a four-digit code. You see a desk, a bookshelf, a painting and a "
    "locked drawer.\n\n"
    "**How to play:** type what you want to do in natural language, e.g. "
    "*'examine the bookshelf'* or *'try 1234 on the door'*. "
    "Use the sidebar to restart."
)

st.set_page_config(page_title="AI Escape Room - V1", page_icon="🔐")
st.title("🔐 AI Escape Room (Version 1)")

if not API_KEY:
    st.error("GEMINI_API_KEY not found. Copy .env.example to .env and add your key.")
    st.stop()

client = genai.Client(
    api_key=API_KEY,
    http_options=types.HttpOptions(timeout=30000),  # 30 s
)


def init_game():
    st.session_state.messages = [{"role": "assistant", "content": INTRO}]
    st.session_state.escaped = False


def ask_game_master(messages):
    """Send the conversation (without the static intro) to Gemini, with retries."""
    contents = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part(text=m["content"])],
        )
        for m in messages[1:]  # skip the intro, history must start with the user
    ]
    last_error = None
    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT, temperature=0.7
                ),
            )
            return response.text or "..."
        except Exception as e:
            last_error = e
            if "503" in str(e) or "429" in str(e):  # busy / rate limited
                time.sleep(2 ** attempt)  # wait 1s, 2s, 4s, 8s
                continue
            raise
    raise last_error


if "messages" not in st.session_state:
    init_game()

with st.sidebar:
    st.header("Controls")
    if st.button("🔄 Restart game"):
        init_game()
        st.rerun()
    st.caption(f"Model: {MODEL}")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if st.session_state.escaped:
    st.success("🎉 You escaped the library! Press Restart to play again.")
elif prompt := st.chat_input("What do you do?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            reply = ask_game_master(st.session_state.messages)
        except Exception as e:
            st.session_state.messages.pop()  # remove the unanswered user message
            st.error(f"Game Master unavailable, please try again: {e}")
            st.stop()
        if ESCAPE_TOKEN in reply:
            st.session_state.escaped = True
            reply = reply.replace(ESCAPE_TOKEN, "").strip()
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    if st.session_state.escaped:
        st.rerun()