"""Compile a KAE JSON document into a normalized, validated runtime document."""
from copy import deepcopy
from engine.data.normalizer import normalize_project
from engine.data.reference_resolver import validate_references


def compile_project(document, *, validate=True):
    project = normalize_project(document)
    diagnostics = []
    if validate:
        from engine.project.project_validator import validate_project
        diagnostics.extend(validate_project(project))
    diagnostics.extend(validate_references(project))
    if diagnostics:
        from engine.core.errors import ValidationError
        raise ValidationError("Project compilation failed", diagnostics)
    return deepcopy(project)
