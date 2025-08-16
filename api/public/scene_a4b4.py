
from manim import *
from math import *
config.frame_size = (3840, 2160)
config.frame_width = 14.22

from manim import *

class GenScene(Scene):
    def construct(self):
        equation = MathTex("2x + 3 = 7")
        step1 = MathTex("2x + 3 - 3 = 7 - 3")
        step2 = MathTex("2x = 4")
        step3 = MathTex("\\frac{2x}{2} = \\frac{4}{2}")
        step4 = MathTex("x = 2")

        self.play(Write(equation))
        self.wait(1)
        self.play(Transform(equation, step1))
        self.wait(1)
        self.play(Transform(equation, step2))
        self.wait(1)
        self.play(Transform(equation, step3))
        self.wait(1)
        self.play(Transform(equation, step4))
        self.wait(1)
