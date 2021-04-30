import os
os.environ['SDL_VIDEO_WINDOW_POS'] = '400,200'

import pygame
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
from OpenGL.GLU import *
import pyrr
from TextureLoader import load_texture_pygame
from ObjLoader import ObjLoader
import numpy as np

from camera import Camera

# CAMERA settings
cam = Camera()
WIDTH, HEIGHT = 1280, 720
lastX, lastY = WIDTH / 2, HEIGHT / 2
first_mouse = True

vertex_shader_geometry = """
#version 330 core

layout(location = 0) in vec3 position;
layout(location = 1) in vec4 color;

uniform mat4 model;
uniform mat4 projection;
uniform mat4 view;

out vec4 vColor;

void main() {
  gl_Position = vec4(position, 1.0);
  vColor = color;
}
"""

fragment_shader_geometry = """
#version 330 core
in vec4 vColor;
out vec4 fColor;

void main(void) {
  fColor = vColor;
}
"""

vertex_shader_obj = """
# version 330

layout(location = 0) in vec3 a_position;
layout(location = 1) in vec2 a_texture;
layout(location = 2) in vec3 a_normal;

uniform mat4 model;
uniform mat4 projection;
uniform mat4 view;

out vec2 v_texture;

void main() {
    gl_Position = projection * view * model * vec4(a_position, 1.0);
    v_texture = a_texture;
}
"""

fragment_shader_obj = """
# version 330

in vec2 v_texture;

out vec4 out_color;

uniform sampler2D s_texture;

void main() {
    out_color = texture(s_texture, v_texture);
}
"""


def mouse_look(xpos, ypos):
    global first_mouse, lastX, lastY

    if first_mouse:
        lastX = xpos
        lastY = ypos
        first_mouse = False

    xoffset = xpos - lastX
    yoffset = lastY - ypos

    lastX = xpos
    lastY = ypos

    cam.process_mouse_movement(xoffset, yoffset)

shaders = {}    # Holds {'shader_name': {'shader_program': ..., 'model_loc': ..., 'proj_loc': ..., 'view_loc': ...}}
all_objs = {}   # Holds {'obj_name': {'VAO': ..., 'VBO_pos': ..., 'VBO_color': ..., 'textures': ..., '': ..., 'num_faces': ...}}
lines = []      # Holds line names which are keys for the all_objs dict
objs = []       # Holds names of objs read in from .obj models

# Returns the object index
def load_obj(obj_filepath, texture_filepath):
    obj_name = 'obj'+str(len(objs)).zfill(5)
    objs.append(obj_name)
    all_objs[obj_name] = {'VAO': glGenVertexArrays(1), 'VBO_pos': glGenBuffers(1), 'textures': glGenTextures(1)}

    obj_faces, obj_buffer = ObjLoader.load_model(obj_filepath, scale=0.3)

    all_objs[obj_name]['num_faces'] = len(obj_faces)

    # Vertex Array Object
    glBindVertexArray(all_objs[obj_name]['VAO'])

    # Vertex Buffer Object
    glBindBuffer(GL_ARRAY_BUFFER, all_objs[obj_name]['VBO_pos'])
    glBufferData(GL_ARRAY_BUFFER, obj_buffer.nbytes, obj_buffer, GL_STATIC_DRAW)

    # vertices
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, obj_buffer.itemsize * 8, ctypes.c_void_p(0))
    
    # textures
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, obj_buffer.itemsize * 8, ctypes.c_void_p(12))
    load_texture_pygame(texture_filepath, all_objs[obj_name]['textures'])

    # normals
    glEnableVertexAttribArray(2)
    glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, obj_buffer.itemsize * 8, ctypes.c_void_p(20))

    return obj_name

def rot_matrix_x_44(degrees):
    c, s = np.cos(np.deg2rad(degrees)), np.sin(np.deg2rad(degrees))
    return np.array(((1, 0, 0, 0), (0, c, s, 0), (0, -s, c, 0), (0, 0, 0, 1)))

