"""Project load entry point combining parsing, migration and validation."""
from engine.data.json_loader import load_project_document
from engine.project.project_migration import migrate_project
from engine.project.project_validator import require_valid_project


def load_project(path, *, validate=True):
    project = migrate_project(load_project_document(path))
    return require_valid_project(project) if validate else project
