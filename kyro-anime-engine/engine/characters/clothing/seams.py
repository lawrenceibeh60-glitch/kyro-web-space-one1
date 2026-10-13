"""Seam line generation between matching panel edges."""


def seam_line(start, end, inset=0.0):
    if inset < 0 or inset >= 0.5:
        raise ValueError("inset must be in [0, 0.5)")
    return (tuple(a + (b - a) * inset for a, b in zip(start, end)),
            tuple(b + (a - b) * inset for a, b in zip(start, end)))


def seam_length(start, end):
    return sum((a - b) ** 2 for a, b in zip(start, end)) ** 0.5
