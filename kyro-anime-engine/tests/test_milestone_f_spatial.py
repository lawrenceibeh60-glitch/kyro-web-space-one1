"""Milestone F: 3D spatial transforms, perspective camera, quaternion interpolation.

Tests the cinematic 3D production upgrade foundations:
- 4x4 matrix operations (translation, rotation, scaling, perspective)
- Extended Camera with z, rotation_x/y, fov, clip planes, aperture
- Perspective projection
- Quaternion-based camera interpolation (no gimbal lock)
- Schema validation for 3D transform fields and cinematic camera
- Backward compatibility: existing 2D projects validate unchanged
"""
import json
import math
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "formats" / "schemas"


def _load(name):
    with open(SCHEMAS_DIR / name) as f:
        return json.load(f)


SCENE_SCHEMA = _load("scene.schema.json")
ANIMATION_SCHEMA = _load("animation.schema.json")
DRAWING_SCHEMA = _load("drawing.schema.json")
STYLE_SCHEMA = _load("style.schema.json")

_REGISTRY = Registry().with_resources(
    [
        ("scene.schema.json", Resource.from_contents(SCENE_SCHEMA)),
        ("animation.schema.json", Resource.from_contents(ANIMATION_SCHEMA)),
        ("drawing.schema.json", Resource.from_contents(DRAWING_SCHEMA)),
        ("style.schema.json", Resource.from_contents(STYLE_SCHEMA)),
    ]
)
VALIDATOR = Draft202012Validator(SCENE_SCHEMA, registry=_REGISTRY)


class TestMatrices4x4(unittest.TestCase):
    """Test 4x4 matrix math for 3D spatial transforms."""

    def test_identity_4x4(self):
        from engine.math.matrices import IDENTITY_4X4, transform_point_3d
        result = transform_point_3d(IDENTITY_4X4, (5, 10, 15))
        self.assertAlmostEqual(result[0], 5.0)
        self.assertAlmostEqual(result[1], 10.0)
        self.assertAlmostEqual(result[2], 15.0)

    def test_translation_3d(self):
        from engine.math.matrices import translation_3d, transform_point_3d
        m = translation_3d(10, 20, 30)
        result = transform_point_3d(m, (0, 0, 0))
        self.assertAlmostEqual(result[0], 10.0)
        self.assertAlmostEqual(result[1], 20.0)
        self.assertAlmostEqual(result[2], 30.0)

    def test_scaling_3d(self):
        from engine.math.matrices import scaling_3d, transform_point_3d
        m = scaling_3d(2, 3, 4)
        result = transform_point_3d(m, (1, 1, 1))
        self.assertAlmostEqual(result[0], 2.0)
        self.assertAlmostEqual(result[1], 3.0)
        self.assertAlmostEqual(result[2], 4.0)

    def test_scaling_uniform(self):
        from engine.math.matrices import scaling_3d, transform_point_3d
        m = scaling_3d(2)
        result = transform_point_3d(m, (1, 2, 3))
        self.assertAlmostEqual(result[0], 2.0)
        self.assertAlmostEqual(result[1], 4.0)
        self.assertAlmostEqual(result[2], 6.0)

    def test_rotation_z_90(self):
        from engine.math.matrices import rotation_z, transform_point_3d
        m = rotation_z(math.pi / 2)
        result = transform_point_3d(m, (1, 0, 0))
        self.assertAlmostEqual(result[0], 0.0, places=5)
        self.assertAlmostEqual(result[1], 1.0, places=5)
        self.assertAlmostEqual(result[2], 0.0, places=5)

    def test_rotation_x_90(self):
        from engine.math.matrices import rotation_x, transform_point_3d
        m = rotation_x(math.pi / 2)
        result = transform_point_3d(m, (0, 1, 0))
        self.assertAlmostEqual(result[0], 0.0, places=5)
        self.assertAlmostEqual(result[1], 0.0, places=5)
        self.assertAlmostEqual(result[2], 1.0, places=5)

    def test_rotation_y_90(self):
        from engine.math.matrices import rotation_y, transform_point_3d
        m = rotation_y(math.pi / 2)
        result = transform_point_3d(m, (0, 0, 1))
        self.assertAlmostEqual(result[0], 1.0, places=5)
        self.assertAlmostEqual(result[1], 0.0, places=5)
        self.assertAlmostEqual(result[2], 0.0, places=5)

    def test_multiply_4x4_identity(self):
        from engine.math.matrices import IDENTITY_4X4, multiply_4x4, translation_3d
        m = translation_3d(5, 10, 15)
        result = multiply_4x4(IDENTITY_4X4, m)
        for r in range(4):
            for c in range(4):
                self.assertAlmostEqual(result[r][c], m[r][c])

    def test_compose_translate_then_scale(self):
        from engine.math.matrices import translation_3d, scaling_3d, multiply_4x4, transform_point_3d
        t = translation_3d(10, 0, 0)
        s = scaling_3d(2)
        combined = multiply_4x4(s, t)
        result = transform_point_3d(combined, (0, 0, 0))
        self.assertAlmostEqual(result[0], 20.0)

    def test_perspective_projection_valid(self):
        from engine.math.matrices import perspective_projection
        m = perspective_projection(math.radians(60), 16 / 9, 0.1, 1000)
        self.assertEqual(len(m), 4)
        self.assertEqual(len(m[0]), 4)
        # m[3][2] should be -1 for standard perspective
        self.assertAlmostEqual(m[3][2], -1.0)

    def test_perspective_invalid_clips_raises(self):
        from engine.math.matrices import perspective_projection
        with self.assertRaises(ValueError):
            perspective_projection(math.radians(60), 1.0, 100, 10)

    def test_orthographic_projection(self):
        from engine.math.matrices import orthographic_projection
        m = orthographic_projection(-10, 10, -10, 10, 0.1, 100)
        self.assertEqual(len(m), 4)
        self.assertAlmostEqual(m[0][0], 0.1)  # 2/(right-left)


