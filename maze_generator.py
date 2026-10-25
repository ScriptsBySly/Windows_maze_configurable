from dataclasses import dataclass
import random
from typing import Callable, Optional


@dataclass(frozen=True)
class Maze:
    """A rectangular grid, indexed as maze.cells[row][column]."""

    cells: tuple

    def __post_init__(self):
        rows = tuple(tuple(row) for row in self.cells)
        if not rows or not rows[0]:
            raise ValueError("A maze must contain at least one cell.")
        if any(len(row) != len(rows[0]) for row in rows):
            raise ValueError("Maze rows must all have the same width.")
        if any(cell not in (0, 1) for row in rows for cell in row):
            raise ValueError("Maze cells must be 0 (passage) or 1 (wall).")
        object.__setattr__(self, "cells", rows)

    @property
    def width(self):
        return len(self.cells[0])

    @property
    def height(self):
        return len(self.cells)


_algorithms = {}


# Fix algo name if it is wrong
def _normalize_name(name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Algorithm name must be a nonempty string.")
    return name.strip().lower().replace("-", "_").replace(" ", "_")


# Register algo
def register_algorithm(name: str):
    """Register a generator using @register_algorithm('name')."""
    key = _normalize_name(name)

    def decorator(generator: Callable):
        if key in _algorithms:
            raise ValueError(f"Algorithm {key!r} is already registered.")
        if not callable(generator):
            raise TypeError("A maze generator must be callable.")
        _algorithms[key] = generator
        return generator

    return decorator

# Reply with available algorithms
def available_algorithms():
    """Return registered names, including the unfinished placeholders."""
    return tuple(sorted(_algorithms))


# Generate maze using a registered algorithm
def generate_maze(
    algorithm: str, *, width: int = 16, height: int = 16,
    seed: Optional[int] = None,
) -> Maze:
    """Select an algorithm and validate its returned grid.

    Unknown names raise ValueError. Unfinished algorithms raise
    NotImplementedError. This function does not create any Ursina entities.
    """
    key = _normalize_name(algorithm)
    if key not in _algorithms:
        choices = ", ".join(available_algorithms())
        raise ValueError(f"Unknown maze algorithm {algorithm!r}. Choose from: {choices}")
    for name, value in (("width", width), ("height", height)):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} must be a positive integer.")

    maze = _algorithms[key](width=width, height=height, seed=seed)

    if not isinstance(maze, Maze):
        raise TypeError(f"Algorithm {key!r} must return a Maze.")
    if (maze.width, maze.height) != (width, height):
        raise ValueError(f"Algorithm {key!r} returned the wrong grid dimensions.")
    
    return maze


@register_algorithm("DFS")
def recursive_backtracker(*, width, height, seed):
    """Carve a randomized depth-first maze with a solid outer border.

    Width and height describe the final wall/passage grid, not logical rooms.
    Rooms occupy odd coordinates, with a wall between adjacent rooms. Odd
    dimensions use the space fully; even dimensions leave an extra wall strip
    at the right or bottom. Each dimension must be at least three.
    """
    if width < 3 or height < 3:
        raise ValueError("DFS requires width and height of at least 3.")

    rng = random.Random(seed)
    cells = [[1] * width for _ in range(height)]
    start = (rng.randrange(1, width - 1, 2), rng.randrange(1, height - 1, 2))
    visited = {start}
    cells[start[1]][start[0]] = 0

    def neighbors(cell):
        x, y = cell
        candidates = [
            (nx, ny)
            for nx, ny in ((x + 2, y), (x - 2, y), (x, y + 2), (x, y - 2))
            if 0 < nx < width - 1 and 0 < ny < height - 1
        ]
        rng.shuffle(candidates)
        return iter(candidates)

    # Each stack entry retains a cell's remaining neighbors, just as a
    # recursive call would. This avoids Python's recursion-depth limit.
    stack = [(start, neighbors(start))]
    while stack:
        current, remaining = stack[-1]
        next_cell = next(remaining, None)
        if next_cell is None:
            stack.pop()
            continue
        if next_cell in visited:
            continue

        visited.add(next_cell)
        x, y = current
        nx, ny = next_cell
        cells[(y + ny) // 2][(x + nx) // 2] = 0
        cells[ny][nx] = 0
        stack.append((next_cell, neighbors(next_cell)))

    return Maze(cells)


# @register_algorithm("prim")
# def prim(*, width, height, seed):
#     raise NotImplementedError("prim is not implemented yet.")


# @register_algorithm("kruskal")
# def kruskal(*, width, height, seed):
#     raise NotImplementedError("kruskal is not implemented yet.")


# @register_algorithm("recursive_division")
# def recursive_division(*, width, height, seed):
#     raise NotImplementedError("recursive_division is not implemented yet.")



