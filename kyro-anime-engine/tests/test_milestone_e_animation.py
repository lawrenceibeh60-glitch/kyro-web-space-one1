"""Milestone E: Advanced animation - rig constraints, IK solver, deformation, pose evaluation.

Tests the 2D two-bone IK solver, constraint functions, bone-weighted deformation,
forward kinematics chain evaluation, skeleton validation, pose library, and rig schema.
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


RIG_SCHEMA = _load("rig.schema.json")
ANIMATION_SCHEMA = _load("animation.schema.json")

_REGISTRY = Registry().with_resources(
    [
        ("rig.schema.json", Resource.from_contents(RIG_SCHEMA)),
        ("animation.schema.json", Resource.from_contents(ANIMATION_SCHEMA)),
    ]
)
VALIDATOR = Draft202012Validator(RIG_SCHEMA, registry=_REGISTRY)


class TestRigSchema(unittest.TestCase):
    """Validate rig.schema.json structure."""

    def _valid_rig(self):
        return {
            "id": "rig_1",
            "character_id": "char_1",
            "bones": [
                {
                    "id": "hip",
                    "name": "Hip",
                    "character_part_id": "body",
                    "pivot": {"x": 0, "y": 0},
                    "rotation": 0,
                },
                {
                    "id": "spine",
                    "name": "Spine",
                    "character_part_id": "body",
                    "parent_id": "hip",
                    "pivot": {"x": 0, "y": -50},
                    "rotation": 0,
                    "length": 50,
                },
            ],
        }

    def test_valid_rig_passes(self):
        errors = list(VALIDATOR.iter_errors(self._valid_rig()))
        self.assertEqual(errors, [])

    def test_missing_character_id_fails(self):
        rig = self._valid_rig()
        del rig["character_id"]
        errors = list(VALIDATOR.iter_errors(rig))
        self.assertTrue(len(errors) > 0)

    def test_bone_missing_pivot_fails(self):
        rig = self._valid_rig()
        del rig["bones"][0]["pivot"]
        errors = list(VALIDATOR.iter_errors(rig))
        self.assertTrue(len(errors) > 0)

    def test_invalid_constraint_type_fails(self):
        rig = self._valid_rig()
        rig["constraints"] = [{"type": "invalid_type", "bone_id": "hip"}]
        errors = list(VALIDATOR.iter_errors(rig))
        self.assertTrue(len(errors) > 0)

    def test_valid_constraint_passes(self):
        rig = self._valid_rig()
        rig["constraints"] = [
            {"type": "rotation_limit", "bone_id": "spine", "min": -45, "max": 45}
        ]
        errors = list(VALIDATOR.iter_errors(rig))
        self.assertEqual(errors, [])

    def test_ik_constraint_with_bend_direction(self):
        rig = self._valid_rig()
        rig["constraints"] = [
            {
                "type": "ik_two_bone",
                "bone_id": "hip",
                "target_bone_id": "spine",
                "bend_direction": 1,
                "weight": 0.8,
            }
        ]
        errors = list(VALIDATOR.iter_errors(rig))
        self.assertEqual(errors, [])

    def test_additional_properties_rejected(self):
        rig = self._valid_rig()
        rig["unknown_field"] = True
        errors = list(VALIDATOR.iter_errors(rig))
        self.assertTrue(len(errors) > 0)


class TestTwoBoneIK(unittest.TestCase):
    """Test engine.rigging.inverse_kinematics.solve_two_bone."""

    def test_reachable_target(self):
        from engine.rigging.inverse_kinematics import solve_two_bone

        result = solve_two_bone((0, 0), (80, 0), 50, 50)
        self.assertTrue(result["reachable"])
        self.assertAlmostEqual(result["end"][0], 80, places=3)
        self.assertAlmostEqual(result["end"][1], 0, places=3)

    def test_unreachable_target_clamped(self):
        from engine.rigging.inverse_kinematics import solve_two_bone

        result = solve_two_bone((0, 0), (200, 0), 50, 50)
        self.assertFalse(result["reachable"])
        # End should be clamped to max reach
        dist = math.hypot(result["end"][0], result["end"][1])
        self.assertAlmostEqual(dist, 100, places=3)

    def test_zero_distance_target(self):
        from engine.rigging.inverse_kinematics import solve_two_bone

        result = solve_two_bone((10, 20), (10, 20), 50, 50)
        self.assertFalse(result["reachable"])

    def test_bend_direction_negative(self):
        from engine.rigging.inverse_kinematics import solve_two_bone

        pos = solve_two_bone((0, 0), (60, 0), 50, 50, bend=1)
        neg = solve_two_bone((0, 0), (60, 0), 50, 50, bend=-1)
        # Joint y should be opposite signs for opposite bend directions
        self.assertLess(pos["joint"][1] * neg["joint"][1], 1e-9)
        self.assertNotAlmostEqual(pos["joint"][1], neg["joint"][1], places=1)

    def test_zero_length_raises(self):
        from engine.rigging.inverse_kinematics import solve_two_bone

        with self.assertRaises(ValueError):
            solve_two_bone((0, 0), (50, 0), 0, 50)

    def test_angles_in_degrees(self):
        from engine.rigging.inverse_kinematics import solve_two_bone

        result = solve_two_bone((0, 0), (100, 0), 50, 50)
        # Fully stretched: root angle ~0, joint angle ~0 (pi - acos(1) = 0)
        self.assertAlmostEqual(result["root_angle"], 0.0, places=1)
        self.assertAlmostEqual(abs(result["joint_angle"]), 0.0, places=1)


class TestConstraints(unittest.TestCase):
    """Test engine.rigging.constraints functions."""

    def test_clamp_rotation_within_range(self):
        from engine.rigging.constraints import clamp_rotation

        self.assertEqual(clamp_rotation(30, -90, 90), 30)

    def test_clamp_rotation_exceeds_max(self):
        from engine.rigging.constraints import clamp_rotation

        self.assertEqual(clamp_rotation(120, -90, 90), 90)

    def test_clamp_rotation_below_min(self):
        from engine.rigging.constraints import clamp_rotation

        self.assertEqual(clamp_rotation(-100, -90, 90), -90)

    def test_clamp_rotation_invalid_range(self):
        from engine.rigging.constraints import clamp_rotation

        with self.assertRaises(ValueError):
            clamp_rotation(0, 90, -90)

    def test_constrain_distance_within_limits(self):
        from engine.rigging.constraints import constrain_distance

        result = constrain_distance((3, 4), (0, 0), 0, 10)
        self.assertAlmostEqual(math.hypot(result[0], result[1]), 5.0, places=5)

    def test_constrain_distance_clamps_to_max(self):
        from engine.rigging.constraints import constrain_distance

        result = constrain_distance((10, 0), (0, 0), 0, 5)
        self.assertAlmostEqual(math.hypot(result[0], result[1]), 5.0, places=5)

    def test_constrain_distance_clamps_to_min(self):
        from engine.rigging.constraints import constrain_distance

        result = constrain_distance((1, 0), (0, 0), 3, 10)
        self.assertAlmostEqual(math.hypot(result[0], result[1]), 3.0, places=5)

    def test_pin_full_weight(self):
        from engine.rigging.constraints import pin

        result = pin((0, 0), (10, 10), 1.0)
        self.assertAlmostEqual(result[0], 10.0, places=5)
        self.assertAlmostEqual(result[1], 10.0, places=5)

    def test_pin_half_weight(self):
        from engine.rigging.constraints import pin

        result = pin((0, 0), (10, 10), 0.5)
        self.assertAlmostEqual(result[0], 5.0, places=5)
        self.assertAlmostEqual(result[1], 5.0, places=5)

    def test_pin_zero_weight(self):
        from engine.rigging.constraints import pin

        result = pin((3, 7), (10, 10), 0.0)
        self.assertAlmostEqual(result[0], 3.0, places=5)
        self.assertAlmostEqual(result[1], 7.0, places=5)


class TestDeformation(unittest.TestCase):
    """Test engine.rigging.deformation weighted bone transforms."""

    def test_single_bone_translation(self):
        from engine.rigging.deformation import deform_point

        point = (10, 0)
        influences = [("bone1", 1.0)]
        transforms = {"bone1": {"x": 5, "y": 0, "rotation": 0}}
        result = deform_point(point, influences, transforms)
        self.assertAlmostEqual(result[0], 15.0, places=3)
        self.assertAlmostEqual(result[1], 0.0, places=3)

    def test_single_bone_rotation_90(self):
        from engine.rigging.deformation import deform_point

        point = (10, 0)
        influences = [("bone1", 1.0)]
        transforms = {"bone1": {"x": 0, "y": 0, "rotation": 90}}
        result = deform_point(point, influences, transforms)
        self.assertAlmostEqual(result[0], 0.0, places=3)
        self.assertAlmostEqual(result[1], 10.0, places=3)

    def test_two_bone_blend(self):
        from engine.rigging.deformation import deform_point

        point = (10, 0)
        influences = [("b1", 0.5), ("b2", 0.5)]
        transforms = {
            "b1": {"x": 10, "y": 0, "rotation": 0},
            "b2": {"x": 0, "y": 0, "rotation": 0},
        }
        result = deform_point(point, influences, transforms)
        self.assertAlmostEqual(result[0], 15.0, places=3)

    def test_no_influences_returns_original(self):
        from engine.rigging.deformation import deform_point

        result = deform_point((5, 10), [], {})
        self.assertEqual(result, (5, 10))

    def test_deform_points_batch(self):
        from engine.rigging.deformation import deform_points

        points = [(0, 0), (10, 0)]
        weights = {0: [("b1", 1.0)], 1: [("b1", 1.0)]}
        transforms = {"b1": {"x": 5, "y": 0, "rotation": 0}}
        result = deform_points(points, weights, transforms)
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0][0], 5.0, places=3)
        self.assertAlmostEqual(result[1][0], 15.0, places=3)

    def test_zero_weight_ignored(self):
        from engine.rigging.deformation import deform_point

        point = (10, 0)
        influences = [("b1", 0.0)]
        transforms = {"b1": {"x": 100, "y": 0, "rotation": 0}}
        result = deform_point(point, influences, transforms)
        self.assertAlmostEqual(result[0], 10.0, places=3)


class TestForwardKinematics(unittest.TestCase):
    """Test engine.rigging.forward_kinematics.evaluate."""

    def test_single_bone_no_parent(self):
        from engine.rigging.forward_kinematics import evaluate

        bones = [{"id": "root", "pivot": {"x": 10, "y": 20}, "rotation": 0}]
        result = evaluate(bones)
        self.assertAlmostEqual(result["root"]["x"], 10.0, places=3)
        self.assertAlmostEqual(result["root"]["y"], 20.0, places=3)
        self.assertAlmostEqual(result["root"]["rotation"], 0.0, places=3)

    def test_child_inherits_parent_rotation(self):
        from engine.rigging.forward_kinematics import evaluate

        bones = [
            {"id": "parent", "pivot": {"x": 0, "y": 0}, "rotation": 90},
            {"id": "child", "parent_id": "parent", "pivot": {"x": 50, "y": 0}, "rotation": 0},
        ]
        result = evaluate(bones)
        # Child pivot (50,0) rotated 90 degrees -> (0,50)
        self.assertAlmostEqual(result["child"]["x"], 0.0, places=3)
        self.assertAlmostEqual(result["child"]["y"], 50.0, places=3)
        self.assertAlmostEqual(result["child"]["rotation"], 90.0, places=3)

    def test_pose_overrides_rotation(self):
        from engine.rigging.forward_kinematics import evaluate

        bones = [{"id": "b1", "pivot": {"x": 0, "y": 0}, "rotation": 0}]
        pose = {"b1": {"rotation": 45}}
        result = evaluate(bones, pose)
        self.assertAlmostEqual(result["b1"]["rotation"], 45.0, places=3)

    def test_chain_accumulates_rotation(self):
        from engine.rigging.forward_kinematics import evaluate

        bones = [
            {"id": "a", "pivot": {"x": 0, "y": 0}, "rotation": 30},
            {"id": "b", "parent_id": "a", "pivot": {"x": 0, "y": 0}, "rotation": 20},
        ]
        result = evaluate(bones)
        self.assertAlmostEqual(result["b"]["rotation"], 50.0, places=3)


class TestSkeleton(unittest.TestCase):
    """Test engine.rigging.skeleton.Skeleton validation."""

    def test_valid_skeleton(self):
        from engine.rigging.skeleton import Skeleton

        skel = Skeleton([
            {"id": "hip", "pivot": {"x": 0, "y": 0}},
            {"id": "spine", "parent_id": "hip", "pivot": {"x": 0, "y": -50}},
        ])
        self.assertTrue(skel.validate())

    def test_duplicate_ids_rejected(self):
        from engine.rigging.skeleton import Skeleton
        from engine.core.errors import ValidationError

        with self.assertRaises(ValidationError):
            Skeleton([
                {"id": "hip", "pivot": {"x": 0, "y": 0}},
                {"id": "hip", "pivot": {"x": 0, "y": 0}},
            ])

    def test_self_parent_rejected(self):
        from engine.rigging.skeleton import Skeleton
        from engine.core.errors import ValidationError

        with self.assertRaises(ValidationError):
            Skeleton([{"id": "hip", "parent_id": "hip", "pivot": {"x": 0, "y": 0}}])

    def test_cycle_rejected(self):
        from engine.rigging.skeleton import Skeleton
        from engine.core.errors import ValidationError

        with self.assertRaises(ValidationError):
            Skeleton([
                {"id": "a", "parent_id": "b", "pivot": {"x": 0, "y": 0}},
                {"id": "b", "parent_id": "a", "pivot": {"x": 0, "y": 0}},
            ])

    def test_dangling_parent_rejected(self):
        from engine.rigging.skeleton import Skeleton
        from engine.core.errors import ValidationError

        with self.assertRaises(ValidationError):
            Skeleton([{"id": "a", "parent_id": "nonexistent", "pivot": {"x": 0, "y": 0}}])

    def test_roots_returns_parentless_bones(self):
        from engine.rigging.skeleton import Skeleton

        skel = Skeleton([
            {"id": "hip", "pivot": {"x": 0, "y": 0}},
            {"id": "spine", "parent_id": "hip", "pivot": {"x": 0, "y": 0}},
        ])
        roots = skel.roots()
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0]["id"], "hip")

    def test_get_bone_by_id(self):
        from engine.rigging.skeleton import Skeleton

        skel = Skeleton([{"id": "hip", "pivot": {"x": 0, "y": 0}}])
        self.assertIsNotNone(skel.get("hip"))
        self.assertIsNone(skel.get("missing"))


class TestPoseLibrary(unittest.TestCase):
    """Test engine.rigging.pose_library.PoseLibrary."""

    def test_save_and_get(self):
        from engine.rigging.pose_library import PoseLibrary

        lib = PoseLibrary()
        lib.save("rest", {"name": "rest", "bones": {"hip": {"rotation": 0}}})
        pose = lib.get("rest")
        self.assertEqual(pose["bones"]["hip"]["rotation"], 0)

    def test_get_returns_deep_copy(self):
        from engine.rigging.pose_library import PoseLibrary

        lib = PoseLibrary()
        lib.save("rest", {"name": "rest", "bones": {"hip": {"rotation": 0}}})
        p1 = lib.get("rest")
        p1["bones"]["hip"]["rotation"] = 99
        p2 = lib.get("rest")
        self.assertEqual(p2["bones"]["hip"]["rotation"], 0)

    def test_delete_existing(self):
        from engine.rigging.pose_library import PoseLibrary

        lib = PoseLibrary()
        lib.save("rest", {"name": "rest", "bones": {}})
        self.assertTrue(lib.delete("rest"))
        self.assertIsNone(lib.get("rest"))

    def test_delete_nonexistent(self):
        from engine.rigging.pose_library import PoseLibrary

        lib = PoseLibrary()
        self.assertFalse(lib.delete("nope"))

    def test_names_listing(self):
        from engine.rigging.pose_library import PoseLibrary

        lib = PoseLibrary()
        lib.save("a", {"name": "a", "bones": {}})
        lib.save("b", {"name": "b", "bones": {}})
        self.assertIn("a", lib.names())
        self.assertIn("b", lib.names())

    def test_empty_name_rejected(self):
        from engine.rigging.pose_library import PoseLibrary

        lib = PoseLibrary()
        with self.assertRaises(ValueError):
            lib.save("", {"name": "", "bones": {}})


class TestPose(unittest.TestCase):
    """Test engine.rigging.pose.Pose data class."""

    def test_set_and_get_rotation(self):
        from engine.rigging.pose import Pose

        p = Pose()
        p.set_rotation("hip", 45)
        self.assertEqual(p.rotation("hip"), 45.0)

    def test_default_rotation_zero(self):
        from engine.rigging.pose import Pose

        p = Pose()
        self.assertEqual(p.rotation("missing"), 0)

    def test_to_dict(self):
        from engine.rigging.pose import Pose

        p = Pose(name="test")
        p.set_rotation("hip", 30)
        d = p.to_dict()
        self.assertEqual(d["name"], "test")
        self.assertEqual(d["bones"]["hip"]["rotation"], 30.0)


if __name__ == "__main__":
    unittest.main()