class TestCamera3D(unittest.TestCase):
    """Test extended Camera with 3D spatial and cinematic properties."""

    def test_default_backward_compatible(self):
        from engine.camera.camera import Camera
        c = Camera()
        d = c.to_dict()
        self.assertEqual(d["x"], 0)
        self.assertEqual(d["y"], 0)
        self.assertEqual(d["zoom"], 1.0)
        self.assertNotIn("z", d)  # omitted when default
        self.assertNotIn("fov", d)  # omitted when default 60

    def test_3d_properties(self):
        from engine.camera.camera import Camera
        c = Camera(z=100, rotation_x=30, rotation_y=45, fov=90)
        d = c.to_dict()
        self.assertEqual(d["z"], 100)
        self.assertEqual(d["rotation_x"], 30)
        self.assertEqual(d["rotation_y"], 45)
        self.assertEqual(d["fov"], 90)

    def test_dolly(self):
        from engine.camera.camera import Camera
        c = Camera()
        c.dolly(50)
        self.assertEqual(c.z, 50)

    def test_set_fov_clamped(self):
        from engine.camera.camera import Camera
        c = Camera()
        c.set_fov(200)
        self.assertEqual(c.fov, 179.0)
        c.set_fov(-10)
        self.assertEqual(c.fov, 1.0)

    def test_from_dict_2d_project(self):
        from engine.camera.camera import Camera
        c = Camera.from_dict({"x": 100, "y": 200, "zoom": 2.0, "rotation": 45})
        self.assertEqual(c.x, 100)
        self.assertEqual(c.y, 200)
        self.assertEqual(c.zoom, 2.0)
        self.assertEqual(c.rotation, 45)
        self.assertEqual(c.z, 0)  # default

    def test_from_dict_empty(self):
        from engine.camera.camera import Camera
        c = Camera.from_dict(None)
        self.assertEqual(c.x, 0)

    def test_orientation_quaternion_cached(self):
        from engine.camera.camera import Camera
        c = Camera(rotation_x=30, rotation_y=45)
        q1 = c.orientation_quaternion
        q2 = c.orientation_quaternion
        self.assertIs(q1, q2)  # same object, cached

    def test_orientation_quaternion_unit_length(self):
        from engine.camera.camera import Camera
        c = Camera(rotation_x=30, rotation_y=45, rotation=60)
        q = c.orientation_quaternion
        mag = math.sqrt(sum(v * v for v in q))
        self.assertAlmostEqual(mag, 1.0, places=5)

    def test_orbit(self):
        from engine.camera.camera import Camera
        c = Camera(x=100, y=0, z=0)
        c.orbit((0, 0, 0), 90)
        self.assertAlmostEqual(c.x, 0.0, places=3)
        self.assertAlmostEqual(abs(c.z), 100.0, places=3)


