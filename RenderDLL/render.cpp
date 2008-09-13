
#include "main.h"
#include "comcall.h"
#include "Marching.h"
#include <assert.h>

bool maketexture(IDirect3DVolumeTexture9 **texp, int size, char *fun)
{
	HRESULT compile_error = COMHandles.effectcompiler->CompileShader(fun, "tx_1_0", D3DXSHADER_OPTIMIZATION_LEVEL3, &COMHandles.tshaderbuffer, ERRORS, NULL);
	if (compile_error != D3D_OK)
	{
		if (ERRORS != NULL && *((ID3DXBuffer **)ERRORS) != NULL)
		{
			checkcompile(fun, compile_error);
		}
		return false;
	}
	CHECK(D3DXCreateTextureShader((const DWORD *)COMHandles.tshaderbuffer->GetBufferPointer(), &COMHandles.tshader));
	CHECK(COMHandles.device->CreateVolumeTexture(size,size,size,1, 0, D3DFMT_L8, D3DPOOL_MANAGED, texp, 0));
	CHECK(D3DXFillVolumeTextureTX(*texp, COMHandles.tshader));
	return true;
}

float marching_vertices[30000000];

void makemesh(IDirect3DVolumeTexture9 **texp, ID3DXMesh **meshp, char *fun)
{
	if (!maketexture(texp, TEX_SIZE, fun)) return;

	D3DLOCKED_BOX box;
	CHECK((*texp)->LockBox(0, &box, NULL, D3DLOCK_READONLY | D3DLOCK_NOSYSLOCK));
	assert(box.RowPitch == TEX_SIZE);
	assert(box.SlicePitch == TEX_SIZE * TEX_SIZE);
	int nv = marching_cubes((celltype *)box.pBits, marching_vertices);
	CHECK((*texp)->UnlockBox(0));
	//printf("Generated %d vertices\n", nv);

	CHECK(D3DXCreateMeshFVF(nv/3, nv, D3DXMESH_32BIT | D3DXMESH_SYSTEMMEM, D3DFVF_XYZ, COMHandles.device, meshp));
	float *vbuffer;
	CHECK((*meshp)->LockVertexBuffer(0, (void **)&vbuffer));
	memcpy(vbuffer, marching_vertices, nv*3*sizeof(float));
	CHECK((*meshp)->UnlockVertexBuffer());
	DWORD *ibuffer;
	CHECK((*meshp)->LockIndexBuffer(0, (void **)&ibuffer));
	for (int i = 0 ; i < nv ; i++)
	{
		ibuffer[i] = i;
	}
	CHECK((*meshp)->UnlockIndexBuffer());

	CHECK(D3DXWeldVertices((*meshp), 0, NULL, NULL, (DWORD *)marching_vertices, NULL, NULL));
	//printf("Welded to %d vertices\n", (*meshp)->GetNumVertices());

	CHECK(D3DXSimplifyMesh((*meshp), (DWORD *)marching_vertices, NULL, NULL, 100000, D3DXMESHSIMP_VERTEX, meshp));
	//printf("Simplified to %d vertices\n", (*meshp)->GetNumVertices());

	CHECK((*meshp)->GenerateAdjacency(0.0f, (DWORD *)marching_vertices));
	CHECK((*meshp)->Optimize(D3DXMESHOPT_COMPACT | D3DXMESHOPT_VERTEXCACHE | D3DXMESH_MANAGED, (DWORD *)marching_vertices, NULL, NULL, NULL, meshp));
	//printf("Optimized to %d vertices\n", (*meshp)->GetNumVertices());

	//char buff[512];
	//sprintf(buff, "Created mesh %d with %d vertices\n", (meshp-&COMHandles.meshes[0]), (*meshp)->GetNumVertices());
	//MessageBox(0, buff, 0, 0);

}

