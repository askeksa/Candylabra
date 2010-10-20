
#include "engine_points.h"
#include "main.h"
#include "comcall.h"
#include "MemoryFile.h"
#include <assert.h>

#define BUCKET_EXPONENT_MIN 0x7f // Near plane at 1.0
#define BUCKET_EXPONENT_MAX 0x88 // Far plane at 512.0
#define BUCKET_MANTISSA_BITS 10
#define NUM_BUCKETS ((BUCKET_EXPONENT_MAX-BUCKET_EXPONENT_MIN) << BUCKET_MANTISSA_BITS)
#define POINTS_PER_BUCKET 101

extern "C" {
	extern int canvas_width, canvas_height;
	extern float constantPool[256];
};

float PointsEngine::getaspect()
{
	return 16.0f / 9.0f;
}

void PointsEngine::prepare_render_surfaces()
{
	int width = canvas_width;
	int	height = canvas_height;
	if (width <= 0 || height <= 0)
	{
		width = 1;
		height = 1;
	}
	if (render_width != width || render_height != height)
	{
		if (COMHandles.renderbuffer) COMHandles.renderbuffer->Release();
		if (COMHandles.renderbuffertex) COMHandles.renderbuffertex->Release();
		if (COMHandles.renderdepthbuffer) COMHandles.renderdepthbuffer->Release();
		if (COMHandles.postbuffer1) COMHandles.postbuffer1->Release();
		if (COMHandles.postbuffer1tex) COMHandles.postbuffer1tex->Release();
		if (COMHandles.postbuffer2) COMHandles.postbuffer2->Release();
		if (COMHandles.postbuffer2tex) COMHandles.postbuffer2tex->Release();
		CHECK(COMHandles.device->CreateTexture(width, height, 1, D3DUSAGE_RENDERTARGET, D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, &COMHandles.renderbuffertex, NULL));
		CHECK(COMHandles.device->CreateTexture(width, height, 1, D3DUSAGE_RENDERTARGET, D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, &COMHandles.postbuffer1tex, NULL));
		CHECK(COMHandles.device->CreateTexture(width, height, 1, D3DUSAGE_RENDERTARGET, D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, &COMHandles.postbuffer2tex, NULL));
		CHECK(COMHandles.device->CreateDepthStencilSurface(width, height, D3DFMT_D16, D3DMULTISAMPLE_NONE, 0, TRUE, &COMHandles.renderdepthbuffer, NULL));
		render_width = width;
		render_height = height;
		last_fov = 0.0f;

		CHECK(COMHandles.renderbuffertex->GetSurfaceLevel(0, &COMHandles.renderbuffer));
		CHECK(COMHandles.postbuffer1tex->GetSurfaceLevel(0, &COMHandles.postbuffer1));
		CHECK(COMHandles.postbuffer2tex->GetSurfaceLevel(0, &COMHandles.postbuffer2));
	}

	CHECK(COMHandles.device->SetRenderTarget(0, COMHandles.renderbuffer));
	CHECK(COMHandles.device->SetDepthStencilSurface(COMHandles.renderdepthbuffer));
}


void PointsEngine::init()
{
	CHECK(COMHandles.device->CreateVertexBuffer(
		MAX_POINTS*sizeof(struct PointVertex),
		D3DUSAGE_DYNAMIC | D3DUSAGE_POINTS | D3DUSAGE_WRITEONLY,
		POINTS_FVF,
		D3DPOOL_DEFAULT,
		&COMHandles.vbuffer,
		NULL));

	point_bucket_sizes = new unsigned int[NUM_BUCKETS];
	point_buckets = new struct PointVertex[NUM_BUCKETS*POINTS_PER_BUCKET];
}

void PointsEngine::reinit()
{
	render_width = 0;
	render_height = 0;
	last_fov = 0.0f;
}

void PointsEngine::deinit()
{
	COMHandles.vbuffer->Release();
	delete point_bucket_sizes;
	point_bucket_sizes = NULL;
	delete point_buckets;
	point_buckets = NULL;
}

static float fullscreenquad[] = {
	-1.0,  1.0, 0.0, 0.0, 0.0,
	 1.0,  1.0, 0.0, 1.0, 0.0,
	-1.0, -1.0, 0.0, 0.0, 1.0,
	 1.0, -1.0, 0.0, 1.0, 1.0
};

void PointsEngine::blit_to_screen(int pass, IDirect3DTexture9 *from)
{
	CHECK(COMHandles.effect->BeginPass(pass));
	//COMHandles.device->SetRenderState(D3DRS_CULLMODE, D3DCULL_NONE);
	CHECK(COMHandles.device->SetTexture(0, from));
	CHECK(COMHandles.device->SetFVF(D3DFVF_XYZ|D3DFVF_TEX1));
	CHECK(COMHandles.device->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, fullscreenquad, 5*sizeof(float)));
	CHECK(COMHandles.effect->EndPass());
}

