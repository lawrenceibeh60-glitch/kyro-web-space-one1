"""Structural and cross-reference validation for scenes."""


def validate_scene(scene, drawings=None):
    drawings = drawings or {}
    errors = []
    if not isinstance(scene, dict):
        return ["scene: must be an object"]
    if not isinstance(scene.get("id"), str) or not scene["id"]:
        errors.append("scene.id: non-empty string required")
    layers = scene.get("layers")
    if not isinstance(layers, list):
        return errors + ["scene.layers: must be a list"]
    seen = set()
    for index, layer in enumerate(layers):
        where = f"scene.layers[{index}]"
        if not isinstance(layer, dict):
            errors.append(f"{where}: must be an object")
            continue
        layer_id = layer.get("id")
        if not isinstance(layer_id, str) or not layer_id or layer_id in seen:
            errors.append(f"{where}.id: missing or duplicate")
        seen.add(layer_id)
        for exp_index, exposure in enumerate(layer.get("exposures", [])):
            drawing_id = exposure.get("drawing") if isinstance(exposure, dict) else None
            if drawing_id not in drawings:
                errors.append(f"{where}.exposures[{exp_index}].drawing: not found")
    return errors
