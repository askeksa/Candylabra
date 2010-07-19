
#include "engine_textobj.h"
#include "main.h"
#include "comcall.h"
#include "MemoryFile.h"
#include <assert.h>

extern "C" {
	extern RECT scissorRect;
	extern float constantPool[256];
};

float TextObjectEngine::getaspect()
{
	return 4.0f / 3.0f;
}

void TextObjectEngine::maketexts(char *texts, int size)
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
				hFont = CreateFont(fontsize, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, 
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
				CHECK(D3DXCreateText(COMHandles.device, hdc, &texts[t], 0.001f, fontex, &COMHandles.meshes[i], NULL, NULL));
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

void TextObjectEngine::prepare_render_surfaces()
{
	int width = scissorRect.right-scissorRect.left;
	int	height = scissorRect.bottom - scissorRect.top;
	if (render_width != width || render_height != height)
	{
		if (COMHandles.renderbuffer) COMHandles.renderbuffer->Release();
		if (COMHandles.renderbuffertex) COMHandles.renderbuffertex->Release();
		if (COMHandles.renderdepthbuffer) COMHandles.renderdepthbuffer->Release();
		CHECK(COMHandles.device->CreateTexture(width, height, 1, D3DUSAGE_RENDERTARGET, D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, &COMHandles.renderbuffertex, NULL));
		CHECK(COMHandles.device->CreateDepthStencilSurface(width, height, D3DFMT_D16, D3DMULTISAMPLE_NONE, 0, TRUE, &COMHandles.renderdepthbuffer, NULL));
		render_width = width;
		render_height = height;
		last_fov = 0.0f;

		CHECK(COMHandles.renderbuffertex->GetSurfaceLevel(0, &COMHandles.renderbuffer));
	}

	CHECK(COMHandles.device->SetRenderTarget(0, COMHandles.renderbuffer));
	CHECK(COMHandles.device->SetDepthStencilSurface(COMHandles.renderdepthbuffer));
}


void TextObjectEngine::init()
{
	MemoryFile object_texts("texts.txt", false);
	if (object_texts.getSize() > 0)
	{
		maketexts((char *)object_texts.getPtr(), object_texts.getSize());
	}
}

void TextObjectEngine::reinit()
{
	deinit();
	render_width = 0;
	render_height = 0;
	last_fov = 0.0f;
	init();
}

void TextObjectEngine::deinit()
{
	for (int i = 0 ; i < N_OBJECTS ; i++)
	{
		if (COMHandles.meshes[i]) COMHandles.meshes[i]->Release();
	}
}

float fullscreenquad[] = {
	-1.0,  1.0, 0.0, 0.0, 0.0,
	 1.0,  1.0, 0.0, 1.0, 0.0,
	-1.0, -1.0, 0.0, 0.0, 1.0,
	 1.0, -1.0, 0.0, 1.0, 1.0
};

void TextObjectEngine::blit_to_screen(int pass)
{
	CHECK(COMHandles.effect->BeginPass(pass));
	//COMHandles.device->SetRenderState(D3DRS_CULLMODE, D3DCULL_NONE);
	CHECK(COMHandles.device->SetTexture(0, COMHandles.renderbuffertex));
	CHECK(COMHandles.device->SetFVF(D3DFVF_XYZ|D3DFVF_TEX1));
	CHECK(COMHandles.device->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, fullscreenquad, 5*sizeof(float)));
	CHECK(COMHandles.effect->EndPass());
}

void TextObjectEngine::render()
{
	D3DXTECHNIQUE_DESC tdesc;
	CHECK(COMHandles.effect->GetTechniqueDesc(COMHandles.effect->GetTechnique(0), &tdesc));

	CHECK(COMHandles.effect->Begin(0, 0));

	prepare_render_surfaces();
	CHECK(COMHandles.device->Clear(0, NULL, D3DCLEAR_ZBUFFER | D3DCLEAR_TARGET, 0xff000000, 1.0f, 0));
	CHECK(COMHandles.device->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE));
	for (unsigned p = 0 ; p < tdesc.Passes-1 ; p++)
	{
		//CHECK(COMHandles.matrix_stack->LoadMatrix(&proj));
		pass(p,p);
	}

	view_display();
	blit_to_screen(tdesc.Passes-1);

	CHECK(COMHandles.effect->End());
}

void TextObjectEngine::drawprimitive(float r, float g, float b, float a, int index)
{
	uploadparams();

	if (constantPool[2] != last_fov)
	{
		setfov();
		CHECK(COMHandles.effect->SetMatrixTranspose("o", &proj));
		last_fov = constantPool[2];
	}

	CHECK(COMHandles.effect->SetMatrixTranspose("m", COMHandles.matrix_stack->GetTop()));
	COMHandles.effect->SetRawValue("c", &r, 0, 16);
	CHECK(COMHandles.effect->CommitChanges());

	if (COMHandles.meshes[index] != NULL) CHECK(COMHandles.meshes[index]->DrawSubset(0));
}

void TextObjectEngine::placelight(float r, float g, float b, float a, int index)
{
}

void TextObjectEngine::placecamera()
{
}

float TextObjectEngine::random()
{
	return mentor_synth_random();
}
