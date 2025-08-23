"""Minimal Streamlit application for dataset generation.

This skeleton implements the first step of the new dataset generation tool.
Users can upload an exercise image, manage persistent rules and view placeholder
sections for prompt, code, video and chat to outline the forthcoming workflow.
"""

from __future__ import annotations

import streamlit as st
from PIL import Image


def main() -> None:
    """Run the Streamlit app."""
    st.set_page_config(layout="wide", page_title="Dataset Tool Skeleton")
    st.title("Dataset Generation Tool")

    # Maintain basic session state placeholders
    image: Image.Image | None = st.session_state.get("image")
    prompt: str = st.session_state.get("prompt", "")
    code: str = st.session_state.get("code", "")
    st.session_state.setdefault("chat", [])
    st.session_state.setdefault("rules", [])

    cols = st.columns(5)

    with cols[0]:
        st.header("Image")
        uploaded = st.file_uploader(
            "Upload exercise image", type=["png", "jpg", "jpeg"], label_visibility="collapsed"
        )
        if uploaded:
            image = Image.open(uploaded)
            st.session_state.image = image
        if image:
            st.image(image, caption="Uploaded image", use_column_width=True)

    with cols[1]:
        st.header("Prompt")
        prompt = st.text_area("", value=prompt, height=300, label_visibility="collapsed")
        st.session_state.prompt = prompt

    with cols[2]:
        st.header("Code")
        code = st.text_area("", value=code, height=300, label_visibility="collapsed")
        st.session_state.code = code

    with cols[3]:
        st.header("Video")
        st.info("Rendered video will appear here.")

    with cols[4]:
        st.header("Chat")
        chat_container = st.container()
        for message in st.session_state.chat:
            chat_container.chat_message(message["role"]).write(message["content"])
        user_message = st.chat_input("Send a message", key="chat_input")
        if user_message:
            st.session_state.chat.append({"role": "user", "content": user_message})
            chat_container.chat_message("user").write(user_message)

        st.subheader("Rules")
        new_rule = st.text_input("Add rule", key="rule_input")
        if st.button("Add Rule") and new_rule:
            st.session_state.rules.append(new_rule)
            st.session_state.rule_input = ""
            st.experimental_rerun()
        for i, rule in enumerate(list(st.session_state.rules)):
            cols_rule = st.columns([4, 1])
            with cols_rule[0]:
                st.text_input(
                    f"Rule {i + 1}", value=rule, key=f"rule_{i}", disabled=True
                )
            with cols_rule[1]:
                if st.button("✖", key=f"del_rule_{i}"):
                    st.session_state.rules.pop(i)
                    st.experimental_rerun()


if __name__ == "__main__":
    main()
