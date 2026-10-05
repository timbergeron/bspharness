"""Scriptable Quake 1 geometry, compilation, and verification."""

from .geometry import Bounds, Brush, Face, box, ramp
from .mapfile import Map, Palette

__all__ = ["Bounds", "Brush", "Face", "Map", "Palette", "box", "ramp"]
__version__ = "0.1.0"