class TestPerspectiveProjection(unittest.TestCase):
    """Test 3D to 2D perspective projection."""

    def test_center_point_projects_to_center(self):
        from engine.camera.camera_transform import project_perspective
        camera = {"x": 0, "y": 0, "z": 0, "fov": 60, "rotation": 0,
                  "rotation_x": 0, "rotation_y": 0, "near_clip": 0.1, "far_clip": 1000}
        result = project_perspective((0, 0, -100), camera, viewport_size=(1280, 720))
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result[0], 640.0, places=1)
        self.assertAlmostEqual(result[1], 360.0, places=1)

    def test_behind_camera_returns_none(self):
        from engine.camera.camera_transform import project_perspective
        camera = {"x": 0, "y": 0, "z": 0, "fov": 60, "near_clip": 0.1, "far_clip": 1000}
        result = project_perspective((0, 0, 10), camera)  # behind camera
        self.assertIsNone(result)

    def test_depth_value_positive(self):
        from engine.camera.camera_transform import project_perspective
        camera = {"x": 0, "y": 0, "z": 0, "fov": 60, "near_clip": 0.1, "far_clip": 1000}
        result = project_perspective((0, 0, -50), camera)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result[2], 50.0, places=1)

    def test_parallax_offset_objects_at_different_depths(self):
        from engine.camera.camera_transform import project_perspective
        camera = {"x": 10, "y": 0, "z": 0, "fov": 60, "near_clip": 0.1, "far_clip": 1000}
        near = project_perspective((0, 0, -10), camera, viewport_size=(1280, 720))
        far = project_perspective((0, 0, -100), camera, viewport_size=(1280, 720))
        self.assertIsNotNone(near)
        self.assertIsNotNone(far)
        # Near object shifts more on screen than far object when camera moves
        self.assertGreater(abs(near[0] - 640), abs(far[0] - 640))


class TestCameraInterpolation(unittest.TestCase):
    """Test smooth camera interpolation with quaternion slerp."""

    def test_interpolate_position_linear(self):
        from engine.camera.camera_transform import interpolate_camera
        a = {"x": 0, "y": 0, "z": 0}
        b = {"x": 100, "y": 200, "z": 50}
        mid = interpolate_camera(a, b, 0.5)
        self.assertAlmostEqual(mid["x"], 50.0)
        self.assertAlmostEqual(mid["y"], 100.0)
        self.assertAlmostEqual(mid["z"], 25.0)

    def test_interpolate_endpoints(self):
        from engine.camera.camera_transform import interpolate_camera
        a = {"x": 0, "y": 0, "zoom": 1}
        b = {"x": 100, "y": 100, "zoom": 2}
        start = interpolate_camera(a, b, 0)
        end = interpolate_camera(a, b, 1)
        self.assertAlmostEqual(start["x"], 0.0)
        self.assertAlmostEqual(end["x"], 100.0)
        self.assertAlmostEqual(start["zoom"], 1.0)
        self.assertAlmostEqual(end["zoom"], 2.0)

    def test_interpolate_fov(self):
        from engine.camera.camera_transform import interpolate_camera
        a = {"fov": 30}
        b = {"fov": 90}
        mid = interpolate_camera(a, b, 0.5)
        self.assertAlmostEqual(mid["fov"], 60.0)

    def test_interpolate_2d_rotation_shortest_path(self):
        from engine.camera.camera_transform import interpolate_camera
        a = {"rotation": 350}
        b = {"rotation": 10}
        mid = interpolate_camera(a, b, 0.5)
        # 350->10 shortest path goes through 360/0; midpoint is 360 or 0
        normalized = mid["rotation"] % 360
        self.assertTrue(normalized < 10 or normalized > 350)

    def test_interpolate_3d_rotation_no_flip(self):
        from engine.camera.camera_transform import interpolate_camera
        a = {"rotation_x": 0, "rotation_y": 0, "rotation": 0}
        b = {"rotation_x": 90, "rotation_y": 90, "rotation": 0}
        mid = interpolate_camera(a, b, 0.5)
        # Should produce smooth intermediate values, no sudden jumps
        self.assertTrue(-180 <= mid["rotation_x"] <= 180)
        self.assertTrue(-180 <= mid["rotation_y"] <= 180)

    def test_interpolate_with_camera_objects(self):
        from engine.camera.camera import Camera
        from engine.camera.camera_transform import interpolate_camera
        a = Camera(x=0, y=0, z=0)
        b = Camera(x=100, y=100, z=50)
        mid = interpolate_camera(a, b, 0.5)
        self.assertAlmostEqual(mid["x"], 50.0)
        self.assertAlmostEqual(mid["z"], 25.0)


