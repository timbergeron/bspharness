"""Scriptable Quake 1 geometry, compilation, and verification."""

from .geometry import Bounds, Brush, Face, box, ramp
from .mapfile import Map, Palette
from .materials import Material, TextureLibrary, WallRun
from .transitions import TransitionRule
from .kits import arch, beam, column, stairs, trim_profile
from .lighting import fixture, lighting_recipe
from .routes import Move, WalkRoute

__all__ = ["Bounds", "Brush", "Face", "Map", "Palette", "Material", "TextureLibrary",
           "TransitionRule", "WallRun", "box", "ramp", "arch", "beam", "column",
           "stairs", "trim_profile", "fixture", "lighting_recipe", "Move", "WalkRoute"]
__version__ = "0.3.0"
