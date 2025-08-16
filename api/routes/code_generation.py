from flask import Blueprint, jsonify, request
# Anthropic support temporarily disabled; keep placeholder for future use.
# import anthropic
import os
from openai import OpenAI

code_generation_bp = Blueprint('code_generation', __name__)

@code_generation_bp.route('/v1/code/generation', methods=['POST'])
def generate_code():
    body = request.json
    prompt_content = body.get("prompt", "")
    model = body.get("model", "gpt-4o")

    general_system_prompt = """
You are an assistant that knows about Manim. Manim is a mathematical animation engine that is used to create videos programmatically.

The following is an example of the code:
\`\`\`
from manim import *
from math import *

class GenScene(Scene):
def construct(self):
    c = Circle(color=BLUE)
    self.play(Create(c))

\`\`\`

# Rules
1. Always use GenScene as the class name, otherwise, the code will not work.
2. Always use self.play() to play the animation, otherwise, the code will not work.
3. Do not use text to explain the code, only the code.
4. Do not explain the code, only the code.
    """


    if model.startswith("claude-"):
        # Anthropic models are disabled in this environment. Keep this branch as a placeholder.
        return jsonify({"error": "Anthropic models are temporarily disabled. Use an OpenAI model like 'gpt-4o'."}), 400

    else:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        messages = [
            {"role": "system", "content": general_system_prompt},
            {"role": "user", "content": prompt_content},
        ]

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
            )

            code = response.choices[0].message.content

            return jsonify({"code": code})

        except Exception as e:
            return jsonify({"error": str(e)}), 500
