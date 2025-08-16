import streamlit as st
import os
import requests
import json
from PIL import Image

from utils import *

icon = Image.open(os.path.dirname(__file__) + '/../icon.png')

st.set_page_config(page_icon=icon)

styl = f"""
<style>
  textarea {{
  font-family: 'Consolas', monospace !important;
  }}
  }}
</style>
"""
st.markdown(styl, unsafe_allow_html=True)

st.title('💻 Render Engine')

st.write("Quick engine to render Manim code. You can paste code, or generate code from a prompt and render it in one pipeline.")

st.write("## Hello! The new demo it's on [GM Demo](https://generative-manim.vercel.app) :rocket:")

# API configuration
default_api = os.environ.get('API_URL', 'http://127.0.0.1:8080')
api_url = st.text_input('API base URL', value=default_api)

mode = st.radio('Source', options=['Paste code', 'Generate from prompt'])

code = ''
prompt = ''
if mode == 'Paste code':
  code = st.text_area('Paste Manim Python code here', height=300)
else:
  prompt = st.text_area('Prompt to generate Manim code', value='Create a short Manim scene that shows solving 2x+3=7 step by step.', height=200)
  model = st.selectbox('Model for generation', options=['gpt-4o','o1-mini'], index=0)

st.markdown('---')

col1, col2 = st.columns(2)
stream_opt = col1.checkbox('Stream progress', value=False)
aspect = col2.selectbox('Aspect ratio', options=['16:9','1:1','9:16'], index=0)

generate_and_render = st.button('Generate and Render' if mode!='Paste code' else 'Render pasted code')

video_placeholder = st.empty()
progress_placeholder = st.empty()

if generate_and_render:
  # Acquire code: either pasted or generated
  if mode == 'Generate from prompt':
    if not prompt.strip():
      st.warning('Please enter a prompt.')
    else:
      with st.spinner('Requesting code generation...'):
        try:
          payload = {'prompt': prompt, 'model': model}
          resp = requests.post(f"{api_url.rstrip('/')}/v1/code/generation", json=payload, timeout=60)
          resp.raise_for_status()
          data = resp.json()
          code = data.get('code','')
          if not code:
            st.error(f'No code returned: {data}')
        except Exception as e:
          st.error(f'Code generation failed: {e}')
          code = ''

  # If we have code, render it
  if code and code.strip():
    st.subheader('Code to render')
    st.code(code, language='python')

    payload = {
      'code': code,
      'file_class': 'GenScene',
      'aspect_ratio': aspect,
      'stream': stream_opt
    }

    try:
      if stream_opt:
        progress_placeholder.info('Starting streaming render...')
        # stream response
        with requests.post(f"{api_url.rstrip('/')}/v1/video/rendering", json=payload, stream=True) as r:
          r.raise_for_status()
          last_json = None
          for raw in r.iter_lines(decode_unicode=True):
            if not raw:
              continue
            # Try to parse JSON chunk
            try:
              chunk = json.loads(raw)
              last_json = chunk
              if 'percentage' in chunk:
                progress_placeholder.info(f"Animation {chunk.get('animationIndex')} - {chunk.get('percentage')}%")
              elif 'video_url' in chunk:
                progress_placeholder.success('Render complete')
                video_url = chunk.get('video_url')
                video_placeholder.video(video_url)
                st.markdown(f"[Open video]({video_url})")
            except Exception:
              # Not JSON, show raw
              progress_placeholder.text(raw)
          # final check
          if last_json and isinstance(last_json, dict) and 'video_url' in last_json:
            video_url = last_json['video_url']
            video_placeholder.video(video_url)
            st.markdown(f"[Open video]({video_url})")
          else:
            progress_placeholder.warning('Streaming ended without a final video URL. Check server logs.')
      else:
        with st.spinner('Rendering (this may take a while)...'):
          resp = requests.post(f"{api_url.rstrip('/')}/v1/video/rendering", json=payload, timeout=600)
          resp.raise_for_status()
          data = resp.json()
          video_url = data.get('video_url') or data.get('videoUrl')
          if video_url:
            video_placeholder.video(video_url)
            st.markdown(f"[Open video]({video_url})")
          else:
            st.error(f'No video URL returned: {data}')
    except Exception as e:
      st.error(f'Render failed: {e}')
  else:
    st.warning('No code available to render.')
