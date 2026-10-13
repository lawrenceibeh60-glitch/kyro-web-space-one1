"""KYRO ANIME ENGINE - project scaffold with steps 1-7 included
(schemas, Flask backend, Blender-style editor, drawing, animation, export, workspaces).

Usage: python scaffold.py [target_dir] [--update]

Creates every folder and file, fills the built files with their real contents and leaves
the rest as stubs. Safe to re-run: files you have edited are never overwritten.
Files this script wrote earlier and you have not touched are upgraded automatically.
--update  also overwrites files that differ (your edits or an older scaffold); old copies are saved as .bak
"""
import base64
import hashlib
import json
import shutil
import sys
import zlib
from pathlib import Path

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
UPDATE = "--update" in sys.argv[1:]
ROOT = Path(ARGS[0] if ARGS else "kyro-anime-engine")
MANIFEST = ".kae_scaffold.json"  # hashes of files this script wrote, to tell untouched from edited

# folder -> space-separated files
TREE = {
    ".": "run.py requirements.txt pyproject.toml config.py README.md LICENSE .gitignore",

    # ---------- BACKEND ----------
    "backend/app": "application.py lifecycle.py middleware.py exceptions.py dependencies.py",
    "backend/api": "health.py projects.py characters.py drawings.py rigs.py animations.py scenes.py layers.py assets.py timeline.py effects.py cameras.py rendering.py exports.py settings.py schemas.py",
    "backend/services": "project_service.py character_service.py drawing_service.py rig_service.py animation_service.py scene_service.py asset_service.py timeline_service.py render_service.py export_service.py validation_service.py",
    "backend/storage": "project_repository.py asset_repository.py project_index.py file_manager.py atomic_writer.py",

    # ---------- ENGINE ----------
    "engine/core": "engine.py context.py registry.py event_bus.py identifiers.py dependency_graph.py versioning.py diagnostics.py errors.py capabilities.py",
    "engine/project": "project.py project_loader.py project_saver.py project_settings.py project_migration.py asset_manifest.py project_validator.py",
    "engine/data": "json_loader.py json_writer.py schema_registry.py schema_validator.py reference_resolver.py type_coercion.py normalizer.py compiler.py serialization.py",
    "engine/math": "vectors.py matrices.py transforms.py quaternions.py curves.py intersections.py bounding_boxes.py polygons.py triangulation.py numerical.py",
    "engine/geometry": "points.py paths.py bezier.py splines.py contours.py primitives.py mesh2d.py triangulation.py clipping.py tessellation.py spatial_index.py",
    "engine/drawing": "drawing.py stroke.py fill.py brush.py pressure.py path_builder.py shape_builder.py symmetry.py smoothing.py outline_builder.py drawing_operations.py",
    "engine/characters": "character.py character_builder.py character_profile.py character_state.py proportions.py style_profile.py",
    "engine/characters/anatomy": "body_generator.py torso.py shoulders.py arms.py hands.py legs.py feet.py neck.py anatomy_constraints.py",
    "engine/characters/face": "face_generator.py head_shape.py eyes.py irises.py pupils.py eyebrows.py nose.py mouth.py ears.py eyelashes.py expressions.py facial_layout.py",
    "engine/characters/hair": "hair_generator.py hair_styles.py hair_locks.py hair_strands.py hair_layers.py hair_shading.py hair_dynamics.py",
    "engine/characters/clothing": "outfit_generator.py garment.py garment_panels.py folds.py seams.py accessories.py cloth_dynamics.py",
    "engine/characters/views": "front_view.py side_view.py three_quarter_view.py back_view.py view_consistency.py",
    "engine/characters/generation": "parameter_sampler.py geometry_generator.py constraint_solver.py variation.py seed_manager.py quality_checks.py",
    "engine/rigging": "skeleton.py bone.py joint.py rig_builder.py skinning.py deformation.py constraints.py forward_kinematics.py inverse_kinematics.py pose.py pose_library.py rig_validation.py",
    "engine/animation": "animation_clip.py timeline.py keyframe.py keyframe_track.py interpolation.py easing.py motion_curve.py pose_evaluator.py animation_blender.py animation_layers.py animation_events.py frame_rate.py exposure.py lip_sync.py secondary_motion.py",
    "engine/scenes": "scene.py scene_loader.py scene_graph.py scene_node.py hierarchy.py layers.py visibility.py depth_order.py scene_bounds.py scene_validation.py",
    "engine/camera": "camera.py camera_transform.py framing.py camera_path.py zoom.py shake.py tracking.py",
    "engine/rendering": "renderer.py render_context.py render_settings.py render_graph.py render_queue.py draw_command.py draw_batch.py rasterizer.py antialiasing.py line_renderer.py fill_renderer.py mask_renderer.py clipping.py cache.py render_diagnostics.py",
    "engine/shading": "materials.py palettes.py cel_shading.py gradients.py highlights.py shadow_shapes.py light_sources.py rim_lighting.py color_management.py",
    "engine/effects": "effect_stack.py particles.py speed_lines.py impact_frames.py motion_trails.py lightning.py energy_aura.py distortion.py screen_flash.py effect_timing.py",
    "engine/compositing": "compositor.py blend_modes.py alpha.py masks.py depth_compositing.py color_adjustments.py",
    "engine/audio": "audio_track.py waveform.py synchronization.py dialogue.py audio_export.py",
    "engine/export": "export_manager.py frame_scheduler.py render_job.py image_sequence.py video_encoder.py gif_export.py sprite_sheet.py alpha_export.py export_validation.py",
    "engine/performance": "memory_budget.py task_scheduler.py cancellation.py profiling.py resource_pool.py cache_policy.py",

    # ---------- FRONTEND ----------
    "frontend": "index.html editor.html",
    "frontend/css/base": "reset.css variables.css typography.css utilities.css",
    "frontend/css/layout": "application.css header.css sidebar.css workspace.css panels.css responsive.css",
    "frontend/css/components": "buttons.css inputs.css dialogs.css tabs.css tooltips.css dropdowns.css menus.css notifications.css",
    "frontend/css/editor": "viewport.css toolbar.css inspector.css hierarchy.css asset_browser.css canvas_tools.css workspace.css",
    "frontend/css/character": "character_studio.css face_editor.css hair_editor.css outfit_editor.css anatomy_editor.css rig_editor.css",
    "frontend/css/animation": "timeline.css keyframes.css dope_sheet.css graph_editor.css playback.css",
    "frontend/css/rendering": "render_queue.css render_settings.css export_dialog.css",
    "frontend/css/themes": "dark.css high_contrast.css",
    "frontend/js/core": "application.js event_bus.js state_manager.js command_manager.js undo_redo.js keyboard_shortcuts.js selection_manager.js",
    "frontend/js/api": "client.js projects.js characters.js drawings.js animations.js scenes.js exports.js",
    "frontend/js/editor": "editor_controller.js viewport_controller.js canvas_controller.js transform_tools.js drawing_tools.js hierarchy_controller.js inspector_controller.js workspace_layout.js",
    "frontend/js/rendering": "renderer.js canvas_backend.js geometry.js draw_queue.js outlines.js shading.js compositing.js render_cache.js",
    "frontend/js/character": "character_builder.js face_renderer.js body_renderer.js hair_renderer.js outfit_renderer.js character_controller.js character_inspector.js",
    "frontend/js/animation": "timeline.js playback.js keyframes.js interpolation.js pose_evaluator.js animation_clips.js graph_editor.js",
    "frontend/js/scene": "scene_controller.js scene_hierarchy.js layers.js camera_controller.js",
    "frontend/js/effects": "particles.js speed_lines.js lightning.js camera_shake.js",
    "frontend/js/ui": "project_manager.js asset_browser.js properties_panel.js timeline_panel.js dialogs.js notifications.js",
    "frontend/assets/icons": "",
    "frontend/assets/fonts": "",
    "frontend/assets/presets": "",

    # ---------- FORMATS ----------
    "formats/schemas": "project.schema.json character.schema.json drawing.schema.json rig.schema.json animation.schema.json scene.schema.json effects.schema.json render.schema.json",
    "formats/examples": "project.json character.json scene.json animation.json",

    # ---------- DATA DIRS ----------
    "projects": "",
    "user_assets": "",
    "cache": "",
    "exports": "",

    # ---------- TESTS ----------
    **{f"tests/{d}": "" for d in "core data geometry drawing characters rigging animation scenes rendering effects export integration".split()},

    # ---------- DOCS ----------
    "docs": "architecture.md project_format.md character_generation.md drawing_engine.md rigging_system.md animation_pipeline.md rendering_pipeline.md effects_system.md export_pipeline.md performance.md",
}

