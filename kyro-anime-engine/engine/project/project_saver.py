"""Validated project save entry point with atomic replacement."""
from engine.data.json_writer import write_project_document


def save_project(path, project, *, validate=True):
    return write_project_document(path, project, validate=validate)
