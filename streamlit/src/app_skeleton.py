"""Minimal Streamlit application for dataset generation.

This skeleton implements the first step of the new dataset generation tool.
Users can upload an exercise image which is displayed immediately.
Future commits will extend this interface with prompt generation, code
rendering, chat refinement and dataset logging.
"""

import streamlit as st
from PIL import Image


def main() -> None:
    """Run the Streamlit app."""
    st.set_page_config(layout="wide", page_title="Dataset Tool Skeleton")
    st.title("Dataset Generation Tool")

    uploaded = st.file_uploader("Upload exercise image", type=["png", "jpg", "jpeg"])
    if uploaded:
        image = Image.open(uploaded)
        st.image(image, caption="Uploaded image", use_column_width=True)


if __name__ == "__main__":
    main()
