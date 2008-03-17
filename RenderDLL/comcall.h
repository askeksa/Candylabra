#ifndef _COMCALL_H_
#define _COMCALL_H_

#include <d3d9.h>
#include <d3dx9.h>
#include "constants.h"

struct COMStruct {
	LPDIRECT3DDEVICE9			device;
	LPD3DXMATRIXSTACK			matrix_stack;
	LPDIRECT3DINDEXBUFFER9		composite_index;
	LPDIRECT3DVERTEXBUFFER9		composite_vertex;
	LPD3DXEFFECT				effect;
	LPDIRECT3DTEXTURE9			textures[NUM_TEXTURES];
	LPDIRECT3DSURFACE9			surfaces[NUM_TEXTURES];
	LPDIRECT3DSURFACE9			backbuffer;
	LPDIRECT3DSURFACE9			depthbuffer;
	LPDIRECT3DSURFACE9			newbacksurface;
	LPDIRECT3DSURFACE9			newdepthbuffer;
};

extern "C" {
	extern COMStruct COMHandles;
};

#endif