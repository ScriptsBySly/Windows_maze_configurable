from ursina import *

###
# Global variables
###

#configuration parameters
config_texture_scale = (8,2)
config_roof_height = 4
config_maze_size = 64
config_movement_speed = 2
config_camera_frontal_collider = 2


#flags
flag_rotating = False

#trackable variables
rotation_remaining = 0

###
# INITIALIZE
###

# create a window
app = Ursina()

# create the ground of the maze
ground  = Entity(model='plane', collider='box', scale=config_maze_size, texture='grass', texture_scale=config_texture_scale)
ceiling = Entity(model='plane', collider='box', scale=config_maze_size, texture='brick', texture_scale=config_texture_scale, y=config_roof_height, rotation_x=180)

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
half = config_maze_size / 16
height = config_roof_height
thickness = 1

wall_settings = dict(
    model='cube',
    collider='box',
    texture='brick',
    texture_scale=config_texture_scale,
    color=color.white,
)

walls = [
    # Left and right
    Entity(position=(-half, height/2, 0),
           scale=(thickness, height, config_maze_size),
           **wall_settings),
    Entity(position=(half, height/2, 0),
           scale=(thickness, height, config_maze_size),
           **wall_settings),

    # Front and back
    Entity(position=(0, height/2, half),
           scale=(config_maze_size, height, thickness),
           **wall_settings),
    Entity(position=(0, height/2, -half),
           scale=(config_maze_size, height, thickness),
           **wall_settings),
]



def move_camera():
    global flag_rotating, rotation_remaining

    if not flag_rotating:
        camera.position += camera.forward *config_movement_speed * time.dt
        #If a collision is detected, set the flag to rotate camera
        if camera.intersects(ignore=[ground, ceiling]).hit:
            flag_rotating = True
            rotation_remaining = 90
    else:
        camera.rotation_y -= 90 * time.dt  
        rotation_remaining -= 90 * time.dt
        if rotation_remaining <= 0:
            flag_rotating = False
            camera.rotation_y = round(camera.rotation_y / 90) * 90  # Snap to nearest 90 degrees



def update():
    move_camera()


# start running the game
app.run()


