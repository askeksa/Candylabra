
#include "engine_eris.h"
#include "main.h"
#include "comcall.h"
#include "MemoryFile.h"
#include <assert.h>

extern char effectfile[];

float ErisEngine::getaspect()
{
	return 16.0f / 9.0f;
}

void maketexts(const unsigned char *text, int n_objects)
{
	LPD3DXMESH mesh = NULL;
	HDC hdc = CreateCompatibleDC( NULL );
	HFONT hFont;
	HFONT hFontOld;

	int t = 0;

	char *fontname = "Arial Black";
	int fontsize = 10;
	float fontex = 0.5f;
	hFont = CreateFont(fontsize, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, 
		OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, DEFAULT_QUALITY, DEFAULT_PITCH | FF_DONTCARE, fontname);
	hFontOld = (HFONT)SelectObject(hdc, hFont); 

	for (int i = 0 ; i < N_OBJECTS ; i++)
	{
		char one_char[2];
		one_char[0] = text[i];
		one_char[1] = 0;
		//MessageBox(0,one_char,0,0);
		if (one_char[0] != 0 && one_char[0] != ' ') {
			CHECK(D3DXCreateText(COMHandles.device, hdc, &one_char[0], 0.001f, fontex, &COMHandles.meshes[i], NULL, NULL));
		} else {
			COMHandles.meshes[i] = NULL;
		}
	}

	SelectObject(hdc, hFontOld);

	DeleteObject( hFont );
	DeleteDC( hdc );
}

static void init_effect_and_stuff()
{
	MemoryFile effect(effectfile);
	maketexts(effect.getPtr(), N_OBJECTS);
}

static void deinit_effect_and_stuff()
{
	for (int i = 0 ; i < N_OBJECTS ; i++)
	{
		RELEASE(COMHandles.meshes[i]);
	}
}

void ErisEngine::init()
{
	for (int i = 0 ; i < N_LIGHTS ; i++)
	{
		CHECK(COMHandles.device->CreateCubeTexture(CUBESIZE, 1, D3DUSAGE_RENDERTARGET, D3DFMT_R32F, D3DPOOL_DEFAULT, &COMHandles.cubetex[i], 0));
	}
	CHECK(COMHandles.device->CreateDepthStencilSurface(CUBESIZE, CUBESIZE, D3DFMT_D16, D3DMULTISAMPLE_NONE, 0, TRUE, &COMHandles.cubedepth, NULL));

	init_effect_and_stuff();
}

void ErisEngine::reinit()
{
	deinit_effect_and_stuff();
	init_effect_and_stuff();
}

void ErisEngine::deinit()
{
	deinit_effect_and_stuff();
	RELEASE(COMHandles.cubedepth);
	for (int i = 0 ; i < N_LIGHTS ; i++)
	{
		RELEASE(COMHandles.cubetex[i]);
	}
}

static D3DXMATRIX p[6] = {
	D3DXMATRIX(
	0,0,1,1,
	0,1,0,0,
	-1,0,0,0,
	0,0,-1,0
	),
	D3DXMATRIX(
	0,0,-1,-1,
	0,1,0,0,
	1,0,0,0,
	0,0,-1,0
	),
	D3DXMATRIX(
	1,0,0,0,
	0,0,1,1,
	0,-1,0,0,
	0,0,-1,0
	),
	D3DXMATRIX(
	1,0,0,0,
	0,0,-1,-1,
	0,1,0,0,
	0,0,-1,0
	),
	D3DXMATRIX(
	1,0,0,0,
	0,1,0,0,
	0,0,1,1,
	0,0,-1,0
	),
	D3DXMATRIX(
	-1,0,0,0,
	0,1,0,0,
	0,0,-1,-1,
	0,0,-1,0
	),
};

void ErisEngine::render()
{
	CHECK(COMHandles.effect->Begin(0, 0));

	for (int i = 0 ; i < N_LIGHTS ; i++)
	{
		char var[20];
		sprintf(var, "_cubetex%d", i);
		CHECK(COMHandles.effect->SetTexture(var, COMHandles.cubetex[i]));
	}

	CHECK(COMHandles.device->SetDepthStencilSurface(COMHandles.cubedepth));
	for (int i = 0 ; i < N_LIGHTS ; i++)
	{
		for (int f = 0 ; f < 6 ; f++) {
			IDirect3DSurface9 *face;
			CHECK(COMHandles.cubetex[i]->GetCubeMapSurface((D3DCUBEMAP_FACES)f, 0, &face));
			CHECK(COMHandles.device->SetRenderTarget(0, face));
			CHECK(COMHandles.device->Clear(0, NULL, D3DCLEAR_ZBUFFER | D3DCLEAR_TARGET, 0, 1.0f, 0));
			CHECK(COMHandles.effect->SetMatrixTranspose("fvm", &p[f]));
			pass(i,0);
		}
	}

	view_display();
	CHECK(COMHandles.device->Clear(0, NULL, D3DCLEAR_ZBUFFER | D3DCLEAR_TARGET, 0, 1.0f, 0));
	CHECK(COMHandles.effect->SetMatrixTranspose("vm", &proj));
	pass(3,1);
	CHECK(COMHandles.effect->SetMatrixTranspose("vm", &proj));
	pass(2,1);

	CHECK(COMHandles.effect->End());
}

void ErisEngine::setposition(char *name, int index)
{
	D3DXMATRIX *trans = COMHandles.matrix_stack->GetTop();
	float pos[3] = { trans->_41, trans->_42, trans->_43 };
	CHECK(COMHandles.effect->SetRawValue(name, pos, index*16, 12));
}

void ErisEngine::drawprimitive(float r, float g, float b, float a, int index)
{
	uploadparams();

	CHECK(COMHandles.effect->SetMatrixTranspose("m", COMHandles.matrix_stack->GetTop()));
	CHECK(COMHandles.effect->SetRawValue("c", &r, 0, 16));

	CHECK(COMHandles.effect->CommitChanges());

	if (index >= 0 && index < N_OBJECTS && COMHandles.meshes[index] != NULL)
	{
		CHECK(COMHandles.meshes[index]->DrawSubset(0));
	}
}

void ErisEngine::placelight(float r, float g, float b, float a, int index)
{
	setposition("ld", index);

	CHECK(COMHandles.effect->SetRawValue("lc", &r, index*16, 16));
	CHECK(COMHandles.effect->CommitChanges());
}

void ErisEngine::placecamera()
{
	setposition("d", 0);

	setfov();

	COMHandles.matrix_stack->Push();
	D3DXMatrixInverse(COMHandles.matrix_stack->GetTop(), NULL, COMHandles.matrix_stack->GetTop());
	COMHandles.matrix_stack->MultMatrix(&proj);
	CHECK(COMHandles.effect->SetMatrixTranspose("vm", COMHandles.matrix_stack->GetTop()));
	COMHandles.matrix_stack->Pop();
}