int vertex_compare(const void *e1, const void *e2)
{
	struct PointVertex *p1 = (struct PointVertex *)e1;
	struct PointVertex *p2 = (struct PointVertex *)e2;
	return *(int *)&p2->z - *(int *)&p1->z;
}

void PointsEngine::render()
{
	constantPool[2] = 1.0f;

	D3DXTECHNIQUE_DESC tdesc;
	CHECK(COMHandles.effect->GetTechniqueDesc(COMHandles.effect->GetTechnique(0), &tdesc));

	CHECK(COMHandles.effect->Begin(0, 0));

	prepare_render_surfaces();
	CHECK(COMHandles.device->Clear(0, NULL, D3DCLEAR_ZBUFFER | D3DCLEAR_TARGET, 0x00000000, 1.0f, 0));
	CHECK(COMHandles.device->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE));
	for (unsigned p = 0 ; p < tdesc.Passes-3 ; p++)
	{
		CHECK(COMHandles.effect->BeginPass(p));
	
		//CHECK(COMHandles.matrix_stack->LoadMatrix(&proj));
		memset(point_bucket_sizes, 0, NUM_BUCKETS*sizeof(unsigned int));
		tree_pass(p);

		//qsort(mapped_buffer, n_points, sizeof(struct PointVertex), vertex_compare);

		unsigned int n_points = 0;
		CHECK(COMHandles.vbuffer->Lock(0, 0, (void **)&mapped_buffer, D3DLOCK_DISCARD));
		for (unsigned int bucket = 0 ; bucket < NUM_BUCKETS ; bucket++)
		{
			unsigned int bucket_size = point_bucket_sizes[bucket];
			struct PointVertex *bucketp = &point_buckets[bucket*POINTS_PER_BUCKET];
			memcpy(&mapped_buffer[n_points], bucketp, bucket_size*sizeof(struct PointVertex));
			n_points += bucket_size;
		}
		CHECK(COMHandles.vbuffer->Unlock());

		uploadparams();
		setfov();

		CHECK(COMHandles.effect->SetMatrixTranspose("o", &proj));
		CHECK(COMHandles.effect->SetFloat("w", (float)canvas_width));
		CHECK(COMHandles.effect->SetFloat("h", (float)canvas_height));
		CHECK(COMHandles.effect->CommitChanges());

		CHECK(COMHandles.device->SetFVF(POINTS_FVF));
		CHECK(COMHandles.device->SetStreamSource(0, COMHandles.vbuffer, 0, sizeof(struct PointVertex)));
		CHECK(COMHandles.device->DrawPrimitive(D3DPT_POINTLIST, 0, n_points));

		CHECK(COMHandles.effect->EndPass( ));
	}

	CHECK(COMHandles.device->SetRenderTarget(0, COMHandles.postbuffer1));
	blit_to_screen(tdesc.Passes-3, COMHandles.renderbuffertex);
	view_display();
	blit_to_screen(tdesc.Passes-2, COMHandles.renderbuffertex);
	blit_to_screen(tdesc.Passes-1, COMHandles.postbuffer1tex);

	CHECK(COMHandles.effect->End());
}

void PointsEngine::drawprimitive(float r, float g, float b, float a, int index)
{
	D3DXMATRIX *trans = COMHandles.matrix_stack->GetTop();
	unsigned int z_int = *(unsigned int *)&trans->_43;
	unsigned int bucket = ((BUCKET_EXPONENT_MAX << 23) - z_int) >> (23 - BUCKET_MANTISSA_BITS);
	if (bucket < NUM_BUCKETS)
	{
		unsigned int bucket_size = point_bucket_sizes[bucket];
		struct PointVertex *p = &point_buckets[bucket*POINTS_PER_BUCKET+bucket_size];
		p->x = trans->_41;
		p->y = trans->_42;
		p->z = trans->_43;
		p->size = sqrtf(trans->_11*trans->_11 + trans->_12*trans->_12 + trans->_13*trans->_13);
		p->r = r;
		p->g = g;
		p->b = b;
		p->a = a;
		point_bucket_sizes[bucket]++;
	}

}

void PointsEngine::placelight(float r, float g, float b, float a, int index)
{
}

void PointsEngine::placecamera()
{
}

float PointsEngine::random()
{
	return mentor_synth_random();
}
/*
char *PointsEngine::predefined_variables() {
	return "time/seed/size/pass/";
}
*/