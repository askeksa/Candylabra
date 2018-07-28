
#include "engine_sprites.h"
#include "main.h"
#include "comcall.h"
#include "MemoryFile.h"
#include <assert.h>

extern "C" {
	extern RECT scissorRect;
	extern float constantPool[256];
	void Oidos_FillRandomData();
};

SpritesEngine::SpritesEngine() : render_width(0), render_height(0) {
	Oidos_FillRandomData();
}

float SpritesEngine::getaspect()
{
	return 16.0f / 9.0f;
}

void SpritesEngine::makesprites(char *path, int size)
{
	char filename[256];
	memcpy(filename, path, size);
	int pathlength = 0;
	while (pathlength < size && filename[pathlength] > 32) pathlength++;
	for (int i = 0; i < N_OBJECTS; i++) {
		sprintf(&filename[pathlength], "%02d.png", i);
		D3DXCreateTextureFromFileEx(COMHandles.device, filename,
			D3DX_DEFAULT_NONPOW2, D3DX_DEFAULT_NONPOW2, D3DX_FROM_FILE,
			0, D3DFMT_UNKNOWN, D3DPOOL_MANAGED, D3DX_DEFAULT, D3DX_DEFAULT, 0,
			&COMHandles.sprite_info[i], NULL, &COMHandles.sprites[i]);
	}
}

void SpritesEngine::prepare_render_surfaces()
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

		CHECK(COMHandles.renderbuffertex->GetSurfaceLevel(0, &COMHandles.renderbuffer));
	}

	CHECK(COMHandles.device->SetRenderTarget(0, COMHandles.renderbuffer));
	CHECK(COMHandles.device->SetDepthStencilSurface(COMHandles.renderdepthbuffer));
}


void SpritesEngine::init()
{
	MemoryFile object_texts(datafile, false);
	if (object_texts.getSize() > 0)
	{
		makesprites((char *)object_texts.getPtr(), object_texts.getSize());
	}
}

void SpritesEngine::reinit()
{
	deinit();
	render_width = 0;
	render_height = 0;
	init();
}

void SpritesEngine::deinit()
{
	for (int i = 0 ; i < N_OBJECTS ; i++)
	{
		if (COMHandles.sprites[i]) {
			COMHandles.sprites[i]->Release();
			COMHandles.sprites[i] = NULL;
		}
	}
}

static float fullscreenquad[] = {
	-1.0,  1.0, 0.0, 0.0, 0.0,
	 1.0,  1.0, 0.0, 1.0, 0.0,
	-1.0, -1.0, 0.0, 0.0, 1.0,
	 1.0, -1.0, 0.0, 1.0, 1.0
};

void SpritesEngine::blit_to_screen(int pass)
{
	CHECK(COMHandles.effect->BeginPass(pass));
	//COMHandles.device->SetRenderState(D3DRS_CULLMODE, D3DCULL_NONE);
	CHECK(COMHandles.device->SetTexture(0, COMHandles.renderbuffertex));
	CHECK(COMHandles.device->SetFVF(D3DFVF_XYZ|D3DFVF_TEX1));
	CHECK(COMHandles.device->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, fullscreenquad, 5*sizeof(float)));
	CHECK(COMHandles.effect->EndPass());
}

void SpritesEngine::render()
{
	D3DXTECHNIQUE_DESC tdesc;
	CHECK(COMHandles.effect->GetTechniqueDesc(COMHandles.effect->GetTechnique(0), &tdesc));

	CHECK(COMHandles.effect->Begin(0, 0));

	prepare_render_surfaces();
	CHECK(COMHandles.device->Clear(0, NULL, D3DCLEAR_ZBUFFER | D3DCLEAR_TARGET, 0xff000000, 1.0f, 0));
	CHECK(COMHandles.device->SetSamplerState(0, D3DSAMP_MAGFILTER, D3DX_FILTER_LINEAR));
	CHECK(COMHandles.device->SetSamplerState(0, D3DSAMP_MINFILTER, D3DX_FILTER_LINEAR));
	CHECK(COMHandles.device->SetSamplerState(0, D3DSAMP_MIPFILTER, D3DX_FILTER_LINEAR));
	for (unsigned p = 0 ; p < tdesc.Passes-1 ; p++)
	{
		//CHECK(COMHandles.matrix_stack->LoadMatrix(&proj));
		CHECK(COMHandles.device->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE));
		pass(p,p);
	}

	view_display();
	blit_to_screen(tdesc.Passes-1);

	CHECK(COMHandles.effect->End());
}

void SpritesEngine::drawprimitive(float r, float g, float b, float a, int index)
{
	if (COMHandles.sprites[index] != NULL) {
		uploadparams();

		CHECK(COMHandles.effect->SetMatrixTranspose("m", COMHandles.matrix_stack->GetTop()));
		COMHandles.effect->SetRawValue("c", &r, 0, 16);
		float tsize[2];
		tsize[0] = float(COMHandles.sprite_info[index].Width);
		tsize[1] = float(COMHandles.sprite_info[index].Height);
		COMHandles.effect->SetRawValue("tsize", tsize, 0, 8);
		CHECK(COMHandles.effect->CommitChanges());

		CHECK(COMHandles.device->SetTexture(0, COMHandles.sprites[index]));
		CHECK(COMHandles.device->SetFVF(D3DFVF_XYZ | D3DFVF_TEX1));
		CHECK(COMHandles.device->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, fullscreenquad, 5 * sizeof(float)));
		CHECK(COMHandles.device->SetTexture(0, NULL));
	}
}

void SpritesEngine::placelight(float r, float g, float b, float a, int index)
{
}

void SpritesEngine::placecamera()
{
}

float SpritesEngine::random()
{
	return oidos_random();
}
