"""Sampled scalar/vector motion curves with arc-length metadata."""
from engine.animation.interpolation import evaluate_track
from engine.geometry.points import polyline_length


class MotionCurve:
    def __init__(self, keyframes):
        self.keyframes = sorted((dict(key) for key in keyframes), key=lambda key: key["t"])
        if any(a["t"] >= b["t"] for a, b in zip(self.keyframes, self.keyframes[1:])):
            raise ValueError("Motion key times must strictly increase")

    def evaluate(self, frame, default=0):
        return evaluate_track(self.keyframes, frame, default)

    def sample(self, start=None, end=None, count=32):
        if count < 1:
            raise ValueError("count must be positive")
        if not self.keyframes:
            return []
        start = self.keyframes[0]["t"] if start is None else start
        end = self.keyframes[-1]["t"] if end is None else end
        return [self.evaluate(start + (end - start) * i / count) for i in range(count + 1)]


def path_length(samples):
    return polyline_length(samples)
