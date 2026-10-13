"""Build deterministic vector draw commands from KAE scenes."""
import math
from engine.animation.exposure import drawing_at
from engine.animation.pose_evaluator import evaluate_transform
from engine.camera.camera_path import evaluate_camera_path
from engine.camera.camera_transform import world_to_screen
from engine.rendering.draw_command import DrawCommand
from engine.scenes.depth_order import sort_by_depth


def render_commands(project, frame, *, scene_id=None, camera=None):
    scenes = project.get("scenes", [])
    scene = next((item for item in scenes if item.get("id") == scene_id), None) if scene_id else (scenes[0] if scenes else None)
    if scene is None:
        return []
    camera = camera or evaluate_camera_path(
        scene.get("camera", {}).get("tracks", {}), frame,
        scene.get("camera", {}).get("transform", {}),
    )
    commands = []
    for index, layer in enumerate(sort_by_depth(scene.get("layers", []))):
        if not layer.get("visible", True):
            continue
        drawing_id = drawing_at(layer.get("exposures", []), frame)
        drawing = project.get("drawings", {}).get(drawing_id)
        if drawing is None:
            continue
        transform = evaluate_transform(layer, frame)
        opacity = transform.get("opacity", 1)
        angle = math.radians(transform.get("rotation", 0))
        cosine, sine = math.cos(angle), math.sin(angle)
        for stroke in drawing.get("strokes", []):
            points = []
            for point in stroke.get("points", []):
                x, y = point[0] * transform.get("scale_x", 1), point[1] * transform.get("scale_y", 1)
                x, y = x * cosine - y * sine, x * sine + y * cosine
                world = (x + transform.get("x", 0), y + transform.get("y", 0))
                points.append(world_to_screen(world, camera))
            commands.append(DrawCommand(
                "polygon" if stroke.get("fill") else "line", points,
                color=stroke.get("color", "#111111"), width=stroke.get("width", 1),
                fill=stroke.get("fill"), opacity=opacity, z=index,
                metadata={"layer_id": layer.get("id"), "drawing_id": drawing_id, "stroke_id": stroke.get("id")},
            ))
    return commands


def render_frame(project, frame, *, scene_id=None, background=None):
    from engine.rendering.rasterizer import rasterize
    settings = project.get("settings", {})
    scene = next((item for item in project.get("scenes", []) if item.get("id") == scene_id), None) if scene_id else project.get("scenes", [None])[0]
    camera = None
    if scene:
        camera = evaluate_camera_path(scene.get("camera", {}).get("tracks", {}), frame,
                                     scene.get("camera", {}).get("transform", {}))
    commands = render_commands(project, frame, scene_id=scene_id, camera=camera)
    return rasterize(commands, settings.get("width", 1280), settings.get("height", 720),
                     background=background or settings.get("background", "#ffffff"))
