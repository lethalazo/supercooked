"""Character visual consistency - face generation, 3D rendering, reference management."""

from supercooked.character.face import generate_face
from supercooked.character.reference import add_reference, get_references, list_references, remove_reference
from supercooked.character.threeD import render_character

__all__ = [
    "generate_face",
    "render_character",
    "add_reference",
    "list_references",
    "get_references",
    "remove_reference",
]
