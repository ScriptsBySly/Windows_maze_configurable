from ursina import *

###
# Global variables
###

config_texture_scale = (16,16)
config_roof_height = 4
config_maze_size = 64

###
# INITIALIZE
###

# create a window
app = Ursina()

# create the ground of the maze
ground  = Entity(model='plane', collider='box', scale=config_maze_size, texture='grass', texture_scale=config_texture_scale)
ceiling = Entity(model='plane', collider='box', scale=config_maze_size, texture='brick', texture_scale=config_texture_scale, y=config_roof_height, rotation_x=180)

# setup the camer
camera.position = (0, config_roof_height/2, 0)
camera.rotation = (0, 0, 0)

# setup lighting

# sun = DirectionalLight()
# sun.look_at(Vec3(1,-1,-1))
# Sky()


#AmbientLight(color=color.rgba(120, 120, 120, 255))



# start running the game
app.run()


