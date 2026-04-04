"""3D character rendering via Blender bpy (headless).

Wraps Blender's Python API to create basic 3D character renders.
Requires Blender to be installed and bpy importable.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from supercooked.config import IDENTITIES_DIR, OUTPUT_DIR
from supercooked.identity.action_log import log_action
from supercooked.identity.manager import load_identity


def _ensure_bpy():
    """Import bpy, raising RuntimeError if Blender is not available."""
    try:
        import bpy  # noqa: F401
        return bpy
    except ImportError:
        raise RuntimeError(
            "Blender Python module (bpy) is not available. "
            "Install Blender and ensure it is on your PATH, or install the bpy pip package. "
            "See: https://docs.blender.org/api/current/"
        )


def render_character(
    slug: str,
    pose: str = "default",
    output_path: Path | None = None,
    resolution: tuple[int, int] = (1080, 1920),
) -> Path:
    """Render a 3D character for a digital being using Blender bpy.

    Creates a basic humanoid 3D mesh, applies pose, and renders to an image.

    Args:
        slug: Identity slug.
        pose: Pose name - "default" (standing), "wave", "sit", "point".
        output_path: Optional custom output path. Defaults to output/<slug>/3d/<timestamp>.png.
        resolution: Render resolution as (width, height). Defaults to 1080x1920.

    Returns:
        Path to the rendered image file.

    Raises:
        RuntimeError: If Blender bpy is not installed/importable.
        FileNotFoundError: If the identity does not exist.
    """
    bpy = _ensure_bpy()

    # Verify identity exists
    identity = load_identity(slug)

    # Determine output path
    if output_path is None:
        render_dir = OUTPUT_DIR / slug / "3d"
        render_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:6]
        output_path = render_dir / f"{pose}_{timestamp}_{unique_id}.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Reset Blender scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Create a basic character mesh (humanoid placeholder)
    # Head
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=(0, 0, 1.7))
    head = bpy.context.active_object
    head.name = f"{slug}_head"

    # Body
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1.0))
    body = bpy.context.active_object
    body.name = f"{slug}_body"
    body.scale = (0.4, 0.25, 0.5)

    # Legs
    for x_offset in (-0.15, 0.15):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.8, location=(x_offset, 0, 0.35))
        leg = bpy.context.active_object
        leg.name = f"{slug}_leg"

    # Arms
    for x_offset, arm_name in [(-0.55, "left_arm"), (0.55, "right_arm")]:
        bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.6, location=(x_offset, 0, 1.1))
        arm = bpy.context.active_object
        arm.name = f"{slug}_{arm_name}"

        # Apply pose
        if pose == "wave" and arm_name == "right_arm":
            arm.rotation_euler = (0, 0, 0.8)
            arm.location = (0.5, 0, 1.4)
        elif pose == "point" and arm_name == "right_arm":
            arm.rotation_euler = (0, -1.2, 0)
            arm.location = (0.5, 0, 1.2)

    # Apply sitting pose
    if pose == "sit":
        for obj in bpy.data.objects:
            if "leg" in obj.name:
                obj.rotation_euler = (1.57, 0, 0)
                obj.location = (obj.location.x, 0.3, 0.6)

    # Create a material with the being's name-derived color
    name_hash = hash(identity.being.name) % 0xFFFFFF
    r = ((name_hash >> 16) & 0xFF) / 255.0
    g = ((name_hash >> 8) & 0xFF) / 255.0
    b = (name_hash & 0xFF) / 255.0

    mat = bpy.data.materials.new(name=f"{slug}_material")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)

    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.data.materials.append(mat)

    # Set up camera
    bpy.ops.object.camera_add(location=(3, -3, 2))
    camera = bpy.context.active_object
    camera.name = "RenderCamera"

    # Point camera at the character
    bpy.ops.object.constraint_add(type="TRACK_TO")
    constraint = camera.constraints["Track To"]
    constraint.target = head
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"

    bpy.context.scene.camera = camera

    # Set up lighting
    bpy.ops.object.light_add(type="SUN", location=(5, -5, 10))
    sun = bpy.context.active_object
    sun.data.energy = 3.0

    bpy.ops.object.light_add(type="AREA", location=(-3, 3, 5))
    fill = bpy.context.active_object
    fill.data.energy = 50.0

    # Configure render settings
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.filepath = str(output_path)
    scene.render.image_settings.file_format = "PNG"

    # Render
    bpy.ops.render.render(write_still=True)

    log_action(
        slug,
        action="render_3d_character",
        platform="blender",
        details={
            "pose": pose,
            "resolution": f"{resolution[0]}x{resolution[1]}",
            "output_path": str(output_path),
        },
        result=f"Rendered 3D character at {output_path}",
    )

    return output_path
