"""Schema discovery routes."""
import json
from pathlib import Path

from flask import Blueprint, jsonify

import config

bp = Blueprint("schemas", __name__)


@bp.get("/schemas")
def list_schemas():
    root = config.SCHEMAS_DIR
    items = []
    for path in sorted(root.glob("*.schema.json")):
        items.append({
            "name": path.stem.replace(".schema", ""),
            "path": f"/api/schemas/{path.name}",
            "title": path.name,
        })
    return jsonify(schemas=items)


@bp.get("/schemas/<schema_name>")
def get_schema(schema_name):
    path = config.SCHEMAS_DIR / f"{schema_name}.schema.json"
    if not path.exists():
        return jsonify(error="Schema not found"), 404
    with path.open("r", encoding="utf-8") as f:
        return jsonify(json.load(f))

