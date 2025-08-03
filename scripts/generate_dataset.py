# Offline batch-processing script for building a training dataset.
#
# Reads prompts from a JSON/JSONL/CSV file, generates Manim code and videos
# using the local API and stores the results in a JSONL dataset file.
#
# Usage:
#     python scripts/generate_dataset.py prompts.jsonl output.jsonl
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List

import requests

API_BASE = "http://localhost:5000"


def read_prompts(path: Path) -> List[str]:
    if path.suffix == ".json":
        return json.loads(path.read_text())
    if path.suffix in {".jsonl", ".jl"}:
        return [json.loads(line)["prompt"] for line in path.read_text().splitlines()]
    if path.suffix == ".csv":
        with path.open() as f:
            reader = csv.DictReader(f)
            return [row["prompt"] for row in reader]
    raise ValueError("Unsupported input format")


def main(input_file: str, output_file: str) -> None:
    prompts = read_prompts(Path(input_file))
    dataset: List[Dict[str, str]] = []
    for prompt in prompts:
        body = {"prompts": [prompt], "style": "1b3b-feynman-veritasium"}
        code_resp = requests.post(f"{API_BASE}/v1/code/generation", json=body)
        code_resp.raise_for_status()
        codes = code_resp.json().get("codes") or []
        code = codes[0]["code"] if codes else code_resp.json().get("code", "")

        render_body = {"codes": [{"code": code, "file_class": "GenScene"}]}
        render_resp = requests.post(f"{API_BASE}/v1/video/rendering", json=render_body)
        render_resp.raise_for_status()
        videos = render_resp.json().get("videos") or []
        video_url = None
        if videos:
            first = videos[0]
            video_url = first.get("video_url") if isinstance(first, dict) else first

        dataset.append({"prompt": prompt, "code": code, "video_url": video_url})

    with open(output_file, "w") as f:
        for item in dataset:
            f.write(json.dumps(item) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/generate_dataset.py <prompts_file> <output_file>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
