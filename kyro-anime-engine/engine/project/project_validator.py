"""Canonical KAE project validation facade."""
from backend.services.validation_service import validate_project as _validate_project


def validate_project(project):
    return _validate_project(project)


def require_valid_project(project):
    errors = validate_project(project)
    if errors:
        from engine.core.errors import ValidationError
        raise ValidationError("Project failed validation", errors)
    return project
