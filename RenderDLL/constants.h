#ifndef _CONSTANTS_H_
#define _CONSTANTS_H_

#include <d3d9.h>

static const int N_OBJECTS = 5;
static const int N_LIGHTS = 2;
static const int CUBESIZE = 512;

static const int MAX_VERTICES = 1638400;
static const int MAX_FACES = 3276800;
static const int MY_FVF = (D3DFVF_XYZ|D3DFVF_NORMAL|D3DFVF_DIFFUSE);

static const int NUM_TEXTURES = 2;
static const int TEXTURE_WIDTH = 512;
static const int TEXTURE_HEIGHT = 512;


#endif