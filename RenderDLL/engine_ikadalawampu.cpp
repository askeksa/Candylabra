
#include "engine_ikadalawampu.h"
#include "main.h"
#include "comcall.h"
#include <assert.h>

#define AMIGA_WIDTH 320
#define AMIGA_HEIGHT 200

extern "C" {
	extern float constantPool[256];
	extern int nodecount, subexpcount;
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

static void drawbar(float minx, float miny, float width, float height, float r, float g, float b, float a)
{
	float barquad[12] = {
		minx, miny+height, 0.0f,
		minx+width, miny+height, 0.0f,
		minx, miny, 0.0f,
		minx+width, miny, 0.0f
	};
	float c[4] = {r,g,b,a};
	CHECK(COMHandles.effect->SetRawValue("c", &c, 0, 16));
	CHECK(COMHandles.effect->CommitChanges());
	CHECK(COMHandles.device->SetFVF(D3DFVF_XYZ));
	CHECK(COMHandles.device->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, barquad, 3*sizeof(float)));
}

struct bar { float size; float r,g,b; };
static void drawbars(float minx, float miny, float width, float height, int nvblanks, struct bar *bars, int nbars)
{
	float bottom = miny;
	for (int i = 0 ; i < nbars ; i++)
	{
		float size = bars[i].size * height / nvblanks;
		drawbar(minx,bottom,width,size, bars[i].r, bars[i].g, bars[i].b, 1.0);
		bottom += size;
	}
	for (int v = 0 ; v <= nvblanks ; v++)
	{
		drawbar(minx-width*0.5f,miny+height*v/nvblanks,width*2,0.005, 1.0,1.0,1.0,1.0);
	}
}

void IkadalawampuEngine::render()
{
	constantPool[2] = 1.0f;
	setfov();

	nodecount = 0;
	subexpcount = 0;
	p_particles = 0;
	p_colortables = 0;
	p_lines = 0;
	p_pixels = 0;

	lastcolor0 = 0;
	lastcolor1 = 0;

	CHECK(COMHandles.effect->Begin(0, 0));

	float sz[2] = { (float)AMIGA_WIDTH, (float)AMIGA_HEIGHT };
	CHECK(COMHandles.effect->SetRawValue("screensize", &sz, 0, 8));

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

	CHECK(COMHandles.effect->BeginPass(2));
	CHECK(COMHandles.device->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE));
	CHECK(COMHandles.device->SetTexture(0, 0));
	struct bar bars[7] = {
		0.75, 0.4,0.4,0.4, // c2p+clear
		0.000040f*nodecount, 0.2,0.2,0.8,
		0.000040f*subexpcount, 0.2,0.6,0.6,
		0.000400f*p_particles, 0.2,0.8,0.2,
		0.001500f*p_colortables, 1.0,1.0,0.0,
		0.000100f*p_lines, 1.0,0.5,0.0,
		0.000010f*p_pixels, 1.0,0.0,0.0
	};
	drawbars(0.98,-0.9,0.01,1.8, 5, bars, 7);
	CHECK(COMHandles.effect->EndPass());

	CHECK(COMHandles.effect->End());
}

void IkadalawampuEngine::drawprimitive(float rcol, float gcol, float bdummy, float adummy, int index)
{
	uploadparams();

	const D3DXMATRIX *m = COMHandles.matrix_stack->GetTop();

	CHECK(COMHandles.effect->SetMatrixTranspose("m", m));
	CHECK(COMHandles.effect->SetRawValue("c", &rcol, 0, 16));
	CHECK(COMHandles.effect->CommitChanges());

	CHECK(COMHandles.device->SetTexture(0, NULL));
	CHECK(COMHandles.device->SetFVF(D3DFVF_XYZ));
	CHECK(COMHandles.device->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, quad, 3*sizeof(float)));

	p_particles++;

	int color0 = (int)(rcol*60.0f+0.5f);
	int color1 = (int)(gcol*60.0f+0.5f);
	if (color0 != lastcolor0 || color1 != lastcolor1)
	{
		p_colortables++;
		lastcolor0 = color0;
		lastcolor1 = color1;
	}

	float a = m->m[0][0], b = m->m[1][0], c = m->m[0][1], d = m->m[1][1];
	float x0 = m->m[3][0]+AMIGA_WIDTH*0.5f, y0 = m->m[3][1]+AMIGA_HEIGHT*0.5f;

	float rdet = 1.0f/(a*d-b*c);
	float e = rdet*d, f = -rdet*b, g = -rdet*c, h = rdet*a;
	float A = e*e + g*g, B = f*f + h*h, C = e*f + g*h;
	float xrad = 1.0f/sqrtf(A), yrad = 1.0f/sqrtf(B-C*C/A);
	float ymin = y0 - yrad, ymax = y0 + yrad;
	if (ymin < 0.0f) ymin = 0.0f;
	if (ymax > (float)AMIGA_HEIGHT) ymax = (float)AMIGA_HEIGHT;

	int ysize = (int)(ymax-ymin)+1;
	int xsize = (int)(xrad*2.0f)+1;
	if (ysize > 0)
	{
		p_lines += ysize;
		p_pixels += ysize * xsize;
	}
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
