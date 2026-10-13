"""Project document loading, normalization, validation and serialization."""
from engine.data.normalizer import normalize_project
from engine.data.serialization import dumps, loads

__all__ = ["normalize_project", "dumps", "loads"]