def rot_matrix_y_44(degrees):
    c, s = np.cos(np.deg2rad(degrees)), np.sin(np.deg2rad(degrees))
    return np.array(((c, 0, -s, 0), (0, 1, 0, 0), (s, 0, c, 0), (0, 0, 0, 1)))

def rot_matrix_z_44(degrees):
    c, s = np.cos(np.deg2rad(degrees)), np.sin(np.deg2rad(degrees))
    return np.array(((c, -s, 0, 0), (s, c, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))

def draw_obj(obj_name, xpos, ypos, zpos, roll, pitch, yaw):
    #TODO We really should only change obj_pos upon updated pos or rotation
    translation_matrix = pyrr.matrix44.create_from_translation(pyrr.Vector3([xpos, ypos, zpos]))
    rot_x = rot_matrix_x_44(roll)
    rot_y = rot_matrix_y_44(pitch)
    rot_z = rot_matrix_z_44(yaw)
    pos_matrix = pyrr.matrix44.multiply(pyrr.matrix44.multiply(pyrr.matrix44.multiply(rot_x, rot_y), rot_z), translation_matrix)

    # draw the obj
    glBindVertexArray(all_objs[obj_name]['VAO'])
    glBindTexture(GL_TEXTURE_2D, all_objs[obj_name]['textures'])
    glUniformMatrix4fv(shaders['shader_obj']['model_loc'], 1, GL_FALSE, pos_matrix)
    glDrawArrays(GL_TRIANGLES, 0, all_objs[obj_name]['num_faces'])

def rotate_obj(obj_index, pitch, roll, yaw):
    # Create rotation matrices from the euler angles
    pass

# Returns the index of the object in VAOs, buf_lens, 
def load_line(x1, y1, z1, x2, y2, z2, red, green, blue, alpha):
    line_name = 'line'+str(len(lines)).zfill(5)
    lines.append(line_name)
    all_objs[line_name] = {'VAO': glGenVertexArrays(1), 'VBO_pos': glGenBuffers(1), 'VBO_color': glGenBuffers(1)}
    pos_buf = np.array([x1, y1, z1, x2, y2, z2], dtype='float32')
    col_buf = np.array([red, green, blue, alpha, red, green, blue, alpha], dtype='float32')

    # Vertex Array Object
    glBindVertexArray(all_objs[line_name]['VAO'])

    # Vertex Buffer Objects
    glBindBuffer(GL_ARRAY_BUFFER, all_objs[line_name]['VBO_pos'])
    glBufferData(GL_ARRAY_BUFFER, pos_buf.nbytes, pos_buf, GL_STATIC_DRAW)
    glBindBuffer(GL_ARRAY_BUFFER, all_objs[line_name]['VBO_color'])
    glBufferData(GL_ARRAY_BUFFER, col_buf.nbytes, col_buf, GL_STATIC_DRAW)

    # Vertices
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)

    # Colors
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, 0, None)
    
    return line_name


def draw_line(line_name):
    translation_matrix = pyrr.matrix44.create_from_translation(pyrr.Vector3([0, 0, 0]))
    glBindVertexArray(all_objs[line_name]['VAO'])
    glUniformMatrix4fv(shaders['shader_geom']['model_loc'], 1, GL_FALSE, translation_matrix)
    glDrawArrays(GL_LINES, 0, 2)
    #glBindBuffer(GL_ARRAY_BUFFER, 0); //Unbind

def setup_program_obj(program):
    pass

def setup_program_geometry(program):
    pass

