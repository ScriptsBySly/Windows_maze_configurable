"""Run solver checks with python -m unittest test_maze_solving."""

from collections import deque
import inspect
import random
import unittest

from maze_generator import Maze, generate_maze
from maze_solving import available_solvers, register_solver, solve_maze, solve_maze_live


def reachable(maze, start, end):
    pending = deque([start])
    visited = {start}
    while pending:
        x, y = pending.popleft()
        if (x, y) == end:
            return True
        for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
            if (0 <= nx < maze.width and 0 <= ny < maze.height
                    and maze.cells[ny][nx] == 0 and (nx, ny) not in visited):
                visited.add((nx, ny))
                pending.append((nx, ny))
    return False


class PaintbrushTests(unittest.TestCase):
    def check_route(self, maze, start, end):
        original = maze.cells
        path = solve_maze('PAINTBRUSH', maze, start=start, end=end)
        self.assertEqual(bool(path), reachable(maze, start, end))
        self.assertEqual(maze.cells, original)
        if path:
            self.assertEqual((path[0], path[-1]), (start, end))
            self.assertEqual(len(set(path)), len(path))
            self.assertTrue(all(maze.cells[y][x] == 0 for x, y in path))
            self.assertTrue(all(abs(a[0]-b[0]) + abs(a[1]-b[1]) == 1
                                for a, b in zip(path, path[1:])))
        return path

    def test_generated_mazes(self):
        for size in (3, 16, 31):
            for seed in range(5):
                maze = generate_maze('DFS', width=size, height=size, seed=seed)
                passages = [(x, y) for y, row in enumerate(maze.cells)
                            for x, cell in enumerate(row) if cell == 0]
                self.check_route(maze, passages[0], passages[-1])

    def test_random_grids_with_loops_and_disconnections(self):
        rng = random.Random(42)
        for _ in range(100):
            cells = [[int(rng.random() < .3) for _ in range(8)] for _ in range(8)]
            cells[0][0] = cells[7][7] = 0
            self.check_route(Maze(cells), (0, 0), (7, 7))

    def test_single_cell_and_unreachable(self):
        self.assertEqual(self.check_route(Maze(((0,),)), (0, 0), (0, 0)), [(0, 0)])
        self.assertEqual(self.check_route(Maze(((0, 1, 0),)), (0, 0), (2, 0)), [])

    def test_invalid_inputs(self):
        maze = Maze(((0, 1), (0, 0)))
        for point in ((1, 0), (-1, 0), (2, 0), (0.5, 0), (True, 0), (0,)):
            with self.subTest(point=point):
                with self.assertRaises(ValueError):
                    solve_maze('paintbrush', maze, start=point, end=(1, 1))
                with self.assertRaises(ValueError):
                    solve_maze('paintbrush', maze, start=(0, 0), end=point)
        with self.assertRaises(ValueError):
            solve_maze('unknown', maze, start=(0, 0), end=(1, 1))
        with self.assertRaises(TypeError):
            solve_maze('paintbrush', [[0]], start=(0, 0), end=(0, 0))

    def test_registry(self):
        self.assertIn('paintbrush', available_solvers())
        with self.assertRaises(ValueError):
            register_solver('PAINTBRUSH')(lambda **kwargs: [])
        # Verify new solvers can be selected, without altering built-in entries.
        from maze_solving import _solvers
        try:
            @register_solver('test fixture')
            def fixture(*, maze, start, end):
                return [start]
            self.assertEqual(solve_maze('TEST-FIXTURE', Maze(((0,),)),
                                       start=(0, 0), end=(0, 0)), [(0, 0)])
        finally:
            _solvers.pop('test_fixture', None)

    def test_live_solver_is_lazy_and_matches_batch(self):
        maze = generate_maze('DFS', width=16, height=16, seed=42)
        live = solve_maze_live('paintbrush', maze, start=(1, 1), end=(13, 13))
        self.assertEqual(inspect.getgeneratorstate(live), 'GEN_CREATED')
        self.assertIsNone(next(live))  # Search work yields before any movement.
        decisions = [cell for cell in live if cell is not None]
        self.assertEqual(decisions, solve_maze('paintbrush', maze,
                                             start=(1, 1), end=(13, 13)))

    def test_live_unreachable_and_invalid_inputs(self):
        events = list(solve_maze_live('paintbrush', Maze(((0, 1, 0),)),
                                      start=(0, 0), end=(2, 0)))
        self.assertTrue(events)
        self.assertTrue(all(event is None for event in events))
        with self.assertRaises(ValueError):
            solve_maze_live('unknown', Maze(((0,),)), start=(0, 0), end=(0, 0))
        with self.assertRaises(ValueError):
            solve_maze_live('paintbrush', Maze(((0, 1),)), start=(0, 0), end=(1, 0))


if __name__ == '__main__':
    unittest.main()
