import streamlit as st
import os
import requests
import json
from PIL import Image

from utils import *

icon = Image.open(os.path.dirname(__file__) + '/../icon.png')

st.set_page_config(page_icon=icon)

st.markdown('# 🤖 Prompt Engine')

st.write("Prompt engineering is about giving correct instructions to GPT-4. The more precise the instructions, the better the results. The goal is to generate Manim code from a specific part of code. Then you can use the code to render the animation.")

st.write("## Hello! The new demo it's on [GM Demo](https://generative-manim.vercel.app) :rocket:")

# API URL configuration
default_api = os.environ.get('API_URL', 'http://127.0.0.1:8080')
api_url = st.text_input('API base URL', value=default_api, help='Local API server (Flask)')

st.markdown('---')

prompt = st.text_area('Prompt', value='Create a short Manim scene that shows solving 2x+3=7 step by step.', height=180)
model = st.selectbox('Model', options=['gpt-4o', 'o1-mini'], index=0)

if st.button('Generate'):
	if not prompt.strip():
		st.warning('Please enter a prompt.')
	else:
		with st.spinner('Generating code...'):
			try:
				payload = {'prompt': prompt, 'model': model}
				resp = requests.post(f"{api_url.rstrip('/')}/v1/code/generation", json=payload, timeout=60)
				resp.raise_for_status()
				data = resp.json()
				code = data.get('code')
				if code:
					st.subheader('Generated code')
					st.code(code, language='python')
					# Optionally show extract of construct
					try:
						construct_only = extract_construct_code(code)
						if construct_only:
							st.subheader('construct() body (extracted)')
							st.code(construct_only, language='python')
					except Exception:
						pass
				else:
					st.error(f"No code returned: {json.dumps(data)}")
			except requests.RequestException as e:
				st.error(f"Request failed: {e}")