class TestSceneSchema3D(unittest.TestCase):
    """Test that scene schema accepts 3D spatial fields."""

    def _minimal_scene(self, **overrides):
        scene = {
            "id": "test_scene",
            "layers": [],
        }
        scene.update(overrides)
        return scene

    def test_transform_with_z(self):
        scene = self._minimal_scene(layers=[{
            "id": "l1", "type": "drawing",
            "transform": {"x": 0, "y": 0, "z": 100}
        }])
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertEqual(errors, [])

    def test_transform_with_3d_rotations(self):
        scene = self._minimal_scene(layers=[{
            "id": "l1", "type": "drawing",
            "transform": {"rotation_x": 30, "rotation_y": 45, "rotation": 90}
        }])
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertEqual(errors, [])

    def test_transform_with_scale_z(self):
        scene = self._minimal_scene(layers=[{
            "id": "l1", "type": "drawing",
            "transform": {"scale_z": 2.0}
        }])
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertEqual(errors, [])

    def test_camera_with_lens(self):
        scene = self._minimal_scene(camera={
            "transform": {"x": 0, "y": 0, "z": 100},
            "lens": {"fov": 75, "near_clip": 0.5, "far_clip": 5000, "projection": "perspective"}
        })
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertEqual(errors, [])

    def test_camera_with_dof(self):
        scene = self._minimal_scene(camera={
            "depth_of_field": {"focus_distance": 50, "aperture": 0.3}
        })
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertEqual(errors, [])

    def test_camera_with_tracks_3d(self):
        scene = self._minimal_scene(camera={
            "tracks": {
                "z": [{"t": 0, "v": 0}, {"t": 24, "v": 100}],
                "fov": [{"t": 0, "v": 60}, {"t": 24, "v": 90}],
                "rotation_y": [{"t": 0, "v": 0}, {"t": 24, "v": 45}]
            }
        })
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertEqual(errors, [])

    def test_light_with_type_and_3d(self):
        scene = self._minimal_scene(lights=[{
            "id": "sun", "x": 0, "y": 0, "radius": 500,
            "intensity": 0.8, "color": "#ffffff",
            "type": "directional", "z": 100,
            "cast_shadows": True
        }])
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertEqual(errors, [])

    def test_backward_compat_2d_project(self):
        """Existing bouncing ball project format must still validate."""
        scene = {
            "id": "scene_1",
            "camera": {
                "transform": {"x": 0, "y": 0, "scale_x": 1, "scale_y": 1}
            },
            "layers": [
                {
                    "id": "layer_ball",
                    "type": "drawing",
                    "transform": {"x": 200, "y": 560},
                    "exposures": [{"start": 0, "length": 24, "drawing": "d_ball"}],
                    "depth": 1.2
                }
            ],
            "lights": [
                {"id": "light_sun", "x": 930, "y": 178, "radius": 520, "intensity": 0.3, "color": "#fff0b3"}
            ]
        }
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertEqual(errors, [])

    def test_invalid_projection_type_rejected(self):
        scene = self._minimal_scene(camera={
            "lens": {"projection": "fisheye"}
        })
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertTrue(len(errors) > 0)

    def test_invalid_light_type_rejected(self):
        scene = self._minimal_scene(lights=[{
            "id": "l1", "x": 0, "y": 0, "radius": 100,
            "intensity": 0.5, "color": "#ffffff", "type": "laser"
        }])
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertTrue(len(errors) > 0)


if __name__ == "__main__":
    unittest.main()
