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
	LPDIRECT3DVERTEXBUFFER9		vbuffer;
	LPDIRECT3DVERTEXBUFFER9		instancevbuffer;
	LPDIRECT3DVERTEXDECLARATION9 vdecl;
	LPDIRECT3DINDEXBUFFER9		indexbuffer;
	LPDIRECT3DSURFACE9			backbuffer;
	LPDIRECT3DSURFACE9			depthbuffer;
	LPDIRECT3DTEXTURE9			renderbuffertex;
	LPDIRECT3DSURFACE9			renderbuffer;
	LPDIRECT3DTEXTURE9			postbuffer1tex;
	LPDIRECT3DSURFACE9			postbuffer1;
	LPDIRECT3DTEXTURE9			postbuffer2tex;
	LPDIRECT3DSURFACE9			postbuffer2;
	LPDIRECT3DSURFACE9			renderdepthbuffer;
	LPDIRECT3DTEXTURE9			renderdepthbuffertex;
	LPDIRECT3DSURFACE9			cubedepth;
	LPDIRECT3DSURFACE9			dummysurface;
	LPDIRECT3DVOLUMETEXTURE9	randomtex;
	LPDIRECT3DVOLUMETEXTURE9	textures[N_OBJECTS]; // Object shape textures
	LPDIRECT3DVOLUMETEXTURE9	dtextures[N_OBJECTS]; // Detail textures
	LPD3DXMESH					meshes[N_OBJECTS];
	LPDIRECT3DCUBETEXTURE9		cubetex[N_LIGHTS];
};

extern "C" {
	extern COMStruct COMHandles;
};

#define RELEASE(o) do { if ((o) != NULL) { (o)->Release(); o = NULL; } } while (0)

#endif