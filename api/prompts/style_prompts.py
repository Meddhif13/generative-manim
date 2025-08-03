"""Utilities for building system prompts with narrative styles."""

# Supported narrative styles for the system prompt builder
SUPPORTED_STYLES = [
    "1b3b-feynman-veritasium",
    "1b3b",
    "feynman",
    "veritasium",
]


def build_system_prompt(style: str) -> str:
    """Return a system prompt for the given narrative ``style``.

    Supported styles are listed in :data:`SUPPORTED_STYLES`.
    The prompt instructs the model to produce Manim code using the ``GenScene``
    class and ``self.play`` for animations without plain-text explanation.
    Each style appends its own narrative guidance aimed at high-school level
    mathematics.
    """

    base_prompt = (
        "You are an assistant that writes Manim code.\n"
        "\n"
        "- Always define a class named GenScene and place all logic inside its construct method.\n"
        "- Use self.play for animations and rely purely on code; do not output explanatory text.\n"
        "- Target high-school mathematics (algebra, geometry, trigonometry and introductory calculus).\n"
    )

    blended = (
        "Blend the narrative styles of 3Blue1Brown, Richard Feynman and Veritasium.\n"
        "Provide step-by-step visual intuition (3Blue1Brown), use simple analogies (Feynman)\n"
        "and weave a real-world narrative (Veritasium)."
    )

    style_prompts = {
        "1b3b-feynman-veritasium": blended,
        "1b3b": (
            "Emphasise intuitive visual derivations and a clear, step-by-step proof "
            "structure in the spirit of 3Blue1Brown."
        ),
        "feynman": (
            "Explain concepts using simple analogies and a friendly, conversational "
            "tone reminiscent of Richard Feynman."
        ),
        "veritasium": (
            "Focus on storytelling, curiosity-driven questions and real-world context "
            "as seen in Veritasium videos."
        ),
    }

    narrative_prompt = style_prompts.get(style, blended)
    return f"{base_prompt}\n{narrative_prompt}"
