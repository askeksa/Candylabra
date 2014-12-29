
#include "engine_uboat.h"
#include "main.h"
#include "comcall.h"
#include "MemoryFile.h"
#include <assert.h>

#define SHADOWSIZE 2048

extern "C" {
	extern RECT scissorRect;
	extern float constantPool[256];
};

float UBoatEngine::getaspect()
{
	return 16.0f / 9.0f;
}

void UBoatEngine::maketexts(char *texts, int size)
{
	LPD3DXMESH mesh = NULL;
	HDC hdc = CreateCompatibleDC( NULL );
	HFONT hFont;
	HFONT hFontOld;

	int t = 0;

	bool readfont = true;
	bool firstfont = true;
	for (int i = 0 ; i < N_OBJECTS ; i++)
	{
		float fontex;
		if (readfont)
		{
			char fontname[100];
			int fontsize;
			int n = sscanf(&texts[t], "%s %d %f\n", &fontname, &fontsize, &fontex);
			if (n >= 3)
			{
				while (t < size && texts[t] >= ' ') t++;
				while (t < size && texts[t] < ' ') t++;
				for (unsigned j = 0 ; j < strlen(fontname) ; j++)
				{
					if (fontname[j] == '_') fontname[j] = ' ';
				}

				if (!firstfont) SelectObject(hdc, hFontOld);
				firstfont = false;
				hFont = CreateFont(fontsize, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET, 
					OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, DEFAULT_QUALITY, DEFAULT_PITCH | FF_DONTCARE, fontname);
				hFontOld = (HFONT)SelectObject(hdc, hFont); 
			}
			readfont = false;
		}

		int next_t = t;
		while (next_t < size && texts[next_t] >= ' ') next_t++;

		if (next_t < size)
		{
			bool empty = next_t == t+3 && texts[t] == '-' && texts[t+1] == '-' && texts[t+2] == '-';
			texts[next_t++] = 0;
			while (next_t < size && texts[next_t] < ' ') next_t++;
			if (!empty)
			{
				CHECK(D3DXCreateText(COMHandles.device, hdc, &texts[t], 0.00048828125f, fontex, &COMHandles.meshes[i], NULL, NULL));
			} else {
				readfont = true;
				i--;
			}
			t = next_t;
		} else {
			COMHandles.meshes[i] = NULL;
		}
	}

	SelectObject(hdc, hFontOld);

	DeleteObject( hFont );
	DeleteDC( hdc );
}

void UBoatEngine::prepare_render_surfaces()
{
	int width = scissorRect.right-scissorRect.left;
	int	height = scissorRect.bottom - scissorRect.top;
	if (render_width != width || render_height != height)
	{
		if (COMHandles.renderbuffer) COMHandles.renderbuffer->Release();
		if (COMHandles.renderbuffertex) COMHandles.renderbuffertex->Release();
		if (COMHandles.renderdepthbuffer) COMHandles.renderdepthbuffer->Release();
		if (COMHandles.renderdepthbuffertex) COMHandles.renderdepthbuffertex->Release();

		CHECK(COMHandles.device->CreateTexture(width, height, 1, D3DUSAGE_RENDERTARGET, D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, &COMHandles.renderbuffertex, NULL));
		CHECK(COMHandles.renderbuffertex->GetSurfaceLevel(0, &COMHandles.renderbuffer));

		CHECK(COMHandles.device->CreateTexture(width, height, 1, D3DUSAGE_DEPTHSTENCIL, (D3DFORMAT)MAKEFOURCC('I','N','T','Z'), D3DPOOL_DEFAULT, &COMHandles.renderdepthbuffertex, NULL));
		CHECK(COMHandles.renderdepthbuffertex->GetSurfaceLevel(0, &COMHandles.renderdepthbuffer));

		render_width = width;
		render_height = height;
		last_fov = 0.0f;

	}
}


void UBoatEngine::init()
{
	MemoryFile object_texts(datafile, false);
	if (object_texts.getSize() > 0)
	{
		maketexts((char *)object_texts.getPtr(), object_texts.getSize());
	}

	// Shadow map
	CHECK(COMHandles.device->CreateTexture(SHADOWSIZE, SHADOWSIZE, 1, D3DUSAGE_DEPTHSTENCIL, (D3DFORMAT)MAKEFOURCC('I','N','T','Z'), D3DPOOL_DEFAULT, &COMHandles.postbuffer1tex, NULL));
	CHECK(COMHandles.postbuffer1tex->GetSurfaceLevel(0, &COMHandles.postbuffer1));
	CHECK(COMHandles.device->CreateRenderTarget(SHADOWSIZE, SHADOWSIZE, D3DFMT_A8R8G8B8, D3DMULTISAMPLE_NONE, 0, false, &COMHandles.dummysurface, NULL));

	// Light/particle buffer
	CHECK(COMHandles.device->CreateTexture(800, 480, 1, D3DUSAGE_RENDERTARGET, D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, &COMHandles.postbuffer2tex, NULL));
	CHECK(COMHandles.postbuffer2tex->GetSurfaceLevel(0, &COMHandles.postbuffer2));
}

void UBoatEngine::reinit()
{
	deinit();
	render_width = 0;
	render_height = 0;
	last_fov = 0.0f;
	init();
}

void UBoatEngine::deinit()
{
	for (int i = 0 ; i < N_OBJECTS ; i++)
	{
		if (COMHandles.meshes[i]) COMHandles.meshes[i]->Release();
	}
}

