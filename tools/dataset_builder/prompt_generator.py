"""Dataset prompt generation utilities.

This module implements the first stage of the dataset generation
workflow.  It downloads exercise images from public Google Drive
links, generates a descriptive prompt (stubbed for now) and persists
the results in a JSON Lines file.  All major actions are logged via
``log_event`` for traceability.

Future phases will extend this with code generation, video rendering
and chat refinement.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List

import requests

try:
    from tools.log_utils import log_event
except ModuleNotFoundError:  # pragma: no cover - allow running as script
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from log_utils import log_event


def download_image(url: str, download_dir: str = "downloads") -> str:
    """Download an image from *url* to *download_dir*.

    The file is saved with a unique name to avoid collisions.  The
    function logs the ``image_download`` action and returns the local
    file path.  Any ``requests`` exceptions are propagated to the
    caller.
    """
    os.makedirs(download_dir, exist_ok=True)
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    ext = os.path.splitext(url)[1] or ".png"
    filename = f"{uuid.uuid4()}{ext}"
    path = os.path.join(download_dir, filename)
    with open(path, "wb") as f:
        f.write(resp.content)
    log_event("image_download", filename)
    return path


def extract_drive_id(url_or_id: str) -> str:
    """Extract the Google Drive file or folder ID from ``url_or_id``."""
    match = re.search(r"/folders/([\w-]+)", url_or_id)
    if match:
        return match.group(1)
    match = re.search(r"/d/([\w-]+)", url_or_id)
    if match:
        return match.group(1)
    return url_or_id


def list_images_in_folder(folder_url_or_id: str, api_key: str | None = None) -> List[str]:
    """Return image download URLs for all files in a Drive folder tree.

    Parameters
    ----------
    folder_url_or_id:
        Public folder URL or ID.
    api_key:
        Optional Google API key stored in ``GOOGLE_API_KEY``.  If the key is
        missing or the request fails, an empty list is returned and the error
        is logged.
    """

    folder_id = extract_drive_id(folder_url_or_id)
    base_url = "https://www.googleapis.com/drive/v3/files"

    def _list(fid: str) -> List[str]:
        urls: List[str] = []
        page_token = None
        while True:
            params = {
                "q": f"'{fid}' in parents and trashed=false",
                "fields": "nextPageToken, files(id, mimeType)",
                "pageSize": 1000,
                "supportsAllDrives": True,
            }
            if api_key:
                params["key"] = api_key
            if page_token:
                params["pageToken"] = page_token
            try:
                resp = requests.get(base_url, params=params, timeout=60)
                resp.raise_for_status()
            except requests.RequestException as e:  # pragma: no cover - network
                log_event("folder_list_error", f"{fid}: {e}")
                return []
            data = resp.json()
            for file in data.get("files", []):
                mime = file.get("mimeType", "")
                if mime == "application/vnd.google-apps.folder":
                    urls.extend(_list(file["id"]))
                elif mime.startswith("image/"):
                    urls.append(f"https://drive.google.com/uc?id={file['id']}")
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return urls

    return _list(folder_id)


def generate_prompt_from_image(image_bytes: bytes, model: str = "placeholder-model") -> Dict[str, Any]:
    """Generate a description and learning objectives from ``image_bytes``.

    This is a stub implementation.  In a future phase this function
    will call a multimodal model using ``image_bytes`` as input.
    """
    # TODO: replace with real vision model call
    description = "Placeholder description for the exercise image."
    objectives = ["Placeholder objective 1", "Placeholder objective 2"]
    return {"description": description, "objectives": objectives, "model_used": model}


def append_record(record: Dict[str, Any], output_file: str) -> None:
    """Append ``record`` as a JSON object to ``output_file``."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def process_images(config_path: str, output_file: str = "datasets/prompts_only.jsonl") -> None:
    """Download images listed in ``config_path`` and generate prompts."""

    with open(config_path, "r", encoding="utf-8") as f:
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

    total = len(urls)
    for idx, url in enumerate(urls, 1):
        log_event("progress", f"{idx}/{total}")
        try:
            path = download_image(url)
        except requests.RequestException as e:
            log_event("image_download_error", f"{url}: {e}")
            continue
        try:
            with open(path, "rb") as img_f:
                result = generate_prompt_from_image(img_f.read())
        except Exception as e:  # pragma: no cover - defensive
            log_event("prompt_error", f"{path}: {e}")
            continue
        record = {
            "image_path": path,
            "description": result["description"],
            "objectives": result["objectives"],
            "model_used": result.get("model_used", "unknown"),
        }
        append_record(record, output_file)
        log_event("prompt_generated", os.path.basename(path))


# ---------------------------------------------------------------------------
# Placeholders for future steps
# ---------------------------------------------------------------------------

def generate_code_from_prompt(prompt: str) -> str:
    """Placeholder for the Manim code generation step."""
    # TODO: implement code generation
    return ""


def render_video_from_code(code: str) -> str:
    """Placeholder for the video rendering step."""
    # TODO: implement video rendering
    return ""


def chat_refinement(message: str) -> str:
    """Placeholder for chat-based refinement of prompts or code."""
    # TODO: implement chat refinement
    return ""


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate prompts from Google Drive images")
    parser.add_argument("--config", default="tools/dataset_builder/images_config.json", help="Path to image URL config file")
    parser.add_argument(
        "--output",
        default="datasets/prompts_only.jsonl",
        help="Where to append generated prompt records",
    )
    args = parser.parse_args()
    process_images(args.config, args.output)
