
#include "engine_atrium.h"
#include "main.h"
#include "comcall.h"
#include "MemoryFile.h"
#include <assert.h>

extern "C" {
	extern RECT scissorRect;
	extern float constantPool[256];
};

float AtriumEngine::getaspect()
{
	return 16.0f / 9.0f;
}

void AtriumEngine::makeobjects()
{
	CHECK(D3DXCreateBox(COMHandles.device, 1.0f, 1.0f, 1.0f, &COMHandles.meshes[0], NULL));
	for (int i = 1 ; i < N_OBJECTS ; i++)
	{
		COMHandles.meshes[i] = NULL;
	}
}

void AtriumEngine::prepare_render_surfaces()
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


void AtriumEngine::init()
{
	makeobjects();
}

void AtriumEngine::reinit()
{
	render_width = 0;
	render_height = 0;
	last_fov = 0.0f;
}

void AtriumEngine::deinit()
{
	for (int i = 0 ; i < N_OBJECTS ; i++)
	{
		if (COMHandles.meshes[i]) COMHandles.meshes[i]->Release();
	}
}

static float fullscreenquad[] = {
	-1.0,  1.0, 0.0, 0.0, 0.0,
	 1.0,  1.0, 0.0, 1.0, 0.0,
	-1.0, -1.0, 0.0, 0.0, 1.0,
	 1.0, -1.0, 0.0, 1.0, 1.0
};

void AtriumEngine::blit_to_screen(int pass)
{
	CHECK(COMHandles.effect->BeginPass(pass));
	//COMHandles.device->SetRenderState(D3DRS_CULLMODE, D3DCULL_NONE);
	CHECK(COMHandles.device->SetTexture(0, COMHandles.renderbuffertex));
	CHECK(COMHandles.device->SetFVF(D3DFVF_XYZ|D3DFVF_TEX1));
	CHECK(COMHandles.device->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, fullscreenquad, 5*sizeof(float)));
	CHECK(COMHandles.effect->EndPass());
}

void AtriumEngine::render()
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

void AtriumEngine::drawprimitive(float r, float g, float b, float a, int index)
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

void AtriumEngine::placelight(float r, float g, float b, float a, int index)
{
}

void AtriumEngine::placecamera()
{
}

float AtriumEngine::random()
{
	return mentor_synth_random();
}
