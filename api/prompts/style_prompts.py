"""Utilities for building system prompts with narrative styles."""
from typing import Callable

def build_system_prompt(style: str) -> str:
    """Return a system prompt for the given narrative ``style``.

    Parameters
    ----------
    style: str
        Identifier of the style to apply. Currently supports:
        ``"1b3b-feynman-veritasium"`` (default), ``"1b3b"``, ``"feynman"``,
        and ``"veritasium"``.
    """
    base_prompt = (
        "You are an assistant that writes Manim code.\n"
        "\n"
        "- Always define a class named GenScene and place all logic inside its construct method.\n"
        "- Use self.play for animations and rely purely on code; do not output explanatory text.\n"
        "- Target high-school mathematics (algebra, geometry, trigonometry and introductory calculus).\n"
    )

    narrative_prompt = (
        "Blend the narrative styles of 3Blue1Brown, Richard Feynman and Veritasium.\n"
        "Provide step-by-step visual intuition (3Blue1Brown), use simple analogies (Feynman)\n"
        "and weave a real-world narrative (Veritasium)."
    )

    if style == "1b3b-feynman-veritasium":
        return f"{base_prompt}\n{narrative_prompt}"
    elif style == "1b3b":
        # TODO: specialize for pure 3Blue1Brown style
        return f"{base_prompt}\n{narrative_prompt}"
    elif style == "feynman":
        # TODO: specialize for pure Feynman style
        return f"{base_prompt}\n{narrative_prompt}"
    elif style == "veritasium":
        # TODO: specialize for pure Veritasium style
        return f"{base_prompt}\n{narrative_prompt}"
    else:
        # Unknown style defaults to the blended narrative
        return f"{base_prompt}\n{narrative_prompt}"
