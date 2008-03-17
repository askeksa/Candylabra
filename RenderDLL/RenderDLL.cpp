// RenderDLL.cpp : Defines the entry point for the DLL application.
//

#include "stdafx.h"
#include "RenderDLL.h"
#include <d3dx9.h>
#include <dxerr.h>
#include <cstdio>
#include "MemoryFile.h"
#include "objgen.h"
#include "comcall.h"

using namespace std;

BOOL APIENTRY DllMain( HMODULE hModule,
                       DWORD  ul_reason_for_call,
                       LPVOID lpReserved
					 )
{
	switch (ul_reason_for_call)
	{
	case DLL_PROCESS_ATTACH:
	case DLL_THREAD_ATTACH:
	case DLL_THREAD_DETACH:
	case DLL_PROCESS_DETACH:
		break;
	}
    return TRUE;
}

#ifndef NDEBUG
void check(char *n, int r) {
	if (r != D3D_OK) {
		char buff[512];
		sprintf(buff, "%s returned %s\n", n, DXGetErrorString(r));
		MessageBox(0, buff, 0, 0);
		ExitProcess(1);
	}
}
#define CHECK(e) check(#e, e)
#else
#define CHECK(e) e
#endif

extern "C" {
	D3DXMATRIXA16 proj;
	void __stdcall dllinit();
	void __stdcall dlldraw();
	extern float constantPool[];

	void __stdcall loadMeshDataFromFile() {
	}

	int noteSamples;
	int numChannels;
	int numRows;
	float channelDeltas[256*128];
	int channelCounts[256*128];
	unsigned char* notes;
	MemoryFile* mf;
	void __stdcall init2() {
		mf = new MemoryFile("sync");
		int* ptr = (int*)mf->getPtr();
		noteSamples = *ptr++;
		numChannels = *ptr++;
		numRows = *ptr++;
		notes = (unsigned char*)ptr;


		LPD3DXBUFFER errors;
		if(D3DXCreateEffectFromFile(COMHandles.device, "shaders.fx", NULL, NULL, 0, NULL, &COMHandles.effect, &errors) != D3D_OK) {
			MessageBox(0, (char*)errors->GetBufferPointer(), 0, 0);
		}

		for(int i = 0; i < 2; i++) {
			CHECK(COMHandles.device->CreateTexture(TEXTURE_WIDTH, TEXTURE_HEIGHT, 1, 
				D3DUSAGE_RENDERTARGET, D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, &COMHandles.textures[i], NULL));
			CHECK(COMHandles.textures[i]->GetSurfaceLevel(0, &COMHandles.surfaces[i]));
		}
		
		COMHandles.device->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO, &COMHandles.backbuffer);
		COMHandles.device->SetSamplerState(0, D3DSAMP_ADDRESSU, D3DTADDRESS_CLAMP);
		COMHandles.device->SetSamplerState(0, D3DSAMP_ADDRESSV, D3DTADDRESS_CLAMP);
		COMHandles.device->SetSamplerState(0, D3DSAMP_MAGFILTER, D3DTEXF_LINEAR);
		COMHandles.device->SetSamplerState(0, D3DSAMP_MINFILTER, D3DTEXF_LINEAR);
	}
};

bool inited = false;

extern "C" {
	struct vertex {
		D3DXVECTOR3 pos;
		D3DXVECTOR3 normal;
		DWORD color;
	};

extern int num_vertices;
extern int num_faces;


float ppquad[] ={
	-1.0f,  1.0f, 0.0f, 
	1.0f,  1.0f, 0.0f, 
	-1.0f, -1.0f, 0.0f, 
	1.0f, -1.0f, 0.0f, 
};

float shaderConstants[4] = {};

RECT scissorRect;
D3DVIEWPORT9 viewport;
void pass(int pass, int src, int target, float w) {
	COMHandles.device->SetTexture(0, COMHandles.textures[src]);
	if(target != 2) {
		COMHandles.device->SetRenderTarget(0, COMHandles.surfaces[target]);
	}
	

	COMHandles.effect->BeginPass(pass);
	COMHandles.device->SetFVF(D3DFVF_XYZ);
	shaderConstants[0] = w;
	COMHandles.device->SetPixelShaderConstantF(0, shaderConstants, 1);
	COMHandles.device->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, ppquad, 3*sizeof(float));
	COMHandles.effect->EndPass();
}

float constantPool[256];

