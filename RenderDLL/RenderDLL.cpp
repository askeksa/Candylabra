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
#include "render.h"
#include "main.h"

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

extern "C" {
	D3DXMATRIXA16 proj;

	float constantPool[256];
	char parambuf[1000];
	float paramvals[100];
	int nparams;

	bool inited = false;
	bool effect_valid = false;

	void initparams()
	{
		int i = 0;
		int n = 0;

		paramvals[1] = 0.0f;
		paramvals[2] = 1.0f;
		paramvals[3] = 0.0f;
		i += sprintf(&parambuf[i], "time/seed/fov/pass/");
		n += 4;

		D3DXEFFECT_DESC desc;
		COMHandles.effect->GetDesc(&desc);
		for (unsigned int p = 0 ; p < desc.Parameters ; p++)
		{
			D3DXPARAMETER_DESC pdesc;
			D3DXHANDLE param = COMHandles.effect->GetParameter(NULL, p);
			COMHandles.effect->GetParameterDesc(param, &pdesc);
			if (pdesc.Elements >= 1) continue;
			switch(pdesc.Class)
			{
			case D3DXPC_SCALAR:
				COMHandles.effect->GetValue(param, &paramvals[n], D3DX_DEFAULT);
				i += sprintf(&parambuf[i], "%s/", pdesc.Name);
				n++;
				break;
				/*
			case D3DXPC_VECTOR:
				COMHandles.effect->GetValue(param, &paramvals[n], D3DX_DEFAULT);
				for (unsigned int c = 1 ; c <= pdesc.Columns ; c++)
				{
					i += sprintf(&parambuf[i], "%s%d/", pdesc.Name, c);
					n++;
				}
				break;
				*/
			default:
				break;
			}
		}
		nparams = n;
	}

	void uploadparams()
	{
		int n = 4;
		D3DXEFFECT_DESC desc;
		COMHandles.effect->GetDesc(&desc);
		for (unsigned int p = 0 ; p < desc.Parameters ; p++)
		{
			D3DXPARAMETER_DESC pdesc;
			D3DXHANDLE param = COMHandles.effect->GetParameter(NULL, p);
			COMHandles.effect->GetParameterDesc(param, &pdesc);
			if (pdesc.Elements >= 1) continue;
			switch(pdesc.Class)
			{
			case D3DXPC_SCALAR:
				COMHandles.effect->SetRawValue(param, &constantPool[n], 0, sizeof(float));
				n++;
				break;
				/*
			case D3DXPC_VECTOR:
				COMHandles.effect->SetRawValue(param, &constantPool[n], 0, pdesc.Columns * sizeof(float));
				n += pdesc.Columns;
				break;
				*/
			default:
				break;
			}
		}
	}

	int noteSamples;
	int numChannels;
	int numRows;
	float channelDeltas[256*128];
	int channelCounts[256*128];
	unsigned char* notes;
	MemoryFile* mf;

	bool __stdcall init3() {
		if (D3DXCreateEffectFromFile(COMHandles.device, "shaders.fx", NULL, NULL, 0, NULL, &COMHandles.effect, ERRORS) != D3D_OK)
		{
			MessageBox(0, (char *)errors->GetBufferPointer(), 0, 0);
			effect_valid = false;
			return false;
		}
		effect_valid = true;

		mf = new MemoryFile("sync");
		int* ptr = (int*)mf->getPtr();
		noteSamples = *ptr++;
		numChannels = *ptr++;
		numRows = *ptr++;
		notes = (unsigned char*)ptr;

		initparams();
		return true;
	}

	void __stdcall init2() {
		CHECK(D3DXCreateMatrixStack(0, &COMHandles.matrix_stack));

		CHECK(COMHandles.device->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO, &COMHandles.backbuffer));
		CHECK(COMHandles.device->GetDepthStencilSurface(&COMHandles.depthbuffer));

		init3();
		render_init();
	}

	RECT scissorRect;
	D3DVIEWPORT9 viewport;
	D3DVIEWPORT9 display_viewport;
	int width, height;
	char *program;

	void pass(int effectpass, int treepass) {
		COMHandles.effect->BeginPass(effectpass);
		constantPool[3] = (float)treepass;
		interpret(program);
		COMHandles.effect->EndPass();
	}

	void setfov()
	{
		width = scissorRect.right - scissorRect.left;
		height = scissorRect.bottom - scissorRect.top;
		{//projection matrix
			float CAMERA_NEAR_Z = 0.125f;
			float CAMERA_FAR_Z = 1024.0f;
			float aspect = width / (float)height;
			D3DXMatrixPerspectiveFovLH(&proj, constantPool[2], aspect, CAMERA_NEAR_Z, CAMERA_FAR_Z);
		}
	}

	RENDERDLL_API int __stdcall getparams(char *buf)
	{
		strcpy(buf, parambuf);
		return nparams;
	}

	RENDERDLL_API int __stdcall init(LPDIRECT3DDEVICE9 device)
	{
		if(!inited) {
			memset(&COMHandles, 0, sizeof(COMHandles));
			COMHandles.device = device;
			init2();
			inited = true;
		}
		return 0;
	}

	RENDERDLL_API int __stdcall reinit()
	{
		if (effect_valid)
		{
			delete mf;
			COMHandles.effect->Release();
		}

		if (!init3())
		{
			return 0;
		}

		render_reinit();
		return 1;
	}

	void updatemusic()
	{
		int totalSamples = numRows*noteSamples*16;
		int beatSamples = noteSamples * 4;
		int sample = ((int) (constantPool[0] * beatSamples)) % totalSamples;
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
	}

	void view_enter()
	{
		CHECK(COMHandles.device->GetScissorRect(&scissorRect));
		D3DSURFACE_DESC backbufferdesc;
		CHECK(COMHandles.backbuffer->GetDesc(&backbufferdesc));
		CHECK(COMHandles.device->GetViewport(&viewport));

		D3DVIEWPORT9 newport = {scissorRect.left, scissorRect.top,
			scissorRect.right-scissorRect.left, scissorRect.bottom-scissorRect.top,
			0, 1
		};
		display_viewport = newport;
	}

	void view_display()
	{
		CHECK(COMHandles.device->SetRenderTarget(0, COMHandles.backbuffer));
		CHECK(COMHandles.device->SetDepthStencilSurface(COMHandles.depthbuffer));
		CHECK(COMHandles.device->SetScissorRect(&scissorRect));
		int border_offset = (int)((width - height * 4.0f / 3.0f) / 2);
		if(border_offset > 0) {
			RECT rect = {
				scissorRect.left+border_offset, scissorRect.top, scissorRect.right-border_offset, scissorRect.bottom
			};
			CHECK(COMHandles.device->SetScissorRect(&rect));
		};
		CHECK(COMHandles.device->SetViewport(&display_viewport));
	}

	void view_restore()
	{
		CHECK(COMHandles.device->SetRenderTarget(0, COMHandles.backbuffer));
		CHECK(COMHandles.device->SetDepthStencilSurface(COMHandles.depthbuffer));
		CHECK(COMHandles.device->SetScissorRect(&scissorRect));
		CHECK(COMHandles.device->SetViewport(&viewport));
	}

	RENDERDLL_API int __stdcall renderobj(char* prog, float* constants) {
		if (!inited || !effect_valid) return 0;

		program = prog;
		memcpy(constantPool, constants, sizeof(float)*256);
		memcpy(&constantPool[1], &paramvals[1], sizeof(float)*(nparams-1));
		
		updatemusic();
		view_enter();

		render_main();

		//restore state
		COMHandles.device->SetVertexShader(NULL);
		COMHandles.device->SetPixelShader(NULL);
		COMHandles.device->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE);
		CHECK(COMHandles.device->SetRenderTarget(0, COMHandles.backbuffer));
		CHECK(COMHandles.device->SetDepthStencilSurface(COMHandles.depthbuffer));
		COMHandles.device->SetTexture(0, 0);

		view_restore();

		int border_offset = (int)((width - height * 4.0f / 3.0f) / 2);
		if(border_offset > 0) {
			D3DRECT hborders[2] = {
				{border_offset, 0, border_offset+1, height},
				{width - border_offset-1, 0, width - border_offset, height},
			};
			COMHandles.device->Clear(2, hborders, D3DCLEAR_TARGET, 0xFF0000, 1.0f, 0);
		}

		return 0;
	}
};