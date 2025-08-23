"""Streamlit application for generating Manim datasets from exercise images.

This app provides a single–page interface with five adjacent sections:
Image, Prompt, Code, Video and Chat.  It orchestrates calls to the existing
Flask API (code generation, chat refinement and video rendering) and persists
approved sessions as structured dataset records.

The implementation focuses on a simple, intuitive workflow and keeps all
state inside ``st.session_state``.  Model calls are abstracted into helper
functions so different providers can be swapped out easily.
"""

from __future__ import annotations

import base64
from datetime import datetime
import os
import uuid
from typing import Dict, List, Any

import requests
import streamlit as st

from tools.dataset_builder.dataset_writer import DatasetRecord, write_record

API_URL = os.getenv("API_URL", "http://localhost:5000")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log_event(action: str, details: str) -> None:
    """Append an entry to ``logs/progress.md`` with a timestamp."""
    os.makedirs("logs", exist_ok=True)
    with open("logs/progress.md", "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()}\t{action}\t{details}\n")


def describe_image(image_bytes: bytes, rules: List[str]) -> Dict[str, Any]:
    """Call a multimodal model to describe the image.

    This function is currently a placeholder.  It demonstrates how an image
    could be sent to a multimodal endpoint.  Developers can replace the body
    with a real model call (OpenAI, Anthropic, HuggingFace, ...).
    """

    _ = image_bytes, rules  # unused in placeholder
    return {
        "description": "Describe the exercise shown in the image.",
        "objectives": ["Identify shapes", "Apply geometry rules"],
        "model": "placeholder-vision"
    }


