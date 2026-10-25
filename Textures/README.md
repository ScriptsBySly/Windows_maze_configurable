# Custom textures

Place seamless JPG images in this folder using these exact filenames:

| Filename | Surface | Built-in fallback when absent |
| --- | --- | --- |
| `wall.jpg` | Maze walls | `brick` |
| `ground.jpg` | Ground | `grass` |
| `ceiling.jpg` | Ceiling | `brick` |
| `door.jpg` | Exit door | `brick` |

Each texture is optional. Missing files use their built-in fallback independently.
Restart `main.py` after adding or replacing images. Remove a file to restore its
fallback. Paths resolve relative to `main.py`, regardless of your working folder.

Textures default to one full image per cell: wall images span the full wall
height and width of each cell face, while ground and ceiling images repeat
once per grid cell (16 x 16 repeats for a 16 x 16 maze).

Adjust `config_texture_scale` in `main.py` to change repeats per cell. The default
`(1, 1)` fits one image; `(2, 2)` repeats it twice in each direction within a cell.
Seamless images tile without visible edges. Each image is stretched to fit the
cell face, so rectangular faces may stretch square images.

The exit door displays its image once, preserving the image's aspect ratio.
It stands at the center of the goal cell, from the floor to two thirds of the
wall height, and rotates horizontally to face the player. It has no collider.

Custom images and subfolders are ignored by Git. Only this README is included
in version control; provide your own images after cloning the project.
