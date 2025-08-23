"""Streamlit interface for viewing Google Drive images and generated prompts.

This app processes one image at a time from the configuration in
``tools/dataset_builder/images_config.json``.  Each image is downloaded,
passed to ``generate_prompt_from_image`` (currently a stub) and displayed
alongside the generated description and learning objectives.  Results are
appended to ``datasets/prompts_only.jsonl`` and key actions are logged
via ``log_event`` for traceability.

Code generation, video rendering and chat refinement are intentionally
left as placeholders for future development.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

import streamlit as st

from tools.dataset_builder.prompt_generator import (
    append_record,
    download_image,
    generate_prompt_from_image,
    list_images_in_folder,
)
from tools.log_utils import log_event

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "tools" / "dataset_builder" / "images_config.json"
OUTPUT_FILE = REPO_ROOT / "datasets" / "prompts_only.jsonl"


def load_urls() -> List[str]:
    """Return the list of image URLs from the configuration file."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    urls: List[str] = []
    if isinstance(data, dict):
        urls.extend(data.get("images", []))
        folder = data.get("folder_url") or data.get("folder_id")
        if folder:
            api_key = os.getenv("GOOGLE_API_KEY")
            urls.extend(list_images_in_folder(folder, api_key))
    else:
        urls.extend(data)
    return urls


def main() -> None:
    st.title("Dataset Prompt Viewer")
    urls = load_urls()

    if "index" not in st.session_state:
        st.session_state.index = 0

    total = len(urls)
    current = st.session_state.index

    if current >= total:
        st.success("All images processed")
        st.stop()

    st.write(f"Image {current + 1} / {total}")
    st.progress(current / total)

    # If an image has not yet been processed, offer to generate its prompt
    if "last_path" not in st.session_state:
        if st.button("Generate prompt for current image"):
            url = urls[current]
            try:
                path = download_image(url)
                with open(path, "rb") as img_f:
                    result = generate_prompt_from_image(img_f.read())
                record = {
                    "image_path": path,
                    "description": result["description"],
                    "objectives": result["objectives"],
                    "model_used": result.get("model_used", "placeholder-model"),
                }
                append_record(record, str(OUTPUT_FILE))
                st.session_state.last_path = path
                st.session_state.last_result = result
                log_event("prompt_generated", Path(path).name)
            except Exception as e:  # pragma: no cover - defensive
                st.error(f"Failed to process image: {e}")
                log_event("prompt_error", f"{url}: {e}")
    else:
        col_img, col_prompt = st.columns(2)
        with col_img:
            st.image(st.session_state.last_path, caption="Downloaded image")
        with col_prompt:
            st.subheader("Description")
            st.write(st.session_state.last_result["description"])
            st.subheader("Objectives")
            for obj in st.session_state.last_result["objectives"]:
                st.write(f"- {obj}")

            approve = st.button("Approve")
            skip = st.button("Skip")

        if approve or skip:
            action = "prompt_approved" if approve else "prompt_skipped"
            log_event(action, Path(st.session_state.last_path).name)
            st.session_state.index += 1
            st.session_state.pop("last_path")
            st.session_state.pop("last_result")
            st.experimental_rerun()

    st.write("---")
    st.info(
        "Code generation, video rendering and chat refinement will be added in future steps."
    )


if __name__ == "__main__":  # pragma: no cover
    main()