void UBoatEngine::render()
{
	D3DXTECHNIQUE_DESC tdesc;
	CHECK(COMHandles.effect->GetTechniqueDesc(COMHandles.effect->GetTechnique(0), &tdesc));

	CHECK(COMHandles.effect->Begin(0, 0));

	prepare_render_surfaces();

	// Shadow map
	CHECK(COMHandles.device->SetRenderTarget(0, COMHandles.dummysurface));
	CHECK(COMHandles.device->SetDepthStencilSurface(COMHandles.postbuffer1));
	CHECK(COMHandles.device->Clear(0, NULL, D3DCLEAR_ZBUFFER | D3DCLEAR_TARGET, 0x00ffff00, 1.0f, 0));
	CHECK(COMHandles.device->SetRenderState(D3DRS_ALPHATESTENABLE, FALSE));
	CHECK(COMHandles.device->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE));
	CHECK(COMHandles.device->SetRenderState(D3DRS_POINTSPRITEENABLE, FALSE));
	pass(0,0);

	// Solid objects on screen
	CHECK(COMHandles.device->SetRenderTarget(0, COMHandles.renderbuffer));
	CHECK(COMHandles.device->SetDepthStencilSurface(COMHandles.renderdepthbuffer));
	CHECK(COMHandles.effect->SetTexture("t0", COMHandles.postbuffer1tex));
	CHECK(COMHandles.device->Clear(0, NULL, D3DCLEAR_ZBUFFER | D3DCLEAR_TARGET, 0x00ff0000, 1.0f, 0));
	pass(1,1);

	// bubbles
	CHECK(COMHandles.device->SetRenderTarget(0, COMHandles.postbuffer2));
	CHECK(COMHandles.device->SetDepthStencilSurface(NULL));
	CHECK(COMHandles.effect->SetTexture("t1", COMHandles.renderdepthbuffertex));
	CHECK(COMHandles.effect->SetTexture("t2", COMHandles.renderbuffertex));
	CHECK(COMHandles.device->Clear(0, NULL, D3DCLEAR_TARGET, 0x00000000, 1.0f, 0));
	pass(2,2);

	// Light beams
	CHECK(COMHandles.device->SetRenderState(D3DRS_ALPHABLENDENABLE, TRUE));
	CHECK(COMHandles.device->SetRenderState(D3DRS_SRCBLEND, D3DBLEND_ONE));
	CHECK(COMHandles.device->SetRenderState(D3DRS_DESTBLEND, D3DBLEND_ONE));
	CHECK(COMHandles.device->SetRenderState(D3DRS_FILLMODE, D3DFILL_POINT));
	pass(3,3);

	view_display();
	CHECK(COMHandles.effect->SetTexture("t3", COMHandles.postbuffer2tex));
	CHECK(COMHandles.device->Clear(0, NULL, D3DCLEAR_ZBUFFER | D3DCLEAR_TARGET, 0x00000000, 1.0f, 0));
	CHECK(COMHandles.device->SetRenderState(D3DRS_FILLMODE, D3DFILL_SOLID));
	pass(4,4);

	CHECK(COMHandles.effect->SetTexture("t0", NULL));
	CHECK(COMHandles.effect->SetTexture("t1", NULL));
	CHECK(COMHandles.effect->SetTexture("t2", NULL));
	CHECK(COMHandles.effect->SetTexture("t3", NULL));

	CHECK(COMHandles.effect->End());
}

void UBoatEngine::drawprimitive(float r, float g, float b, float a, int index)
{
	uploadparams();

	CHECK(COMHandles.effect->SetMatrixTranspose("m", COMHandles.matrix_stack->GetTop()));
	COMHandles.effect->SetRawValue("c", &r, 0, 16);
	CHECK(COMHandles.effect->CommitChanges());

	if (COMHandles.meshes[index] != NULL) CHECK(COMHandles.meshes[index]->DrawSubset(0));
}

void UBoatEngine::placelight(float r, float g, float b, float a, int index)
{
	COMHandles.effect->SetRawValue("l", &r, 0, 16);

	D3DXMATRIX *trans = COMHandles.matrix_stack->GetTop();
	float dir[3] = { trans->_31, trans->_32, trans->_33 };
	CHECK(COMHandles.effect->SetRawValue("s", dir, 0, 12)); // sun direction

	D3DXMATRIXA16 shadowproj;
	D3DXMatrixOrthoLH(&shadowproj, 2.0f, 2.0f, -1.0f, 1.0f);

	COMHandles.matrix_stack->Push();
	D3DXMatrixInverse(COMHandles.matrix_stack->GetTop(), NULL, COMHandles.matrix_stack->GetTop());
	COMHandles.matrix_stack->MultMatrix(&shadowproj);
	CHECK(COMHandles.effect->SetMatrixTranspose("sp", COMHandles.matrix_stack->GetTop()));
	COMHandles.matrix_stack->Pop();
}

void UBoatEngine::placecamera()
{
	setfov();

	D3DXMATRIX *trans = COMHandles.matrix_stack->GetTop();
	float pos[3] = { trans->_41, trans->_42, trans->_43 };
	CHECK(COMHandles.effect->SetRawValue("e", pos, 0, 12)); // eye position

	COMHandles.matrix_stack->Push();
	D3DXMatrixInverse(COMHandles.matrix_stack->GetTop(), NULL, COMHandles.matrix_stack->GetTop());
	COMHandles.matrix_stack->MultMatrix(&proj);
	CHECK(COMHandles.effect->SetMatrixTranspose("vp", COMHandles.matrix_stack->GetTop()));
	D3DXMatrixInverse(COMHandles.matrix_stack->GetTop(), NULL, COMHandles.matrix_stack->GetTop());
	CHECK(COMHandles.effect->SetMatrixTranspose("ivp", COMHandles.matrix_stack->GetTop()));
	COMHandles.matrix_stack->Pop();
}

float UBoatEngine::random()
{
	return mentor_synth_random();
}
