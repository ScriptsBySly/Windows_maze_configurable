from matplotlib.pylab import rand
from math import atan2, degrees
from ursina import *
from pathlib import Path
from maze_generator import generate_maze
from maze_solving import solve_maze_live

###
# Global variables
###

#configuration parameters
config_window_width = 1080
config_window_height = 1920
config_texture_scale = (1,1)  # Texture repeats per cell (horizontal, vertical).
config_roof_height = 4
config_movement_speed = 6
config_maze_algorithm = 'DFS'
config_maze_columns = 16
config_maze_rows = 16
config_cell_size = 8 * (2 / 3)  # Horizontal cell size, reduced by one third.
config_maze_size = config_maze_columns * config_cell_size
config_camera_frontal_collider = config_cell_size / 2
config_maze_seed = rand()
config_maze_solver = 'paintbrush'
config_solver_expansions_per_frame = 16
config_turn_speed = 180  # Degrees per second.


# Live solver state; no complete solution path is stored.
solver = None
camera_target = None
goal_cell = None
solver_finished = False
steps_taken = 0
exit_door = None

###
# INITIALIZE
###

# create a window
app = Ursina(
    size=(config_window_width, config_window_height),
    fullscreen=False,
    borderless=False,
)


def project_texture(filename, fallback):
    """Load an optional custom texture relative to this script."""
    folder = Path(__file__).resolve().parent / 'Textures'
    if not (folder / filename).is_file():
        return fallback
    return load_texture(filename, path=folder) or fallback


ground_texture = project_texture('ground.jpg', 'grass')
ceiling_texture = project_texture('ceiling.jpg', 'brick')
wall_texture = project_texture('wall.jpg', 'brick')
door_texture = project_texture('door.jpg', 'brick')

# create the ground of the maze
surface_texture_scale = (
    config_maze_columns * config_texture_scale[0],
    config_maze_rows * config_texture_scale[1],
)
ground  = Entity(model='plane', collider='box', scale=config_maze_size, texture=ground_texture, texture_scale=surface_texture_scale)
ceiling = Entity(model='plane', collider='box', scale=config_maze_size, texture=ceiling_texture, texture_scale=surface_texture_scale, y=config_roof_height, rotation_x=180)

# setup the camera
camera.position = (0, config_roof_height/2, 0)
camera.rotation = (0, 0, 0)
camera.collider = BoxCollider(camera, Vec3(0,0,config_camera_frontal_collider/2), Vec3(1,1,config_camera_frontal_collider))
camera.collision = True
camera.collider.visible = False

# setup lighting

# sun = DirectionalLight()
# sun.look_at(Vec3(1,-1,-1))
# Sky()

#AmbientLight(color=color.rgba(120, 120, 120, 255))



###
# Generate maze walls
###
try:
    maze = generate_maze(
        config_maze_algorithm,
        width=config_maze_columns,
        height=config_maze_rows,
        seed=config_maze_seed,
    )
except NotImplementedError as error:
    # Keep the scene usable while the algorithm implementations are unfinished.
    print(f'Maze generation: {error}')
    maze = None

walls = []
passages = []
if maze is not None:
    cell_width = config_maze_size / maze.width
    cell_depth = config_maze_size / maze.height
    start_position = None

    for row, cells in enumerate(maze.cells):
        for column, cell in enumerate(cells):
            x = (column + .5) * cell_width - config_maze_size / 2
            z = (row + .5) * cell_depth - config_maze_size / 2

            if cell == 1:
                walls.append(Entity(
                    model='cube',
                    collider='box',
                    position=(x, config_roof_height / 2, z),
                    scale=(cell_width, config_roof_height, cell_depth),
                    texture=wall_texture,
                    texture_scale=(2, 2),
                    color=color.white,
                ))
            else:
                passages.append((column, row))
                if start_position is None:
                    start_position = Vec3(x, config_roof_height / 2, z)

    # Spawn inside the first passage rather than potentially inside a wall.
    if start_position is not None:
        camera.position = start_position


solver_status = Text(text='No maze passages available', position=(-.85, .46), scale=1)


def cell_to_world(cell):
    column, row = cell
    return Vec3(
        (column + .5) * cell_width - config_maze_size / 2,
        config_roof_height / 2,
        (row + .5) * cell_depth - config_maze_size / 2,
    )


if passages:
    start_cell, goal_cell = passages[0], passages[-1]
    # Creating the iterator performs no search. update() advances it live.
    solver = solve_maze_live(config_maze_solver, maze, start=start_cell, end=goal_cell)
    solver_status.text = f'{config_maze_solver}: searching'
    point = cell_to_world(start_cell)
    Entity(model='cube', position=(point.x, .03, point.z),
           scale=(cell_width * .4, .05, cell_depth * .4), color=color.green)

    goal_position = cell_to_world(goal_cell)
    door_height = config_roof_height * (2 / 3)
    door_aspect = getattr(door_texture, 'width', 1) / getattr(door_texture, 'height', 2)
    exit_door = Entity(
        model='quad',
        texture=door_texture,
        texture_scale=(1, 1),
        position=(goal_position.x, 0, goal_position.z),
        origin_y=-.5,  # Anchor the bottom edge to the ground.
        scale=(door_height * door_aspect, door_height, 1),
        double_sided=True,
        color=color.white,
    )


def face_exit_door_to_player():
    if exit_door is None:
        return
    dx = camera.x - exit_door.x
    dz = camera.z - exit_door.z
    if dx * dx + dz * dz > .000001:
        # Quad's front points along local -Z; rotate only around vertical Y.
        exit_door.rotation_y = degrees(atan2(dx, dz)) + 180


face_exit_door_to_player()


def move_camera():
    global camera_target, solver_finished, steps_taken

    if solver is None or solver_finished:
        return

    if camera_target is None:
        # Bound search work so a flood-fill cannot block the rendering loop.
        for _ in range(config_solver_expansions_per_frame):
            try:
                decision = next(solver)
            except StopIteration:
                solver_finished = True
                solver_status.text = 'No route to goal'
                return
            if decision is not None:
                camera_target = decision
                break
        if camera_target is None:
            solver_status.text = f'{config_maze_solver}: searching'
            return

    target = cell_to_world(camera_target)
    delta = target - camera.position
    remaining = delta.length()
    if remaining > .0001:
        # Turn in place, then travel between adjacent passage centers.
        desired_yaw = degrees(atan2(delta.x, delta.z))
        turn = (desired_yaw - camera.rotation_y + 180) % 360 - 180
        turn_step = config_turn_speed * time.dt
        if abs(turn) > .01:
            camera.rotation_y += max(-turn_step, min(turn_step, turn))
            solver_status.text = f'{config_maze_solver}: turning'
            return
        camera.rotation_y = desired_yaw
        camera.position += delta.normalized() * min(config_movement_speed * time.dt, remaining)
        solver_status.text = f'{config_maze_solver}: moving ({steps_taken} steps)'
        if (target - camera.position).length() > .0001:
            return

    camera.position = target
    if camera_target != start_cell:
        steps_taken += 1
    if camera_target == goal_cell:
        solver_finished = True
        solver_status.text = f'Solved! {steps_taken} steps'
    camera_target = None



def update():
    move_camera()
    face_exit_door_to_player()


# start running the game
app.run()


