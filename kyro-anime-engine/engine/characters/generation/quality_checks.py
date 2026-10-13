"""Validate generated component geometry and character completeness."""


def check_polygon(points):
    issues = []
    if len(points) < 3:
        issues.append("Polygon requires at least three points")
    if len(set(map(tuple, points))) != len(points):
        issues.append("Polygon contains duplicate vertices")
    return issues


def check_character(character, required=("head", "body")):
    components = character.get("components", {})
    return [f"Missing required component: {name}" for name in required if name not in components]
