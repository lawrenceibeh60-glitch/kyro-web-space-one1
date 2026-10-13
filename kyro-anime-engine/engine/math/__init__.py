"""Dependency-free 2D and 3D math utilities."""
from engine.math.numerical import clamp, lerp
from engine.math.vectors import add, distance, dot, length, normalize, scale, subtract

__all__ = ["add", "subtract", "scale", "dot", "length", "normalize", "distance", "clamp", "lerp"]