
#include "engine_ikadalawampu.h"
#include "main.h"
#include "comcall.h"
#include <assert.h>

#define AMIGA_WIDTH 320
#define AMIGA_HEIGHT 200

extern "C" {
	extern float constantPool[256];
};

float IkadalawampuEngine::getaspect()
{
	return AMIGA_WIDTH/(float)AMIGA_HEIGHT;
}

static const float quad[] = {
	-1.0,  1.0, 0.0,
	1.0,  1.0, 0.0,
	-1.0, -1.0, 0.0,
	1.0, -1.0, 0.0
};

void IkadalawampuEngine::init()
{
	CHECK(COMHandles.device->CreateTexture(AMIGA_WIDTH,AMIGA_HEIGHT, 1,D3DUSAGE_RENDERTARGET, D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, &COMHandles.renderbuffertex, NULL));
	CHECK(COMHandles.renderbuffertex->GetSurfaceLevel(0, &COMHandles.renderbuffer));
}

void IkadalawampuEngine::reinit()
{
}

void IkadalawampuEngine::deinit()
{
	RELEASE(COMHandles.renderbuffertex);
}

void IkadalawampuEngine::render()
{
	constantPool[2] = 1.0f;
	setfov();

	CHECK(COMHandles.effect->Begin(0, 0));

	CHECK(COMHandles.device->SetRenderTarget(0, COMHandles.renderbuffer));
	CHECK(COMHandles.device->SetDepthStencilSurface(NULL));
	CHECK(COMHandles.device->Clear(0, NULL, D3DCLEAR_TARGET, D3DCOLOR_RGBA(0,0,0,255), 1.0f, 0));
	CHECK(COMHandles.device->SetRenderState(D3DRS_ALPHABLENDENABLE, TRUE));
	CHECK(COMHandles.device->SetRenderState(D3DRS_SRCBLEND, D3DBLEND_ONE));
	CHECK(COMHandles.device->SetRenderState(D3DRS_DESTBLEND, D3DBLEND_ONE));
	pass(0,0);

	view_display();
	CHECK(COMHandles.effect->BeginPass(1));
	CHECK(COMHandles.device->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE));
	CHECK(COMHandles.device->SetTexture(0, COMHandles.renderbuffertex));
	CHECK(COMHandles.device->SetSamplerState(0, D3DSAMP_MINFILTER, D3DTEXF_LINEAR));
	CHECK(COMHandles.device->SetSamplerState(0, D3DSAMP_MAGFILTER, D3DTEXF_POINT));
	CHECK(COMHandles.device->SetFVF(D3DFVF_XYZ));
	CHECK(COMHandles.device->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, quad, 3*sizeof(float)));
	CHECK(COMHandles.effect->EndPass());

	CHECK(COMHandles.effect->End());
}

void IkadalawampuEngine::drawprimitive(float r, float g, float b, float a, int index)
{
	uploadparams();

	CHECK(COMHandles.effect->SetMatrixTranspose("m", COMHandles.matrix_stack->GetTop()));
	CHECK(COMHandles.effect->SetRawValue("c", &r, 0, 16));
	float sz[2] = { (float)AMIGA_WIDTH, (float)AMIGA_HEIGHT };
	CHECK(COMHandles.effect->SetRawValue("screensize", &sz, 0, 8));
	CHECK(COMHandles.effect->CommitChanges());

	CHECK(COMHandles.device->SetTexture(0, NULL));
	CHECK(COMHandles.device->SetFVF(D3DFVF_XYZ));
	CHECK(COMHandles.device->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, quad, 3*sizeof(float)));
}

void IkadalawampuEngine::placelight(float r, float g, float b, float a, int index)
{
}

void IkadalawampuEngine::placecamera()
{
}

float IkadalawampuEngine::random()
{
	return amiga_random();
}
