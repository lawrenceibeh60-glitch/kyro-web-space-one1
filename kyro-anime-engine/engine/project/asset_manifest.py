"""Build asset inventories and reference usage summaries for KAE documents."""
from engine.data.reference_resolver import iter_references


def build_asset_manifest(project):
    usages = {}
    for reference in iter_references(project):
        usages.setdefault(reference["target"], []).append(reference["source"])
    return [
        {
            "id": drawing_id,
            "name": drawing.get("name", drawing_id),
            "kind": "drawing",
            "references": usages.get(drawing_id, []),
        }
        for drawing_id, drawing in project.get("drawings", {}).items()
    ]


def unused_assets(project):
    return [asset for asset in build_asset_manifest(project) if not asset["references"]]
