from matplotlib.pylab import rand
from math import atan2, degrees
from ursina import *
from pathlib import Path
import ctypes
import os
from panda3d.core import Filename
from maze_generator import generate_maze
from maze_solving import solve_maze_live
from text_gradient import vaporwave_text_shader

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
config_wall_growth_duration = 1.5  # Seconds; set to 0 for instant walls.
config_wall_growth_delay = 1.0  # Seconds before the walls begin rising.
config_brb_scale = 2
config_brb_font = 'tahomabd.ttf'  # Tahoma Bold, from the Windows Fonts folder.
config_brb_speed = (.12, .09)  # Horizontal and vertical UI units per second.
config_brb_gradient_speed = .2  # Upward gradient cycles per second.
config_brb_outline_width = 4.0  # Black outline thickness in screen pixels.


# Live solver state; no complete solution path is stored.
solver = None
camera_target = None
goal_cell = None
solver_finished = False
steps_taken = 0
exit_door = None
wall_growth_elapsed = 0
walls_raised = False

###
# INITIALIZE
###

# create a window
app = Ursina(
    size=(config_window_width, config_window_height),
    fullscreen=False,
    borderless=True,
    editor_ui_enabled=False,
)
window.editor_ui.enabled = False
window.exit_button.enabled = False
window.fps_counter.enabled = False
mouse.visible = False

# Poll Windows directly, independently of focused-window input and maze updates.
get_async_key_state = ctypes.WinDLL('user32', use_last_error=True).GetAsyncKeyState
get_async_key_state.argtypes = [ctypes.c_int]
get_async_key_state.restype = ctypes.c_short


def check_global_escape(task):
    if get_async_key_state(0x1B) & 0x8000:  # VK_ESCAPE, currently held down.
        application.quit()
        return task.done
    return task.cont


app.taskMgr.add(check_global_escape, 'global_escape', sort=-100)


windows_font_folder = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
brb_font_path = next(
    (windows_font_folder / name
     for name in (config_brb_font, 'segoeuib.ttf', 'arialbd.ttf')
     if (windows_font_folder / name).is_file()),
    None,
)
brb_font = (Filename.from_os_specific(str(brb_font_path.resolve())).get_fullpath()
            if brb_font_path else Text.default_font)

brb_text = Text(
    text='Be\nRight\nBack', parent=camera.ui, origin=(-.5, 0),
    font=brb_font, scale=config_brb_scale, color=color.white, z=-1,
)
brb_velocity = Vec2(*config_brb_speed)
brb_text.shader = vaporwave_text_shader
brb_text.set_shader_input('outline_width', config_brb_outline_width)
brb_gradient_phase = 0.0
brb_text_width, brb_text_height = brb_text.width, brb_text.height


def move_brb_text():
    """Bounce the entire label inside the current window, including on resize."""
    global brb_gradient_phase
    padding = .02
    fitted_scale = max(.01, min(
        config_brb_scale,
        (window.aspect_ratio - 2 * padding) / brb_text_width,
        (1 - 2 * padding) / brb_text_height,
    ))
    brb_text.scale = fitted_scale
    x_min = -window.aspect_ratio / 2 + padding
    x_max = max(x_min, window.aspect_ratio / 2 - brb_text_width * fitted_scale - padding)
    y_limit = max(0, .5 - brb_text_height * fitted_scale / 2 - padding)
    brb_text.x += brb_velocity.x * time.dt
    brb_text.y += brb_velocity.y * time.dt
    for axis, lower, upper in (('x', x_min, x_max), ('y', -y_limit, y_limit)):
        position = getattr(brb_text, axis)
        if position <= lower or position >= upper:
            setattr(brb_text, axis, max(lower, min(upper, position)))
            speed = abs(getattr(brb_velocity, axis))
            setattr(brb_velocity, axis, -speed if position >= upper else speed)

    brb_gradient_phase = (brb_gradient_phase + time.dt * config_brb_gradient_speed) % 1
    brb_text.set_shader_input('gradient_phase', brb_gradient_phase)
    brb_text.set_shader_input('viewport_height', float(app.win.get_y_size()))
    brb_text.set_shader_input('label_center_y', float(brb_text.y))
    brb_text.set_shader_input('label_height', brb_text_height * fitted_scale)


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
                    position=(x, 0, z),
                    origin_y=-.5,
                    scale=(cell_width, .001, cell_depth),
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


def raise_walls():
    """Keep wall bottoms on the floor while stretching their tops upward."""
    global wall_growth_elapsed, walls_raised
    if walls_raised or not walls:
        return False

    wall_growth_elapsed += time.dt
    growth_time = wall_growth_elapsed - config_wall_growth_delay
    if growth_time < 0:
        return True
    progress = (1 if config_wall_growth_duration <= 0 else
                min(growth_time / config_wall_growth_duration, 1))
    eased = progress * progress * (3 - 2 * progress)
    for wall in walls:
        wall.scale_y = max(.001, config_roof_height * eased)

    walls_raised = progress >= 1
    return not walls_raised


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
                return
            if decision is not None:
                camera_target = decision
                break
        if camera_target is None:
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
            return
        camera.rotation_y = desired_yaw
        camera.position += delta.normalized() * min(config_movement_speed * time.dt, remaining)
        if (target - camera.position).length() > .0001:
            return

    camera.position = target
    if camera_target != start_cell:
        steps_taken += 1
    if camera_target == goal_cell:
        solver_finished = True
    camera_target = None



def update():
    move_brb_text()
    if raise_walls():
        face_exit_door_to_player()
        return
    move_camera()
    face_exit_door_to_player()


# start running the game
app.run()


