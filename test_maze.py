"""Preview a DFS maze: python test_maze.py

Save a plot instead: python test_maze.py --output maze.png
Black cells are walls; white cells are passages.
"""

import argparse
from collections import deque

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from maze_generator import Maze, generate_maze


def find_endpoints(maze: Maze):
    """Use the first passage as start and a farthest reachable passage as end.

    The generator supplies no endpoint metadata. These are preview endpoints,
    not openings carved into the maze's outer walls.
    """
    start = next(
        ((column, row) for row, cells in enumerate(maze.cells)
         for column, cell in enumerate(cells) if cell == 0),
        None,
    )
    if start is None:
        raise ValueError('Cannot mark endpoints: the maze has no passages.')

    pending = deque([start])
    visited = {start}
    end = start
    while pending:
        end = pending.popleft()
        x, y = end
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (0 <= nx < maze.width and 0 <= ny < maze.height
                    and maze.cells[ny][nx] == 0 and (nx, ny) not in visited):
                visited.add((nx, ny))
                pending.append((nx, ny))
    return start, end


def plot_maze(maze: Maze):
    """Return a 2D figure with the same row/column orientation as the grid."""
    start, end = find_endpoints(maze)
    figure, axes = plt.subplots(figsize=(8, 8))
    axes.imshow(
        maze.cells,
        cmap=ListedColormap(['white', 'black']),
        vmin=0,
        vmax=1,
        interpolation='nearest',
        origin='upper',
        aspect='equal',
    )
    markers = []
    endpoints = [(start, 'green', 'Start', 'S'), (end, 'red', 'End', 'E')]
    if start == end:
        endpoints = [(start, 'purple', 'Start / End', 'S/E')]
    for (x, y), marker_color, label, text in endpoints:
        markers.append(axes.scatter(
            x, y, c=marker_color, s=100, edgecolors='white', label=label,
            zorder=3,
        ))
        axes.annotate(
            text, (x, y), xytext=(7, 7), textcoords='offset points',
            color=marker_color, weight='bold', annotation_clip=False,
            bbox=dict(facecolor='white', alpha=.85, edgecolor='none', pad=1),
            zorder=4,
        )
    axes.set_title(f'DFS maze — {maze.width} columns × {maze.height} rows')
    axes.set_xlabel('Column')
    axes.set_ylabel('Row')
    axes.legend(
        handles=[
            Patch(facecolor='black', label='Wall'),
            Patch(facecolor='white', edgecolor='black', label='Passage'),
        ] + markers,
        loc='upper center',
        bbox_to_anchor=(0.5, -0.09),
        ncol=4,
    )
    figure.tight_layout()
    return figure, axes


def main():
    parser = argparse.ArgumentParser(description='Generate and plot a DFS maze.')
    parser.add_argument('--width', type=int, default=31, help='Grid columns (default: 31)')
    parser.add_argument('--height', type=int, default=31, help='Grid rows (default: 31)')
    parser.add_argument('--seed', type=int, default=0, help='Random seed (default: 0)')
    parser.add_argument('--output', help='Save to an image file instead of opening a window')
    args = parser.parse_args()

    try:
        maze = generate_maze('DFS', width=args.width, height=args.height, seed=args.seed)
    except (NotImplementedError, ValueError) as error:
        parser.exit(1, f'Maze generation failed: {error}\n')

    figure, _ = plot_maze(maze)
    if args.output:
        figure.savefig(args.output, dpi=150, bbox_inches='tight')
        plt.close(figure)
        print(f'Saved maze plot to {args.output}')
    else:
        plt.show()


if __name__ == '__main__':
    main()
