"""Streamlit interface for exploring the Generative Manim API."""

import json

try:
    import streamlit as st
    import requests
except Exception:  # pragma: no cover - interface dependencies may be optional
    st = None

API_BASE = "http://127.0.0.1:8080"

if st is None:
    print("Streamlit not installed. Install interface requirements to enable this app.")
else:
    st.title("Generative Manim Interface")

    # Fetch available styles and models
    try:
        style_resp = requests.get(f"{API_BASE}/v1/styles").json()
        styles = style_resp.get("styles", [])
    except Exception:
        styles = []
    try:
        model_resp = requests.get(f"{API_BASE}/v1/models").json()
        # flatten models into list of all valid models
        models = []
        for engine_models in model_resp.get("valid_models", {}).values():
            models.extend(engine_models)
    except Exception:
        models = []

    style_choice = st.selectbox("Style", styles) if styles else st.text_input("Style")
    model_choice = st.selectbox("Model", models) if models else st.text_input("Model")
    prompts_input = st.text_area("Prompts (one per line)")

    if "results" not in st.session_state:
        st.session_state["results"] = []

    if st.button("Generate Code"):
        prompt_list = [p.strip() for p in prompts_input.splitlines() if p.strip()]
        payload = {"prompts": prompt_list, "style": style_choice, "model": model_choice}
        with st.spinner("Generating code..."):
            resp = requests.post(f"{API_BASE}/v1/code/generation", json=payload).json()
            st.session_state["results"] = resp.get("codes", [])

    results = st.session_state.get("results", [])
    for idx, item in enumerate(results):
        st.subheader(f"Prompt {idx}")
        prompt_val = st.text_input("Prompt", item.get("prompt", ""), key=f"prompt_{idx}")
        code_val = st.text_area("Code", item.get("code", ""), height=200, key=f"code_{idx}")
        cols = st.columns(2)
        if cols[0].button("Improve with Chat", key=f"improve_{idx}"):
            messages = [{"role": "user", "content": prompt_val, "prompt_index": idx}]
            payload = {
                "messages": messages,
                "review_mode": True,
                "style": style_choice,
                "prompts": [r["prompt"] for r in results],
                "codes": results,
                "prompt_index": idx,
            }
            with st.spinner("Improving code..."):
                response = requests.post(
                    f"{API_BASE}/v1/chat/generation", json=payload, stream=True
                )
                improved = None
                for line in response.iter_lines():
                    if not line:
                        continue
                    if line.startswith(b"data:"):
                        chunk = json.loads(line.decode()[5:])
                        if "improved_code" in chunk:
                            improved = chunk["improved_code"][idx]
                if improved:
                    results[idx]["code"] = improved
                    st.success("Code improved")

        if cols[1].button("Render", key=f"render_{idx}"):
            payload = {"codes": [{"prompt": prompt_val, "code": code_val, "file_class": "GenScene"}]}
            with st.spinner("Rendering video..."):
                resp = requests.post(f"{API_BASE}/v1/video/rendering", json=payload).json()
                video_url = resp.get("videos", [{}])[0].get("video_url")
                if video_url:
                    st.video(video_url)
                    results[idx]["video_url"] = video_url

    if st.button("Export Dataset"):
        dataset = [
            {"prompt": r.get("prompt"), "code": r.get("code"), "video_url": r.get("video_url")}
            for r in results
        ]
        data_str = "\n".join(json.dumps(d) for d in dataset)
        st.download_button("Download JSONL", data=data_str, file_name="dataset.jsonl")
