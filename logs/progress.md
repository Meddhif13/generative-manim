# Progress Log

## 2025-08-23
- Added Streamlit dataset tool for image, prompt, code, video, and chat workflow (`streamlit/src/dataset_app.py`).
- Introduced `DatasetRecord` dataclass and JSONL writer utility (`tools/dataset_builder/dataset_writer.py`).
- Documented dataset generation interface in README (`README.md`).
- Connected chat interface to real `/v1/chat/generation` API with streaming responses (`streamlit/src/dataset_app.py`).
- Added UI controls to edit and remove persistent rules (`streamlit/src/dataset_app.py`).
- Started new dataset generation app rebuild with an image upload skeleton (`streamlit/src/app_skeleton.py`).
- Expanded skeleton with side-by-side placeholders for prompt, code, video and chat (`streamlit/src/app_skeleton.py`).
- Added simple chat history using Streamlit's chat components (`streamlit/src/app_skeleton.py`).
- Simplified chat state initialization with `setdefault` (`streamlit/src/app_skeleton.py`).
- Introduced minimal rule management allowing users to add and remove persistent rules (`streamlit/src/app_skeleton.py`).

- Integrated real vision model via HTTP API, model selection dropdowns and user ID capture (`streamlit/src/dataset_app.py`).
- Added robust error handling, per-model timestamp metadata and configuration section (`streamlit/src/dataset_app.py`).

- Implemented automatic image download from Google Drive and placeholder prompt generation with logging (`tools/dataset_builder/prompt_generator.py`, `tools/dataset_builder/images_config.json`).
- Added Streamlit interface to display downloaded images and generated prompts (`streamlit/src/prompt_viewer.py`).
- Extended dataset utilities to traverse Google Drive folders recursively and show per-image progress in the Streamlit viewer.
- Refactored logging helper into a shared utility for reuse across tools (`tools/log_utils.py`).
- Refined Streamlit prompt viewer with progress bar, side-by-side display, and approve/skip controls (`streamlit/src/prompt_viewer.py`).
 - Prompt generator and viewer now accept user-supplied Google Drive folder links, making the static config optional.

2025-08-23T21:23:35.179853	progress	1/2
2025-08-23T21:23:35.526722	image_download_error	https://drive.google.com/uc?id=1X7ZnQEqplLWYwgd0_zpZK0s8AjtKoa6G: 404 Client Error: Not Found for url: https://drive.usercontent.google.com/download?id=1X7ZnQEqplLWYwgd0_zpZK0s8AjtKoa6G
2025-08-23T21:23:35.527222	progress	2/2
2025-08-23T21:23:35.865878	image_download_error	https://drive.google.com/uc?id=1NgGDZ-infaWS0URKywH14r2raXI5Qun7: 404 Client Error: Not Found for url: https://drive.usercontent.google.com/download?id=1NgGDZ-infaWS0URKywH14r2raXI5Qun7
