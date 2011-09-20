
#include "engine_points.h"
#include "main.h"
#include "comcall.h"
#include "MemoryFile.h"
#include <assert.h>

#define BUCKET_EXPONENT_MIN 0x7f // Near plane at 1.0
#define BUCKET_EXPONENT_MAX 0x88 // Far plane at 512.0
#define BUCKET_MANTISSA_BITS 10
#define NUM_BUCKETS ((BUCKET_EXPONENT_MAX-BUCKET_EXPONENT_MIN) << BUCKET_MANTISSA_BITS)
#define POINTS_PER_BUCKET 201

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
#if USE_INSTANCING
	CHECK(COMHandles.device->CreateVertexBuffer(
		MAX_POINTS*sizeof(struct PointVertex),
		D3DUSAGE_DYNAMIC | D3DUSAGE_WRITEONLY,
		0,
		D3DPOOL_DEFAULT,
		&COMHandles.vbuffer,
		NULL));

	static const struct CornerVertex ivbdata[4] = {
		0.5f,0.5f, 0.5f,-0.5f, -0.5f,0.5f, -0.5f,-0.5f
	};
	CHECK(COMHandles.device->CreateVertexBuffer(
		sizeof(ivbdata),
		D3DUSAGE_WRITEONLY,
		0,
		D3DPOOL_DEFAULT,
		&COMHandles.instancevbuffer,
		NULL));
	void *ivb = NULL;
	CHECK(COMHandles.instancevbuffer->Lock(0, 0, &ivb, D3DLOCK_DISCARD));
	memcpy(ivb, ivbdata, sizeof(ivbdata));
	CHECK(COMHandles.instancevbuffer->Unlock());

	static const D3DVERTEXELEMENT9 vertex_decl[] = {
		// Stream, Offset, Type, Method, Usage, UsageIndex
		{ 0, 0, D3DDECLTYPE_FLOAT2, D3DDECLMETHOD_DEFAULT, D3DDECLUSAGE_TEXCOORD, 2 },
		{ 1, 0, D3DDECLTYPE_FLOAT3, D3DDECLMETHOD_DEFAULT, D3DDECLUSAGE_POSITION, 0 },
		{ 1, 12, D3DDECLTYPE_FLOAT1, D3DDECLMETHOD_DEFAULT, D3DDECLUSAGE_TEXCOORD, 0 },
		{ 1, 16, D3DDECLTYPE_FLOAT4, D3DDECLMETHOD_DEFAULT, D3DDECLUSAGE_TEXCOORD, 1 },
		D3DDECL_END()
	};
	CHECK(COMHandles.device->CreateVertexDeclaration(vertex_decl, &COMHandles.vdecl));

	static const unsigned short indices[] = {
		0,1,2,3
	};
	CHECK(COMHandles.device->CreateIndexBuffer(sizeof(indices), D3DUSAGE_WRITEONLY, D3DFMT_INDEX16, D3DPOOL_DEFAULT, &COMHandles.indexbuffer, NULL));
	void *ib;
	CHECK(COMHandles.indexbuffer->Lock(0, 0, &ib, D3DLOCK_DISCARD));
	memcpy(ib, indices, sizeof(indices));
	CHECK(COMHandles.indexbuffer->Unlock());
#else
	CHECK(COMHandles.device->CreateVertexBuffer(
		MAX_POINTS*3*sizeof(struct PointTriVertex),
		D3DUSAGE_DYNAMIC | D3DUSAGE_WRITEONLY,
		POINT_TRI_FVF,
		D3DPOOL_DEFAULT,
		&COMHandles.vbuffer,
		NULL));
#endif

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
#if USE_INSTANCING
	COMHandles.instancevbuffer->Release();
	COMHandles.indexbuffer->Release();
#endif
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
#if USE_INSTANCING
			memcpy(&mapped_buffer[n_points], bucketp, bucket_size*sizeof(struct PointVertex));
			n_points += bucket_size;
#else
			for (unsigned int p = 0 ; p < bucket_size ; p++)
			{
				mapped_buffer[n_points*3+0].point = bucketp[p];
				mapped_buffer[n_points*3+0].ox = 0.875f;
				mapped_buffer[n_points*3+0].oy = -0.5f;
				mapped_buffer[n_points*3+1].point = bucketp[p];
				mapped_buffer[n_points*3+1].ox = -0.875f;
				mapped_buffer[n_points*3+1].oy = -0.5f;
				mapped_buffer[n_points*3+2].point = bucketp[p];
				mapped_buffer[n_points*3+2].ox = 0.0f;
				mapped_buffer[n_points*3+2].oy = 1.0f;
				n_points++;
			}
#endif
		}
		CHECK(COMHandles.vbuffer->Unlock());

		uploadparams();
		setfov();

		CHECK(COMHandles.effect->SetMatrixTranspose("o", &proj));
		CHECK(COMHandles.effect->SetFloat("w", (float)canvas_width));
		CHECK(COMHandles.effect->SetFloat("h", (float)canvas_height));
		CHECK(COMHandles.effect->CommitChanges());
#if USE_INSTANCING
		CHECK(COMHandles.device->SetVertexDeclaration(COMHandles.vdecl));
		CHECK(COMHandles.device->SetStreamSource(0, COMHandles.instancevbuffer, 0, sizeof(struct CornerVertex)));
		CHECK(COMHandles.device->SetStreamSourceFreq(0, D3DSTREAMSOURCE_INDEXEDDATA | n_points));
		CHECK(COMHandles.device->SetStreamSource(1, COMHandles.vbuffer, 0, sizeof(struct PointVertex)));
		CHECK(COMHandles.device->SetStreamSourceFreq(1, D3DSTREAMSOURCE_INSTANCEDATA | 1));
		CHECK(COMHandles.device->SetIndices(COMHandles.indexbuffer));
		CHECK(COMHandles.device->DrawIndexedPrimitive(D3DPT_TRIANGLESTRIP, 0, 0, 4, 0, 2));

		CHECK(COMHandles.device->SetVertexDeclaration(NULL));
		CHECK(COMHandles.device->SetStreamSourceFreq(0, 1));
		CHECK(COMHandles.device->SetStreamSourceFreq(1, 1));
#else
		CHECK(COMHandles.device->SetFVF(POINT_TRI_FVF));
		CHECK(COMHandles.device->SetStreamSource(0, COMHandles.vbuffer, 0, sizeof(struct PointTriVertex)));
		CHECK(COMHandles.device->DrawPrimitive(D3DPT_TRIANGLELIST, 0, n_points));
#endif
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
		p->size2 = trans->_11*trans->_11 + trans->_12*trans->_12 + trans->_13*trans->_13;
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