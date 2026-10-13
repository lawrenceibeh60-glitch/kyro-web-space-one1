"""Stable depth sorting for parallax and compositing."""


def sort_by_depth(items, *, key="depth", reverse=False):
    return [item for _, item in sorted(
        enumerate(items),
        key=lambda pair: (pair[1].get(key, 1.0), pair[0]),
        reverse=reverse,
    )]
