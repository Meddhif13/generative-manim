from flask import Blueprint, jsonify, request
import subprocess
import os
import json
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
    """
    Uploads the video to Azure Blob Storage and returns the URL.
    """
    cloud_file_name = f"{video_storage_file_name}.mp4"

    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=cloud_file_name
    )

    # Upload the video file
    with open(file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

    # Construct the URL of the uploaded blob
    blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{cloud_file_name}"
    return blob_url


def move_to_public_folder(
    file_path: str, video_storage_file_name: str, base_url: Union[str, None] = None
) -> str:
    """
    Moves the video to the public folder and returns the URL.
    """
    public_folder = os.path.join(os.path.dirname(__file__), "public")
    os.makedirs(public_folder, exist_ok=True)

    new_file_name = f"{video_storage_file_name}.mp4"
    new_file_path = os.path.join(public_folder, new_file_name)

    shutil.move(file_path, new_file_path)

    # Use the provided base_url if available, otherwise fall back to BASE_URL
    url_base = base_url if base_url else BASE_URL
    video_url = f"{url_base.rstrip('/')}/public/{new_file_name}"
    return video_url


def get_frame_config(aspect_ratio):
    if aspect_ratio == "16:9":
        return (3840, 2160), 14.22
    elif aspect_ratio == "9:16":
        return (1080, 1920), 8.0
    elif aspect_ratio == "1:1":
        return (1080, 1080), 8.0
    else:
        return (3840, 2160), 14.22


def _render_single_video(data):
    """Render a single video and return result metadata.

    Parameters
    ----------
    data: dict
        Request payload containing ``code``, ``file_class`` and other metadata.

    Returns
    -------
    dict
        Result containing ``prompt``, ``code``, ``video_url``, ``time`` and ``error``.
    """

    start_time = time.time()
    code = data.get("code")
    file_name = data.get("file_name")
    file_class = data.get("file_class")

    user_id = data.get("user_id") or str(uuid.uuid4())
    project_name = data.get("project_name")
    iteration = data.get("iteration")
    aspect_ratio = data.get("aspect_ratio")
    prompt = data.get("prompt")

    video_storage_file_name = f"video-{user_id}-{project_name}-{iteration}"

    if not code:
        return {
            "prompt": prompt,
            "code": code,
            "error": "No code provided",
            "time": time.time() - start_time,
        }

    frame_size, frame_width = get_frame_config(aspect_ratio)

    modified_code = f"""
from manim import *
from math import *

{code}
    """

    file_name = file_name or f"{file_class or 'GenScene'}.py"
    file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), file_name)

    try:
        with open(file_path, "w") as f:
            f.write(modified_code)

        def inner_render():
            try:
                command_list = [
                    "manim",
                    file_path,
                    file_class,
                    "--format=mp4",
                    "--media_dir",
                    ".",
                    "--custom_folders",
                ]

                process = subprocess.Popen(
                    command_list,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=os.path.dirname(os.path.realpath(__file__)),
                    text=True,
                    bufsize=1,
                )
                error_output = []
                while True:
                    output = process.stdout.readline()
                    error = process.stderr.readline()
                    if output == "" and error == "" and process.poll() is not None:
                        break
                    if error:
                        error_output.append(error.strip())

                if process.returncode == 0:
                    video_file_path = os.path.join(
                        os.path.dirname(os.path.realpath(__file__)),
                        f"{file_class or 'GenScene'}.mp4",
                    )
                    if not os.path.exists(video_file_path):
                        video_file_path = os.path.join(
                            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                            f"{file_class or 'GenScene'}.mp4",
                        )
                    if USE_LOCAL_STORAGE:
                        base_url = (
                            request.host_url if request and hasattr(request, "host_url") else None
                        )
                        video_url = move_to_public_folder(
                            video_file_path, video_storage_file_name, base_url
                        )
                    else:
                        video_url = upload_to_azure_storage(
                            video_file_path, video_storage_file_name
                        )
                    return {"video_url": video_url}
                else:
                    full_error = "\n".join(error_output)
                    return {"error": full_error}
            except Exception as e:
                return {"error": str(e)}
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
                video_file = os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    f"{file_class or 'GenScene'}.mp4",
                )
                if os.path.exists(video_file):
                    os.remove(video_file)

        result = inner_render()
        result.update({
            "prompt": prompt,
            "code": code,
            "time": time.time() - start_time,
        })
        return result
    except Exception as e:
        return {
            "prompt": prompt,
            "code": code,
            "error": str(e),
            "time": time.time() - start_time,
        }


@video_rendering_bp.route("/v1/video/rendering", methods=["POST"])
def render_video():
    data = request.json or {}

    # Batch rendering path
    if isinstance(data.get("codes"), list):
        results = []
        for i, item in enumerate(data.get("codes", [])):
            payload = {**data, **item}
            payload.pop("codes", None)
            payload["iteration"] = f"{data.get('iteration', 0)}-{i}"
            payload.setdefault("stream", False)
            result = _render_single_video(payload)
            results.append(result)
        return jsonify({"videos": results}), 200

    # Single rendering
    # TODO: Consider asynchronous job handling here for future scalability.
    result = _render_single_video(data)
    status = 200 if not result.get("error") else 500
    return jsonify(result), status


@video_rendering_bp.route("/v1/video/exporting", methods=["POST"])
def export_video():
    scenes = request.json.get("scenes")
    title_slug = request.json.get("titleSlug")
    local_filenames = []

    # Download each scene
    for scene in scenes:
        video_url = scene["videoUrl"]
        object_name = video_url.split("/")[-1]
        local_filename = download_video(video_url)
        local_filenames.append(local_filename)

    # Create a list of input file arguments for ffmpeg
    input_files = " ".join([f"-i {filename}" for filename in local_filenames])

    # Generate a unique filename with UNIX timestamp
    timestamp = int(time.time())
    merged_filename = os.path.join(
        os.getcwd(), f"exported-scene-{title_slug}-{timestamp}.mp4"
    )

    # Command to merge videos using ffmpeg
    command = f"ffmpeg {input_files} -filter_complex 'concat=n={len(local_filenames)}:v=1:a=0[out]' -map '[out]' {merged_filename}"

    try:
        # Execute the ffmpeg command
        subprocess.run(command, shell=True, check=True)
        print("Videos merged successfully.")
        print(f"merged_filename: {merged_filename}")
        public_url = upload_to_azure_storage(
            merged_filename, f"exported-scene-{title_slug}-{timestamp}"
        )
        print(f"Video URL: {public_url}")
        return jsonify(
            {"status": "Videos merged successfully", "video_url": public_url}
        )
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg error: {e}")
        return jsonify({"error": "Failed to merge videos"}), 500
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


def download_video(video_url):
    local_filename = video_url.split("/")[-1]
    response = requests.get(video_url)
    response.raise_for_status()
    with open(local_filename, 'wb') as f:
        f.write(response.content)
    return local_filename
