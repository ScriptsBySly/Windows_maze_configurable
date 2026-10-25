"""Selectable maze solvers, independent of Ursina.

    path = solve_maze('paintbrush', maze, start=(1, 1), end=(13, 13))

Coordinates are (column, row). Paths include both endpoints. An unreachable
goal returns an empty list. Solvers never modify the supplied Maze.
Add solvers with @register_solver('name'); accept maze, start and end keywords
and return a list of adjacent passage coordinates.
"""

from maze_generator import Maze


_solvers = {}
_live_solvers = {}


def _normalize_name(name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError('Solver name must be a nonempty string.')
    return name.strip().lower().replace('-', '_').replace(' ', '_')


def register_solver(name):
    """Register a solver using @register_solver('name')."""
    key = _normalize_name(name)

    def decorator(solver):
        if key in _solvers:
            raise ValueError(f'Solver {key!r} is already registered.')
        if not callable(solver):
            raise TypeError('A maze solver must be callable.')
        _solvers[key] = solver
        return solver

    return decorator


def available_solvers():
    return tuple(sorted(_solvers))


def register_live_solver(name):
    """Register a lazy solver yielding None for work, or a cell to move to."""
    key = _normalize_name(name)

    def decorator(solver):
        if key in _live_solvers:
            raise ValueError(f'Live solver {key!r} is already registered.')
        if not callable(solver):
            raise TypeError('A live maze solver must be callable.')
        _live_solvers[key] = solver
        return solver

    return decorator


def solve_maze_live(algorithm, maze: Maze, *, start, end):
    """Create an iterator without searching ahead.

    Advance it during the frame loop: None means one flood-fill expansion;
    a (column, row) pair means a committed movement decision. Stop advancing
    while moving to that cell. Exhaustion before reaching end means no route.
    Paintbrush has full map knowledge, but computes decisions incrementally.
    """
    key = _normalize_name(algorithm)
    if key not in _live_solvers:
        choices = ', '.join(sorted(_live_solvers))
        raise ValueError(f'Unknown live maze solver {algorithm!r}. Choose from: {choices}')
    if not isinstance(maze, Maze):
        raise TypeError('maze must be a Maze returned by the generator.')
    start = _validate_endpoint(maze, start, 'start')
    end = _validate_endpoint(maze, end, 'end')
    return _live_solvers[key](maze=maze, start=start, end=end)


def _validate_endpoint(maze, point, name):
    if (not isinstance(point, (tuple, list)) or len(point) != 2
            or any(type(value) is not int for value in point)):
        raise ValueError(f'{name} must be a (column, row) pair of integers.')
    x, y = point
    if not (0 <= x < maze.width and 0 <= y < maze.height):
        raise ValueError(f'{name} lies outside the maze.')
    if maze.cells[y][x] != 0:
        raise ValueError(f'{name} must be a passage, not a wall.')
    return (x, y)


def solve_maze(algorithm, maze: Maze, *, start, end):
    """Return a path, or [] if no route exists; invalid inputs raise errors."""
    key = _normalize_name(algorithm)
    if key not in _solvers:
        choices = ', '.join(available_solvers())
        raise ValueError(f'Unknown maze solver {algorithm!r}. Choose from: {choices}')
    if not isinstance(maze, Maze):
        raise TypeError('maze must be a Maze returned by the generator.')
    start = _validate_endpoint(maze, start, 'start')
    end = _validate_endpoint(maze, end, 'end')
    path = _solvers[key](maze=maze, start=start, end=end)
    if not isinstance(path, list):
        raise TypeError(f'Solver {key!r} must return a list of coordinates.')
    if path:
        if path[0] != start or path[-1] != end:
            raise ValueError(f'Solver {key!r} returned incorrect endpoints.')
        for point in path:
            _validate_endpoint(maze, point, 'path coordinate')
        for a, b in zip(path, path[1:]):
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
                raise ValueError(f'Solver {key!r} returned nonadjacent steps.')
    return path


@register_solver('paintbrush')
def paintbrush(*, maze, start, end):
    """Collect the incremental solver's decisions for callers needing a path."""
    return [cell for cell in paintbrush_live(maze=maze, start=start, end=end)
            if cell is not None]


@register_live_solver('paintbrush')
def paintbrush_live(*, maze, start, end):
    """Discard branches using temporary edge blocking and flood-fill tests.

    Adapted from section 4.1 of Maze Solving Algorithms by Chand, Goel and
    Rathore: https://sce.carleton.ca/faculty/wainer/papers/Maze.pdf
    Previous path cells are excluded to prevent loops. This finds a route,
    not necessarily the shortest one in a maze containing cycles. Repeated
    flood fills can require quadratic time in the number of passage cells.
    """
    blocked_edges = set()
    previous = set()

    def edge(a, b):
        return frozenset((a, b))

    def neighbors(point):
        x, y = point
        for candidate in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)):
            nx, ny = candidate
            if (0 <= nx < maze.width and 0 <= ny < maze.height
                    and maze.cells[ny][nx] == 0 and candidate not in previous
                    and edge(point, candidate) not in blocked_edges):
                yield candidate

    def can_reach_goal(origin):
        pending = [origin]
        painted = {origin}
        while pending:
            current = pending.pop()
            yield None  # Let the app render between flood-fill expansions.
            if current == end:
                return True
            for neighbor in neighbors(current):
                if neighbor not in painted:
                    painted.add(neighbor)
                    pending.append(neighbor)
        return False

    if not (yield from can_reach_goal(start)):
        return

    current = start
    yield current
    while current != end:
        choices = list(neighbors(current))
        # Keep pruning optional openings until only a necessary one remains.
        for candidate in choices[:-1]:
            opening = edge(current, candidate)
            blocked_edges.add(opening)
            if (yield from can_reach_goal(current)):
                continue
            blocked_edges.remove(opening)
            next_cell = candidate
            break
        else:
            next_cell = choices[-1]

        previous.add(current)
        current = next_cell
        yield current
