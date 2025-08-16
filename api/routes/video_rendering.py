from flask import Blueprint, jsonify, current_app, request, Response
import subprocess
import os
import re
import json
import sys
import traceback
from azure.storage.blob import BlobServiceClient
import shutil
from typing import Union
import uuid
import time
import requests

video_rendering_bp = Blueprint("video_rendering", __name__)


USE_LOCAL_STORAGE = os.getenv("USE_LOCAL_STORAGE", "true") == "true"
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8080")


def upload_to_azure_storage(file_path: str, video_storage_file_name: str) -> str:
    cloud_file_name = f"{video_storage_file_name}.mp4"
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=cloud_file_name)
    with open(file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    return f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{cloud_file_name}"


def move_to_public_folder(file_path: str, video_storage_file_name: str, base_url: Union[str, None] = None) -> str:
    public_folder = os.path.join(os.path.dirname(__file__), "public")
    os.makedirs(public_folder, exist_ok=True)
    new_file_name = f"{video_storage_file_name}.mp4"
    new_file_path = os.path.join(public_folder, new_file_name)
    shutil.move(file_path, new_file_path)
    url_base = base_url if base_url else BASE_URL
    return f"{url_base.rstrip('/')}/public/{new_file_name}"


def get_frame_config(aspect_ratio):
    if aspect_ratio == "16:9":
        return (3840, 2160), 14.22
    if aspect_ratio == "9:16":
        return (1080, 1920), 8.0
    if aspect_ratio == "1:1":
        return (1080, 1080), 8.0
    return (3840, 2160), 14.22


@video_rendering_bp.route("/v1/video/rendering", methods=["POST"])
def render_video():
    # Extract input
    code = request.json.get("code")
    file_class = request.json.get("file_class")
    user_id = request.json.get("user_id") or str(uuid.uuid4())
    project_name = request.json.get("project_name") or "default"
    iteration = request.json.get("iteration") or "0"
    aspect_ratio = request.json.get("aspect_ratio")
    stream = request.json.get("stream", False)

    video_storage_file_name = f"video-{user_id}-{project_name}-{iteration}"

    if code is None:
        return jsonify(error="No code provided"), 400

    # Strip Markdown fences
    try:
        code = re.sub(r"^```(?:\w+)?\s*\n?", "", code)
        code = re.sub(r"\n?\s*```$", "", code)
        code = code.strip()
    except Exception:
        pass

    frame_size, frame_width = get_frame_config(aspect_ratio)

    modified_code = f"""
from manim import *
from math import *
config.frame_size = {frame_size}
config.frame_width = {frame_width}

{code}
"""

    # Write temp file
    api_dir = os.path.dirname(os.path.dirname(__file__))
    public_dir = os.path.join(api_dir, "public")
    os.makedirs(public_dir, exist_ok=True)
    file_path = os.path.join(public_dir, f"scene_{os.urandom(2).hex()}.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(modified_code)

    def run_and_stream():
        video_file_path = None
        error_output = []
        try:
            cmd = ["manim", file_path, file_class or "GenScene", "--format=mp4", "--media_dir", ".", "--custom_folders"]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=os.path.dirname(os.path.realpath(__file__)))

            while True:
                out = proc.stdout.readline()
                err = proc.stderr.readline()
                if out:
                    print("STDOUT:", out.strip())
                if err:
                    print("STDERR:", err.strip())
                    error_output.append(err.strip())
                    # detect progress
                    anim = re.search(r"Animation (\d+):", err)
                    if anim:
                        yield json.dumps({"animationIndex": int(anim.group(1)), "percentage": 0}) + "\n"
                    perc = re.search(r"(\d+)%", err)
                    if perc:
                        yield json.dumps({"animationIndex": None, "percentage": int(perc.group(1))}) + "\n"

                if out == "" and err == "" and proc.poll() is not None:
                    break

            if proc.returncode == 0:
                # Find produced mp4
                candidate = os.path.join(os.path.dirname(os.path.realpath(__file__)), f"{file_class or 'GenScene'}.mp4")
                if os.path.exists(candidate):
                    video_file_path = candidate
                else:
                    # try parent
                    candidate = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), f"{file_class or 'GenScene'}.mp4")
                    if os.path.exists(candidate):
                        video_file_path = candidate

                # fallback: newest mp4 in public_dir
                if not video_file_path:
                    mp4s = [p for p in os.listdir(public_dir) if p.lower().endswith('.mp4')]
                    if mp4s:
                        video_file_path = os.path.join(public_dir, sorted(mp4s)[-1])

                if not video_file_path or not os.path.exists(video_file_path):
                    yield json.dumps({"error": "Video file not found after rendering.\n" + "\n".join(error_output)}) + "\n"
                    return

                if USE_LOCAL_STORAGE:
                    base_url = request.host_url if request and hasattr(request, "host_url") else None
                    video_url = move_to_public_folder(video_file_path, video_storage_file_name, base_url)
                else:
                    video_url = upload_to_azure_storage(video_file_path, video_storage_file_name)

                yield json.dumps({"video_url": video_url}) + "\n"
            else:
                yield json.dumps({"error": "Manim failed:\n" + "\n".join(error_output)}) + "\n"

        except Exception as e:
            tb = traceback.format_exc()
            yield json.dumps({"error": str(e) + "\n" + tb}) + "\n"
        finally:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
            try:
                if video_file_path and os.path.exists(video_file_path):
                    os.remove(video_file_path)
            except Exception:
                pass

    if stream:
        return Response(run_and_stream(), content_type="text/event-stream", status=207)

    # non-streaming: collect generator results
    video_url = None
    for item in run_and_stream():
        try:
            parsed = json.loads(item)
        except Exception:
            continue
        if isinstance(parsed, dict) and parsed.get("video_url"):
            video_url = parsed["video_url"]
        if isinstance(parsed, dict) and parsed.get("error"):
            return jsonify({"error": parsed.get("error")}), 500

    if video_url:
        return jsonify({"message": "Video generation completed", "video_url": video_url}), 200
    return jsonify({"message": "Video generation completed, but no URL was found"}), 200


@video_rendering_bp.route("/v1/video/exporting", methods=["POST"])
def export_video():
    scenes = request.json.get("scenes")
    title_slug = request.json.get("titleSlug")
    local_filenames = []

    for scene in scenes:
        video_url = scene["videoUrl"]
        local_filename = download_video(video_url)
        local_filenames.append(local_filename)

    input_files = " ".join([f"-i {filename}" for filename in local_filenames])
    timestamp = int(time.time())
    merged_filename = os.path.join(os.getcwd(), f"exported-scene-{title_slug}-{timestamp}.mp4")
    command = f"ffmpeg {input_files} -filter_complex 'concat=n={len(local_filenames)}:v=1:a=0[out]' -map '[out]' {merged_filename}"

    try:
        subprocess.run(command, shell=True, check=True)
        public_url = upload_to_azure_storage(merged_filename, f"exported-scene-{title_slug}-{timestamp}")
        return jsonify({"status": "Videos merged successfully", "video_url": public_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def download_video(video_url):
    local_filename = video_url.split("/")[-1]
    response = requests.get(video_url)
    response.raise_for_status()
    with open(local_filename, "wb") as f:
        f.write(response.content)
    return local_filename
                    # Move/upload