def main():
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE) # |pygame.FULLSCREEN
    pygame.mouse.set_visible(True)
    pygame.event.set_grab(True)

    shaders['shader_obj'] = {}
    shaders['shader_obj']['shader_program'] = compileProgram(compileShader(vertex_shader_obj, GL_VERTEX_SHADER), compileShader(fragment_shader_obj, GL_FRAGMENT_SHADER))
    shaders['shader_obj']['model_loc'] = glGetUniformLocation(shaders['shader_obj']['shader_program'], "model")
    shaders['shader_obj']['proj_loc'] = glGetUniformLocation(shaders['shader_obj']['shader_program'], "projection")
    shaders['shader_obj']['view_loc'] = glGetUniformLocation(shaders['shader_obj']['shader_program'], "view")
    
    shaders['shader_geom'] = {}
    shaders['shader_geom']['shader_program'] = compileProgram(compileShader(vertex_shader_geometry, GL_VERTEX_SHADER), compileShader(fragment_shader_geometry, GL_FRAGMENT_SHADER))
    shaders['shader_geom']['model_loc'] = glGetUniformLocation(shaders['shader_geom']['shader_program'], "model")
    shaders['shader_geom']['proj_loc'] = glGetUniformLocation(shaders['shader_geom']['shader_program'], "projection")
    shaders['shader_geom']['view_loc'] = glGetUniformLocation(shaders['shader_geom']['shader_program'], "view")

    projection = pyrr.matrix44.create_perspective_projection_matrix(45, WIDTH / HEIGHT, 0.1, 100)

    glUseProgram(shaders['shader_obj']['shader_program'])
    glClearColor(0, 0.1, 0.1, 1)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glUniformMatrix4fv(shaders['shader_obj']['proj_loc'], 1, GL_FALSE, projection)

    glUseProgram(shaders['shader_geom']['shader_program'])
    glUniformMatrix4fv(shaders['shader_geom']['proj_loc'], 1, GL_FALSE, projection)

    running = True

    earth_name = load_obj("meshes/earth.obj", "meshes/earth.png")
    line1_name = load_line(0, 0, 0, 50, 0, 0, 0, 1, 0, 1)
    #glTranslatef(0.0, 0.0, -5.0)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif  event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

            if event.type == pygame.VIDEORESIZE:
                glViewport(0, 0, event.w, event.h)
                projection = pyrr.matrix44.create_perspective_projection_matrix(45, event.w / event.h, 0.1, 100)
                glUniformMatrix4fv(proj_loc, 1, GL_FALSE, projection)

        keys_pressed = pygame.key.get_pressed()
        if keys_pressed[pygame.K_a]:
            cam.process_keyboard("LEFT", 0.03)
        if keys_pressed[pygame.K_d]:
            cam.process_keyboard("RIGHT", 0.03)
        if keys_pressed[pygame.K_w]:
            cam.process_keyboard("FORWARD", 0.03)
        if keys_pressed[pygame.K_s]:
            cam.process_keyboard("BACKWARD", 0.03)
        if keys_pressed[pygame.K_c]:
            global lastX, lastY
            lastX, lastY = WIDTH / 2, HEIGHT / 2
            pygame.mouse.set_pos(WIDTH / 2, HEIGHT / 2)


        mouse_pos = pygame.mouse.get_pos()
        mouse_look(mouse_pos[0], mouse_pos[1])

        # to been able to look around 360 degrees, still not perfect
        #print(mouse_pos)
        if mouse_pos[0] <= 0:
            pygame.mouse.set_pos((1277, mouse_pos[1]))  # Requires mouse to be visible... TODO
        elif mouse_pos[0] >= 1279:
            pygame.mouse.set_pos((2, mouse_pos[1]))


        ct = pygame.time.get_ticks() / 1000

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        view = cam.get_view_matrix()

        # Draw .obj objects
        glUseProgram(shaders['shader_obj']['shader_program'])
        glUniformMatrix4fv(shaders['shader_obj']['view_loc'], 1, GL_FALSE, view)
        rot_y = 0.02 * pygame.time.get_ticks()
        draw_obj(earth_name, 0, 0, 0, 0, rot_y, 22.5)
        pygame.time.wait(10)

        # Draw geometric objects
        glUseProgram(shaders['shader_geom']['shader_program'])
        glUniformMatrix4fv(shaders['shader_geom']['view_loc'], 1, GL_FALSE, view)
        draw_line(line1_name)
        
        pygame.display.flip()
        pygame.time.wait(1)

    pygame.quit()

main()