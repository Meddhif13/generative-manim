from flask import Blueprint, jsonify, request
import anthropic
import os
from openai import OpenAI
from api.prompts.style_prompts import build_system_prompt, SUPPORTED_STYLES

code_generation_bp = Blueprint("code_generation", __name__)


def generate_code_for_prompt(prompt: str, model: str, system_prompt: str) -> str:
    """Generate Manim code for a single prompt using the specified model."""
    if model.startswith("claude-"):
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        messages = [{"role": "user", "content": prompt}]
        response = client.messages.create(
            model=model,
            max_tokens=1000,
            temperature=0.2,
            system=system_prompt,
            messages=messages,
        )
        return "".join(block.text for block in response.content)
    else:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content


@code_generation_bp.route("/v1/code/generation", methods=["POST"])
def generate_code():
    body = request.json or {}
    prompts = body.get("prompts")
    prompt_content = body.get("prompt", "")
    model = body.get("model", "gpt-4o")
    style = body.get("style", "1b3b-feynman-veritasium")

    if style not in SUPPORTED_STYLES:
        return (
            jsonify({"error": f"Invalid style. Must be one of: {', '.join(SUPPORTED_STYLES)}"}),
            400,
        )

    if prompt_content and prompts:
        return jsonify({"error": "Provide either 'prompt' or 'prompts', not both"}), 400

    if prompts is not None:
        if not isinstance(prompts, list):
            return jsonify({"error": "'prompts' must be a list of strings"}), 400
        if not all(isinstance(p, str) for p in prompts):
            return jsonify({"error": "All items in 'prompts' must be strings"}), 400

    system_prompt = build_system_prompt(style)

    try:
        if isinstance(prompts, list):
            codes = []
            for p in prompts:
                code = generate_code_for_prompt(p, model, system_prompt)
                codes.append({"prompt": p, "code": code, "model": model})
            return jsonify({"codes": codes, "style": style})
        else:
            code = generate_code_for_prompt(prompt_content, model, system_prompt)
            if prompts is None:
                return jsonify({"code": code, "style": style})
            return jsonify(
                {
                    "codes": [
                        {"prompt": prompt_content, "code": code, "model": model}
                    ],
                    "style": style,
                }
            )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@code_generation_bp.route("/v1/styles", methods=["GET"])
def available_styles():
    """Return the list of supported narrative styles."""
    return jsonify({"styles": SUPPORTED_STYLES})