RENDERDLL_API int __stdcall renderobj(LPDIRECT3DDEVICE9 device, char* program, float* constants) {
	if(!inited) {
		COMHandles.device = device;
		init2();
		dllinit();
		inited = true;
	}

	//set state
	COMHandles.device->SetRenderState(D3DRS_ALPHATESTENABLE, false);

	COMHandles.device->GetScissorRect(&scissorRect);
	COMHandles.device->GetViewport(&viewport);
	
	int totalSamples = numRows*noteSamples*16;
	int beatSamples = noteSamples * 4;
	int sample = ((int) (constants[0] * beatSamples)) % totalSamples;
	int row = sample / noteSamples;
	int offset = sample % noteSamples;

	for(int i = 0; i < numChannels*256; i++) {
		channelDeltas[i] = 44100*10;
		channelCounts[i] = 0;
	}

	for(int i = 0; i <= row; i++) {
		for(int j = 0; j < numChannels*128; j++) {
			channelDeltas[j] += noteSamples;
		}
		for(int j = 0; j < numChannels; j++) {
			int n = notes[j*numRows*16+i] & 0x7F;
			if(n != 0 && n != 0x7F) {
				channelDeltas[j*128+n] = 0;
				channelCounts[j*128+n]++;
			}
		}
	}

	for(int i = 0; i < numChannels*128; i++) {
		channelDeltas[i] = (channelDeltas[i] + offset) / beatSamples;
	}

	constantPool[6] = 1.0f;

	memcpy(constantPool, constants, sizeof(float)*256);
	interpret(program);

	
	{//projection matrix
		float width = scissorRect.right - scissorRect.left;
		float height = scissorRect.bottom - scissorRect.top;
		
		float compsize = width;
		float centerx = scissorRect.left + width/2;
		float centery = scissorRect.top + height/2;
		float CAMERA_NEAR_Z = 0.125f;
		float CAMERA_FAR_Z = 1024.0f;
		float CAMERA_ZOOM = constantPool[6];

		float factor = CAMERA_NEAR_Z / CAMERA_ZOOM / compsize;
		float l = -centerx * factor;
		float r = (viewport.Width-centerx) * factor;
		float t = centery * factor;
		float b = (centery-viewport.Height) * factor;
		D3DXMatrixPerspectiveOffCenterLH(&proj, l, r, b, t, CAMERA_NEAR_Z, CAMERA_FAR_Z);
		COMHandles.device->SetTransform(D3DTS_PROJECTION, &proj);
	}
	
	//COMHandles.effect->Begin(0, 0);
	DWORD color = (((int)(constantPool[3] * 255))<<16) + (((int)(constantPool[4] * 255))<<8) + ((int)(constantPool[5] * 255));
	COMHandles.device->Clear(0, NULL, D3DCLEAR_ZBUFFER|D3DCLEAR_TARGET, color, 1.0f, 0);
	
	//COMHandles.effect->BeginPass(1);
	COMHandles.device->SetFVF(MY_FVF);
	COMHandles.device->SetIndices(COMHandles.composite_index);
	COMHandles.device->SetStreamSource(0, COMHandles.composite_vertex, 0, sizeof(vertex));
	//COMHandles.device->SetVertexShaderConstantF(0, (float*)&proj, 4);
	COMHandles.device->DrawIndexedPrimitive(D3DPT_TRIANGLELIST, 0, 0, num_vertices, 0, num_faces);
	//COMHandles.effect->EndPass();

	//COMHandles.device->SetVertexShader(NULL);
	//COMHandles.device->SetPixelShader(NULL);
	
	//CHECK(COMHandles.device->StretchRect(COMHandles.backbuffer, &scissorRect, COMHandles.surfaces[0], NULL, D3DTEXF_LINEAR));

	//CHECK(COMHandles.device->SetScissorRect(NULL));
	//COMHandles.device->SetViewport(NULL);

/*
	float w = 0.01f;
	pass(0, 0, 1, w);
	for(int i = 0; i < 4; i++) {
		pass(0, 1, 0, w);
		w *= 2.0f;
		pass(0, 0, 1, w);
	}
	


	D3DVIEWPORT9 newport = {scissorRect.left, scissorRect.top,
		scissorRect.right-scissorRect.left, scissorRect.bottom-scissorRect.top,
		0, 1
	};
	COMHandles.device->SetRenderTarget(0, COMHandles.surfaces[2]);
	COMHandles.device->SetScissorRect(&scissorRect);
	COMHandles.device->SetViewport(&newport);

	
	COMHandles.device->SetRenderState(D3DRS_ALPHABLENDENABLE, TRUE);
	COMHandles.device->SetRenderState(D3DRS_DESTBLEND, D3DBLEND_ONE);
	pass(0, 1, 2, w);
*/
	//COMHandles.effect->End();

	//restore state
	//COMHandles.device->SetVertexShader(NULL);
	//COMHandles.device->SetPixelShader(NULL);
	//COMHandles.device->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE);

	//COMHandles.device->SetScissorRect(&scissorRect);
	//COMHandles.device->SetViewport(&viewport);

	//COMHandles.device->SetTexture(0, 0);


	return 0;
}
};