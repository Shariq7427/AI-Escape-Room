"""AI Escape Room - Version 2 (reliable): Python rules + LLM narration."""
import json
from pathlib import Path

import streamlit as st

import llm
from game_state import apply_action, new_state

CFG = json.loads((Path(__file__).parent / "game_config.json").read_text(encoding="utf-8"))

st.set_page_config(page_title="AI Escape Room - V2", page_icon="🔐")
st.title("🔐 AI Escape Room (Version 2 - Reliable)")

if not llm.API_KEY:
    st.error("GEMINI_API_KEY not found. Copy .env.example to .env and add your key.")
    st.stop()


def init_game():
    st.session_state.state = new_state()
    st.session_state.messages = [{"role": "assistant", "content": CFG["intro"]}]


if "state" not in st.session_state:
    init_game()

state = st.session_state.state

with st.sidebar:
    st.header("Controls")
    if st.button("🔄 Restart game"):
        init_game()
        st.rerun()
    st.subheader("🎒 Inventory")
    st.write(", ".join(state["inventory"]) or "empty")
    st.subheader("Progress")
    st.write(f"{'✅' if 'bookshelf' in state['examined'] else '⬜'} Found the digits")
    st.write(f"{'✅' if state['drawer_open'] else '⬜'} Drawer opened")
    st.write(f"{'✅' if state['painting_open'] else '⬜'} Painting compartment opened")
    st.write(f"{'✅' if state['escaped'] else '⬜'} Escaped")
    with st.expander("Game state (debug)"):
        st.json(state)
    st.caption(f"Model: {llm.MODEL}")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if state["escaped"]:
    st.success("🎉 You escaped the library! Press Restart to play again.")
elif prompt := st.chat_input("What do you do?"):
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        try:
            intent = llm.parse_intent(prompt)
        except Exception as e:
            st.error(f"Game Master unavailable, please try again: {e}")
            st.stop()
        result = apply_action(state, CFG, intent)  # Python decides
        try:
            reply = llm.narrate(prompt, result)  # LLM only describes
        except Exception:
            reply = result["facts"]  # graceful fallback: game still works
        st.markdown(reply)
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()