#ifndef _COMCALL_H_
#define _COMCALL_H_

#include <d3d9.h>
#include <d3dx9.h>
#include "constants.h"

struct COMStruct {
	LPDIRECT3DDEVICE9			device;
	LPD3DXMATRIXSTACK			matrix_stack;
	LPD3DXEFFECT				effect;
	LPD3DXEFFECTCOMPILER		effectcompiler;
	LPD3DXBUFFER				tshaderbuffer;
	LPD3DXTEXTURESHADER			tshader;
	LPDIRECT3DSURFACE9			backbuffer;
	LPDIRECT3DSURFACE9			depthbuffer;
	LPD3DXMESH					meshes[N_OBJECTS];
};

extern "C" {
	extern COMStruct COMHandles;
};

#endif