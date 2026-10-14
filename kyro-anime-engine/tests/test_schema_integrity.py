import json
import unittest
from pathlib import Path


SCHEMA_DIR = Path(__file__).parents[1] / "formats" / "schemas"


def _references(value):
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str):
            yield ref
        for child in value.values():
            yield from _references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _references(child)


def _resolve_pointer(document, pointer):
    current = document
    if not pointer:
        return current
    if not pointer.startswith("/"):
        raise AssertionError(f"Unsupported JSON Schema pointer: #{pointer}")
    for raw_part in pointer[1:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(part)]
        else:
            current = current[part]
    return current


class SchemaIntegrityTests(unittest.TestCase):
    def test_all_schema_documents_are_valid_json_and_references_resolve(self):
        schemas = sorted(SCHEMA_DIR.glob("*.schema.json"))
        self.assertTrue(schemas, "No KAE schemas were found")
        documents = {path.name: json.loads(path.read_text(encoding="utf-8")) for path in schemas}

        for source_path in schemas:
            with self.subTest(schema=source_path.name):
                for reference in _references(documents[source_path.name]):
                    file_part, separator, pointer = reference.partition("#")
                    target_path = (SCHEMA_DIR / file_part).resolve() if file_part else source_path.resolve()
                    self.assertTrue(target_path.is_relative_to(SCHEMA_DIR.resolve()), reference)
                    self.assertTrue(target_path.is_file(), f"{source_path.name}: missing {reference}")
                    target = documents.get(target_path.name)
                    if target is None:
                        target = json.loads(target_path.read_text(encoding="utf-8"))
                    if separator:
                        try:
                            _resolve_pointer(target, pointer)
                        except (KeyError, IndexError, ValueError, TypeError) as exc:
                            self.fail(f"{source_path.name}: unresolved {reference}: {exc}")

    def test_camera_supports_independent_horizontal_and_vertical_scale_tracks(self):
        scene = json.loads((SCHEMA_DIR / "scene.schema.json").read_text(encoding="utf-8"))
        camera = scene["$defs"]["camera"]
        transform = camera["properties"]["transform"]["properties"]
        tracks = camera["properties"]["tracks"]["properties"]

        for axis in ("scale_x", "scale_y"):
            with self.subTest(axis=axis):
                self.assertEqual(transform[axis]["minimum"], 0.05)
                self.assertEqual(transform[axis]["maximum"], 32)
                self.assertEqual(tracks[axis]["$ref"], "animation.schema.json#/$defs/track")

    def test_project_reuses_standalone_rig_and_effect_schemas(self):
        project = json.loads((SCHEMA_DIR / "project.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(project["properties"]["rigs"]["items"]["$ref"], "rig.schema.json")
        self.assertEqual(project["properties"]["effects"]["items"]["$ref"], "effects.schema.json")


if __name__ == "__main__":
    unittest.main()