static void init_effect_and_stuff()
{
	CHECKC(D3DXCreateEffectCompilerFromFile("shaders.fx", NULL, NULL, D3DXSHADER_OPTIMIZATION_LEVEL3, &COMHandles.effectcompiler, ERRORS));

	maketexture(&COMHandles.randomtex, 32, "r");

	char t[4] = "dt0";
	for (int i = 0 ; i < N_OBJECTS ; i++)
	{
		makemesh(&COMHandles.textures[i], &COMHandles.meshes[i], &t[1]);
		maketexture(&COMHandles.dtextures[i], TEX_SIZE, &t[0]);
		t[2]++;
	}
}

void render_init()
{
	for (int i = 0 ; i < N_LIGHTS ; i++)
	{
		CHECK(COMHandles.device->CreateCubeTexture(CUBESIZE, 1, D3DUSAGE_RENDERTARGET, D3DFMT_R32F, D3DPOOL_DEFAULT, &COMHandles.cubetex[i], 0));
	}
	CHECK(COMHandles.device->CreateDepthStencilSurface(CUBESIZE, CUBESIZE, D3DFMT_D16, D3DMULTISAMPLE_NONE, 0, TRUE, &COMHandles.cubedepth, NULL));

	init_effect_and_stuff();
}

void render_reinit()
{
	COMHandles.effectcompiler->Release();
	COMHandles.randomtex->Release();
	for (int i = 0 ; i < N_OBJECTS ; i++)
	{
		if (COMHandles.meshes[i]) COMHandles.meshes[i]->Release();
		if (COMHandles.textures[i]) COMHandles.textures[i]->Release();
		if (COMHandles.dtextures[i]) COMHandles.dtextures[i]->Release();
	}

	init_effect_and_stuff();
}

D3DXMATRIX p[6] = {
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

void render_main()
{
	CHECK(COMHandles.effect->Begin(0, 0));

	CHECK(COMHandles.effect->SetTexture("_randomtex", COMHandles.randomtex));
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
			CHECK(COMHandles.effect->SetMatrixTranspose("facep", &p[f]));
			pass(i,0);
		}
	}

	view_display();
	CHECK(COMHandles.device->Clear(0, NULL, D3DCLEAR_ZBUFFER | D3DCLEAR_TARGET, 0, 1.0f, 0));
	CHECK(COMHandles.effect->SetMatrixTranspose("vp", &proj));
	pass(3,1);
	CHECK(COMHandles.effect->SetMatrixTranspose("vp", &proj));
	pass(2,1);

	CHECK(COMHandles.effect->End());
}

extern "C" {

	void setposition(char *name, int index)
	{
		D3DXMATRIX *trans = COMHandles.matrix_stack->GetTop();
		float pos[3] = { trans->_41, trans->_42, trans->_43 };
		CHECK(COMHandles.effect->SetRawValue(name, pos, index*16, 12));
	}

	void __stdcall drawprimitive(float r, float g, float b, float a, int index)
	{
		uploadparams();

		CHECK(COMHandles.effect->SetMatrixTranspose("m", COMHandles.matrix_stack->GetTop()));
		CHECK(COMHandles.effect->SetRawValue("color", &r, 0, 16));

		CHECK(COMHandles.effect->SetTexture("_tex", COMHandles.textures[index]));
		CHECK(COMHandles.effect->SetTexture("_detailtex", COMHandles.dtextures[index]));
		CHECK(COMHandles.effect->CommitChanges());

		if (COMHandles.meshes[index] != NULL) CHECK(COMHandles.meshes[index]->DrawSubset(0));
	}

	void __stdcall placelight(float r, float g, float b, float a, int index)
	{
		setposition("lightpos", index);

		CHECK(COMHandles.effect->SetRawValue("lightcol", &r, index*16, 16));
		CHECK(COMHandles.effect->CommitChanges());
	}

	void __stdcall placecamera()
	{
		setposition("campos", 0);

		setfov();

		COMHandles.matrix_stack->Push();
		D3DXMatrixInverse(COMHandles.matrix_stack->GetTop(), NULL, COMHandles.matrix_stack->GetTop());
		COMHandles.matrix_stack->MultMatrix(&proj);
		CHECK(COMHandles.effect->SetMatrixTranspose("vp", COMHandles.matrix_stack->GetTop()));
		COMHandles.matrix_stack->Pop();
	}

};