# Progress Log

## 2025-08-23
- Added Streamlit dataset tool for image, prompt, code, video, and chat workflow (`streamlit/src/dataset_app.py`).
- Introduced `DatasetRecord` dataclass and JSONL writer utility (`tools/dataset_builder/dataset_writer.py`).
- Documented dataset generation interface in README (`README.md`).
- Connected chat interface to real `/v1/chat/generation` API with streaming responses (`streamlit/src/dataset_app.py`).
- Added UI controls to edit and remove persistent rules (`streamlit/src/dataset_app.py`).