def generate_code(prompt: str, rules: List[str]) -> Dict[str, Any]:
    """Generate Manim code by calling the Flask API."""
    payload = {"prompt": prompt + "\n" + "\n".join(rules), "model": "gpt-4o"}
    resp = requests.post(f"{API_URL}/v1/code/generation", json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return {"code": data.get("code", ""), "model": "gpt-4o"}


def render_video(code: str) -> str:
    """Render the provided code through the video rendering API."""
    payload = {"code": code, "file_class": "GenScene", "stream": False}
    resp = requests.post(f"{API_URL}/v1/video/rendering", json=payload, timeout=300)
    resp.raise_for_status()
    data = resp.json()
    return data.get("video_url", "")


def refine_chat(message: str, context: Dict[str, Any], rules: List[str]) -> Dict[str, str]:
    """Refine prompt or code based on a chat message using the API.

    The chat generation endpoint streams responses as Server Sent Events.  This
    helper collects the streamed text into a single message string.  The
    ``context`` dictionary is expected to contain the current ``prompt``,
    ``code`` and the ``chat_history`` so far.  ``rules`` are appended as a
    global prompt to guide the model.
    """

    history = context.get("chat_history", [])
    payload = {
        "messages": history + [{"role": "user", "content": message}],
        "prompt": f"Prompt:\n{context.get('prompt', '')}\n\nCode:\n{context.get('code', '')}",
        "globalPrompt": "\n".join(rules),
        "engine": "openai",
        "model": "gpt-4o",
    }

    resp = requests.post(
        f"{API_URL}/v1/chat/generation", json=payload, stream=True, timeout=60
    )
    resp.raise_for_status()

    chunks: List[str] = []
    for line in resp.iter_lines():
        if not line:
            continue
        if line.startswith(b"data: "):
            content = line[len(b"data: "):].decode("utf-8")
            if content.strip() == "[DONE]":
                break
            chunks.append(content)

    return {"message": "".join(chunks), "model": "gpt-4o"}


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def reset_session() -> None:
    """Clear session state to start a new exercise."""
    for key in [
        "image_path", "prompt", "code", "video_url", "chat_history",
        "rules", "session_active", "checkpoints", "model_metadata",
    ]:
        st.session_state.pop(key, None)


# ---------------------------------------------------------------------------
# Streamlit layout
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(layout="wide", page_title="Generative Manim Dataset Tool")
    st.title("Dataset Generation Tool")

    if "session_active" not in st.session_state:
        st.session_state.session_active = False
    if "rules" not in st.session_state:
        st.session_state.rules = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "checkpoints" not in st.session_state:
        st.session_state.checkpoints = []
    if "model_metadata" not in st.session_state:
        st.session_state.model_metadata = {}

    cols = st.columns(5)

    # ------------------------------------------------------------------ Image
    with cols[0]:
        st.subheader("Image")
        disabled = st.session_state.session_active
        uploaded = st.file_uploader("Upload", type=["png", "jpg"], disabled=disabled)
        if uploaded and not st.session_state.session_active:
            st.session_state.session_active = True
            img_bytes = uploaded.read()
            image_path = os.path.join("uploads", f"{uuid.uuid4()}.png")
            os.makedirs("uploads", exist_ok=True)
            with open(image_path, "wb") as f:
                f.write(img_bytes)
            st.session_state.image_path = image_path
            desc = describe_image(img_bytes, st.session_state.rules)
            st.session_state.prompt = desc["description"]
            st.session_state.model_metadata["vision_model"] = desc.get("model")
            st.image(image_path)
            log_event("image_upload", image_path)
        elif st.session_state.get("image_path"):
            st.image(st.session_state.image_path)

    # --------------------------------------------------------------- Prompt
    with cols[1]:
        st.subheader("Prompt")
        st.session_state.prompt = st.text_area(
            "Prompt", value=st.session_state.get("prompt", ""), height=300
        )
        if st.button("Generate Code"):
            result = generate_code(st.session_state.prompt, st.session_state.rules)
            st.session_state.code = result["code"]
            st.session_state.model_metadata["code_model"] = result.get("model")
            log_event("code_generation", "")

    # ------------------------------------------------------------------ Code
    with cols[2]:
        st.subheader("Code")
        st.session_state.code = st.text_area(
            "Code", value=st.session_state.get("code", ""), height=300
        )
        if st.button("Render Video"):
            if st.session_state.code:
                video_url = render_video(st.session_state.code)
                st.session_state.video_url = video_url
                log_event("video_render", video_url)

        if st.button("Create Checkpoint"):
            cp = {
                "name": f"cp-{len(st.session_state.checkpoints) + 1}",
                "prompt": st.session_state.get("prompt", ""),
                "code": st.session_state.get("code", ""),
                "video_url": st.session_state.get("video_url", ""),
                "rules": list(st.session_state.rules),
            }
            st.session_state.checkpoints.append(cp)
            log_event("checkpoint", cp["name"])

    # ------------------------------------------------------------------ Video
    with cols[3]:
        st.subheader("Video")
        if st.session_state.get("video_url"):
            st.video(st.session_state.video_url)

        if st.session_state.checkpoints:
            names = [cp["name"] for cp in st.session_state.checkpoints]
            idx = st.selectbox("Revert to", options=range(len(names)), format_func=lambda i: names[i])
            if st.button("Revert"):
                cp = st.session_state.checkpoints[idx]
                st.session_state.prompt = cp["prompt"]
                st.session_state.code = cp["code"]
                st.session_state.video_url = cp["video_url"]
                st.session_state.rules = cp["rules"]
                log_event("revert", cp["name"])
                st.experimental_rerun()

    # -------------------------------------------------------------------- Chat
    with cols[4]:
        st.subheader("Chat")
        for msg in st.session_state.chat_history:
            st.markdown(f"**{msg['role']}:** {msg['content']}")
        user_msg = st.text_input("Message", key="chat_input")
        if st.button("Send", key="chat_send") and user_msg:
            st.session_state.chat_history.append({"role": "user", "content": user_msg})
            response = refine_chat(user_msg, st.session_state, st.session_state.rules)
            st.session_state.chat_history.append({"role": "assistant", "content": response["message"]})
            st.session_state.model_metadata["chat_model"] = response.get("model")
            log_event("chat", user_msg)
            st.experimental_rerun()

        # Rule management
        st.markdown("### Rules")
        new_rule = st.text_input("Add rule", key="rule_input")
        if st.button("Add Rule") and new_rule:
            st.session_state.rules.append(new_rule)
            log_event("rule_added", new_rule)
            st.experimental_rerun()
        for i, rule in enumerate(st.session_state.rules):
            st.markdown(f"{i+1}. {rule}")

        if st.button("Approve"):
            record = DatasetRecord(
                image_path=st.session_state.get("image_path", ""),
                prompt_final=st.session_state.get("prompt", ""),
                code_final=st.session_state.get("code", ""),
                video_path=st.session_state.get("video_url", ""),
                rules_applied=st.session_state.rules,
                chat_history=st.session_state.chat_history,
                model_metadata=st.session_state.model_metadata,
                timestamp=datetime.utcnow().isoformat(),
                user_id=st.session_state.get("user_id", "anonymous"),
            )
            write_record(record)
            log_event("approved", st.session_state.get("image_path", ""))
            reset_session()
            st.experimental_rerun()

        if st.button("Discard"):
            log_event("discarded", st.session_state.get("image_path", ""))
            reset_session()
            st.experimental_rerun()


if __name__ == "__main__":
    main()
