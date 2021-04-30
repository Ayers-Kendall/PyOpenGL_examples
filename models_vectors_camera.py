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


vertex_src = """
# version 330

layout(location = 0) in vec3 a_position;
layout(location = 1) in vec2 a_texture;
layout(location = 2) in vec3 a_normal;

uniform mat4 model;
uniform mat4 projection;
uniform mat4 view;

out vec2 v_texture;

void main()
{
    gl_Position = projection * view * model * vec4(a_position, 1.0);
    v_texture = a_texture;
}
"""

fragment_src = """
# version 330

in vec2 v_texture;

out vec4 out_color;

uniform sampler2D s_texture;

void main()
{
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

VAOs = []
VBOs = []
textures = []
buf_lens = []
obj_locs = []   # This location includes the applied rotation info obtained from glUniformMatrix4fv
disp_list_indices = []

# Returns the object index
def load_obj(obj_filepath, texture_filepath):
    VAOs.append(glGenVertexArrays(1))
    VBOs.append(glGenBuffers(1))
    textures.append(glGenTextures(1))

    obj_indices, obj_buffer = ObjLoader.load_model(obj_filepath, scale=0.3)

    buf_lens.append(len(obj_indices))

    # Vertex Array Object
    glBindVertexArray(VAOs[-1])

    # Vertex Buffer Object
    glBindBuffer(GL_ARRAY_BUFFER, VBOs[-1])
    glBufferData(GL_ARRAY_BUFFER, obj_buffer.nbytes, obj_buffer, GL_STATIC_DRAW)

    # vertices
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, obj_buffer.itemsize * 8, ctypes.c_void_p(0))
    
    # textures
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, obj_buffer.itemsize * 8, ctypes.c_void_p(12))
    load_texture_pygame(texture_filepath, textures[-1])

    # normals
    glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, obj_buffer.itemsize * 8, ctypes.c_void_p(20))
    glEnableVertexAttribArray(2)

    return len(VAOs)-1

def rot_matrix_x_44(degrees):
    c, s = np.cos(np.deg2rad(degrees)), np.sin(np.deg2rad(degrees))
    return np.array(((1, 0, 0, 0), (0, c, s, 0), (0, -s, c, 0), (0, 0, 0, 1)))

def rot_matrix_y_44(degrees):
    c, s = np.cos(np.deg2rad(degrees)), np.sin(np.deg2rad(degrees))
    return np.array(((c, 0, -s, 0), (0, 1, 0, 0), (s, 0, c, 0), (0, 0, 0, 1)))

def rot_matrix_z_44(degrees):
    c, s = np.cos(np.deg2rad(degrees)), np.sin(np.deg2rad(degrees))
    return np.array(((c, -s, 0, 0), (s, c, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))

def draw_obj(obj_index, xpos, ypos, zpos, roll, pitch, yaw, obj_loc):
    #TODO We really should only change obj_pos upon updated pos or rotation
    translation_matrix = pyrr.matrix44.create_from_translation(pyrr.Vector3([xpos, ypos, zpos]))
    rot_x = rot_matrix_x_44(roll)
    rot_y = rot_matrix_y_44(pitch)
    rot_z = rot_matrix_z_44(yaw)
    pos_matrix = pyrr.matrix44.multiply(pyrr.matrix44.multiply(pyrr.matrix44.multiply(rot_x, rot_y), rot_z), translation_matrix)
    #rot_y = pyrr.Matrix44.from_y_rotation(-0.8 * glfw.get_time())

    # draw the obj
    glBindVertexArray(VAOs[obj_index])
    glBindTexture(GL_TEXTURE_2D, textures[obj_index])
    glUniformMatrix4fv(obj_loc, 1, GL_FALSE, pos_matrix)
    glDrawArrays(GL_TRIANGLES, 0, buf_lens[obj_index])

def rotate_obj(obj_index, pitch, roll, yaw):
    # Create rotation matrices from the euler angles
    pass


'''
        def label_axis(x, y, z, label):
            glRasterPos3f(x, y, z)
            glut.glutBitmapString(glut.GLUT_BITMAP_HELVETICA_18,
                                  str(label))
        def label_axis_for_feature(x, y, z, feature_ind):
            feature = self.octant_features[feature_ind[0]][feature_ind[1]]
            label_axis(x, y, z, self.labels[feature])

        if self._have_glut:
            try:
                import OpenGL.GLUT as glut
                if bool(glut.glutBitmapString):
                    if self.quadrant_mode == 'independent':
                        label_axis(1.05, 0.0, 0.0, 'x')
                        label_axis(0.0, 1.05, 0.0, 'y')
                        label_axis(0.0, 0.0, 1.05, 'z')
                    elif self.quadrant_mode == 'mirrored':
                        label_axis_for_feature(1.05, 0.0, 0.0, (0, 0))
                        label_axis_for_feature(0.0, 1.05, 0.0, (0, 1))
                        label_axis_for_feature(0.0, 0.0, 1.05, (0, 2))
                        label_axis_for_feature(-1.05, 0.0, 0.0, (6, 0))
                        label_axis_for_feature(0.0, -1.05, 0.0, (6, 1))
                        label_axis_for_feature(0.0, 0.0, -1.05, (6, 2))
                    else:
                        label_axis_for_feature(1.05, 0.0, 0.0, (0, 0))
                        label_axis_for_feature(0.0, 1.05, 0.0, (0, 1))
                        label_axis_for_feature(0.0, 0.0, 1.05, (0, 2))
            except:
                pass
'''
'''
C++ OpenGL lines with shaders example
struct LineSegment_t
{
  float x1, y1;
  float r1,g1,b1,a1;
  float x2, y2;
  float r2,g2,b2,a2;
};

int num_verts = lines.size()*2;
glBindVertexArray( line_vao ); // setup for the layout of LineSegment_t
glBindBuffer(GL_ARRAY_BUFFER, LineBufferObject);
glBufferData(GL_ARRAY_BUFFER, sizeof(LineSegment_t)/2 * num_verts, &lines[0], GL_DYNAMIC_DRAW);
glDrawArrays(GL_LINES, 0, num_verts );
'''

''' Another possible exmple
GLfloat lineSeg[] =
{
    0.0f, 0.0f, 0.0f, // first vertex
    2.0f, 0.0f, 2.0f // second vertex
};

GLuint lineVAO, lineVBO;
glGenVertexArrays(1, &lineVAO);
glGenBuffers(1, &lineVBO);
glBindVertexArray(lineVAO);
glBindBuffer(GL_ARRAY_BUFFER, lineVBO);
glBufferData(GL_ARRAY_BUFFER, sizeof(lineSeg), &lineSeg, GL_STATIC_DRAW);
glEnableVertexAttribArray(0);
glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(GLfloat), (void*)0);
'''

# Returns the index of the object in VAOs, buf_lens, 
def load_line(x1, y1, z1, x2, y2, z2, red, green, blue):
    VAOs.append(glGenVertexArrays(1))
    VBOs.append(glGenBuffers(1))
    buf = np.array([x1, y1, z1, x2, y2, z2], dtype='float32')
    buf_lens.append(2)

    # Vertex Array Object
    glBindVertexArray(VAOs[-1])
    glBindBuffer(GL_ARRAY_BUFFER, VBOs[-1])
    glBufferData(GL_ARRAY_BUFFER, buf.nbytes, buf, GL_STATIC_DRAW)
    glEnableVertexAttribArray(0)    # THIS CAUSES CRASH!! TODO
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * 4, None)
    return len(VBOs)-1


def draw_lines(obj_index, obj_loc):
    translation_matrix = pyrr.matrix44.create_from_translation(pyrr.Vector3([0, 0, 0]))
    glBindVertexArray(VAOs[obj_index])
    glBindBuffer(GL_ARRAY_BUFFER, VBOs[obj_index])
    glColor3f(0.0, 1.0, 0.0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * 4, None)
    glUniformMatrix4fv(obj_loc, 1, GL_FALSE, translation_matrix)
    glDrawArrays(GL_LINES, 0, buf_lens[obj_index])
    #glDisableVertexAttribArray(0); //?
    #glBindBuffer(GL_ARRAY_BUFFER, 0); //Unbind


def main():
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE) # |pygame.FULLSCREEN
    pygame.mouse.set_visible(True)
    pygame.event.set_grab(True)

    #gluPerspective(45, (WIDTH / HEIGHT), 0.1, 50.0)

    shader = compileProgram(compileShader(vertex_src, GL_VERTEX_SHADER), compileShader(fragment_src, GL_FRAGMENT_SHADER))

    glUseProgram(shader)
    glClearColor(0, 0.1, 0.1, 1)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    projection = pyrr.matrix44.create_perspective_projection_matrix(45, WIDTH / HEIGHT, 0.1, 100)

    model_loc = glGetUniformLocation(shader, "model")
    proj_loc = glGetUniformLocation(shader, "projection")
    view_loc = glGetUniformLocation(shader, "view")

    glUniformMatrix4fv(proj_loc, 1, GL_FALSE, projection)

    running = True

    #earth_index = load_obj("meshes/earth.obj", "meshes/earth.png")

    line1 = load_line(0, 0, 0, 50, 0, 0, 1, 0, 0)
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
        glUniformMatrix4fv(view_loc, 1, GL_FALSE, view)

        rot_y = 0.02 * pygame.time.get_ticks()
        #draw_obj(earth_index, 0, 0, 0, 0, rot_y, 22.5, model_loc)
        draw_lines(line1, model_loc)
        pygame.display.flip()
        pygame.time.wait(10)

    pygame.quit()

main()