GITIGNORE = "__pycache__/\n*.pyc\ncache/\nexports/\nprojects/\nuser_assets/\n.venv/\n*.tmp\n*.recovery\n*.bak\n"


def stub(path: Path) -> str:
    name = path.name
    ext = path.suffix
    if name == ".gitignore":
        return GITIGNORE
    if name == "requirements.txt":
        return "# Core runtime stays dependency-light (Pydroid friendly)\nflask\n# Optional: pillow (final renders), imageio-ffmpeg\n"
    if ext == ".py":
        return f'"""{path.relative_to(ROOT).as_posix()} - TODO"""\n'
    if ext == ".js":
        return f"// {path.relative_to(ROOT).as_posix()} - TODO\n"
    if ext == ".css":
        return f"/* {path.relative_to(ROOT).as_posix()} - TODO */\n"
    if ext == ".html":
        return "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><title>KAE</title></head><body></body></html>\n"
    if ext == ".json":
        return "{}\n"
    if ext == ".md":
        return f"# {path.stem.replace('_', ' ').title()}\n\nTODO\n"
    return ""


# ---------- REAL FILE CONTENTS (steps 1-7), zlib + base64 encoded JSON {path: text} ----------
FILES_B64 = (
    "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"
    "ng=="
)


def load_files():
    return json.loads(zlib.decompress(base64.b64decode(FILES_B64)).decode("utf-8"))


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_manifest() -> dict:
    try:
        return json.loads((ROOT / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def untouched(path: Path, manifest: dict) -> bool:
    """True if the file is empty, still the generated stub, or exactly what this script last wrote."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    rel = path.relative_to(ROOT).as_posix()
    return text.strip() == "" or text == stub(path) or manifest.get(rel) == sha(text)


def main():
    real = stubs = kept = updated = 0
    ROOT.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    # 1) real contents
    for rel, content in load_files().items():
        f = ROOT / rel
        cur = f.read_text(encoding="utf-8") if f.exists() else None
        if cur == content:
            manifest[rel] = sha(content)
        elif cur is None or untouched(f, manifest):
            write(f, content)
            manifest[rel] = sha(content)
            real += 1
        elif UPDATE:
            shutil.copy2(f, f.with_name(f.name + ".bak"))
            write(f, content)
            manifest[rel] = sha(content)
            updated += 1
        else:
            kept += 1  # edited by you or from an older scaffold - left alone

    # 2) folders + stubs for everything else
    for folder, names in TREE.items():
        d = ROOT / folder
        d.mkdir(parents=True, exist_ok=True)
        if not names:
            (d / ".gitkeep").touch()
        for n in names.split():
            f = d / n
            if not f.exists():
                write(f, stub(f))
                stubs += 1

    # 3) make every folder under backend/ and engine/ a Python package
    for top in ("backend", "engine"):
        for d in [ROOT / top, *(p for p in (ROOT / top).rglob("*") if p.is_dir())]:
            init = d / "__init__.py"
            if not init.exists():
                write(init, "")
                stubs += 1

    # 4) syntax-check every Python file
    bad = []
    py_files = [p for p in ROOT.rglob("*.py")]
    for p in py_files:
        try:
            compile(p.read_text(encoding="utf-8"), str(p), "exec")
        except SyntaxError as e:
            bad.append(f"{p}: {e}")

    write(ROOT / MANIFEST, json.dumps(manifest, indent=1))

    total_dirs = sum(1 for p in ROOT.rglob("*") if p.is_dir())
    print(f"Done: {ROOT.resolve()}")
    print(f"Folders: {total_dirs} | Real files written: {real} | Updated (.bak saved): {updated} | Stubs created: {stubs} | Kept: {kept}")
    if kept:
        print(f"  {kept} file(s) differ from this version (your edits or an older scaffold) and were left alone.")
        print("  To overwrite them with this version (old copies saved as .bak):  python scaffold.py " + str(ROOT) + " --update")
    print(f"Python check: {'OK' if not bad else 'ERRORS'} ({len(py_files)} files)")
    for b in bad:
        print("  " + b)
    print(f"\nRun:  cd {ROOT} && pip install flask && python run.py   ->  http://127.0.0.1:5000")


if __name__ == "__main__":
    main()
