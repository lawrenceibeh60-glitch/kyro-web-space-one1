"""Uniform-grid point index for fast viewport hit-testing."""
import math


class SpatialIndex:
    def __init__(self, cell_size=64):
        if cell_size <= 0:
            raise ValueError("cell_size must be positive")
        self.cell_size = float(cell_size)
        self._cells = {}
        self._items = {}

    def _cell(self, point):
        return (math.floor(point[0] / self.cell_size), math.floor(point[1] / self.cell_size))

    def insert(self, key, point, value=None):
        self.remove(key)
        point = tuple(point[:2])
        cell = self._cell(point)
        self._items[key] = (point, value)
        self._cells.setdefault(cell, set()).add(key)

    def remove(self, key):
        entry = self._items.pop(key, None)
        if entry is None:
            return False
        cell = self._cell(entry[0])
        self._cells[cell].discard(key)
        if not self._cells[cell]:
            del self._cells[cell]
        return True

    def query(self, point, radius=0):
        min_cell = self._cell((point[0] - radius, point[1] - radius))
        max_cell = self._cell((point[0] + radius, point[1] + radius))
        matches = []
        for x in range(min_cell[0], max_cell[0] + 1):
            for y in range(min_cell[1], max_cell[1] + 1):
                for key in self._cells.get((x, y), ()):
                    position, value = self._items[key]
                    if (position[0] - point[0]) ** 2 + (position[1] - point[1]) ** 2 <= radius ** 2:
                        matches.append((key, value, position))
        return sorted(matches, key=lambda match: (match[2][0] - point[0]) ** 2 + (match[2][1] - point[1]) ** 2)
