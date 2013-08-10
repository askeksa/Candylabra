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
#include "main.h"
#include "engine_atrium.h"
#include "engine_textobj.h"
#include "engine_haumea.h"
#include "engine_eris.h"
#include "engine_ikadalawampu.h"
#include "engine_points.h"
#include "engine_dx11particles.h"

using namespace std;

int current_engine_id = -1;
Engine *active_engine;

int render_return;

char effectfile[101];
char syncfile[101];
char datafile[101];

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
		i += sprintf(&parambuf[i], active_engine->predefined_variables());
		for (int si = 0 ; si < i ; si++) {
			if (parambuf[si] == '/') {
				n += 1;
			}
		}

		if (active_engine->use_effect())
		{
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
	int timerFac,channelFac;
	int channelDataLength;
	float channelDeltas[5000000];
	int channelCounts[5000000];
	unsigned char* notes;

	bool create_effect() {
		COMHandles.effect = NULL;
		if (D3DXCreateEffectFromFile(COMHandles.device, effectfile, NULL, NULL, 0, NULL, &COMHandles.effect, ERRORS) != D3D_OK)
		{
			if (errors == NULL)
			{
				char msg[100];
				sprintf(msg, "Could not create effect from file %s", effectfile);
				MessageBox(0, msg, 0, 0);
			} else {
				MessageBox(0, (char *)errors->GetBufferPointer(), 0, 0);
			}
			effect_valid = false;
			return false;
		}
		effect_valid = true;
		return true;
	}

	void destroy_effect() {
		if (COMHandles.effect)
		{
			COMHandles.effect->Release();
			COMHandles.effect = NULL;
		}
	}

	void __stdcall init_sync() {
/*
		mf = new MemoryFile("sync");
		int* ptr = (int*)mf->getPtr();
		noteSamples = *ptr++;
		numChannels = *ptr++;
		numRows = *ptr++;
		notes = (unsigned char*)ptr;
*/
		MemoryFile* mf = new MemoryFile(syncfile);
		if (mf->ok()) {
			int* ptr = (int*)mf->getPtr();
			timerFac = *ptr++;
			channelFac = *ptr++;
			channelDataLength = *ptr++;
			if (channelDataLength <= sizeof(channelDeltas))
			{
				memcpy(channelDeltas, ptr, channelDataLength);
			} else {
				MessageBox(0, "Sync data buffer overflow", 0, 0);
			}
		}
		delete mf;
	}

	void __stdcall init2() {
		CHECK(D3DXCreateMatrixStack(0, &COMHandles.matrix_stack));

		CHECK(COMHandles.device->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO, &COMHandles.backbuffer));
		CHECK(COMHandles.device->GetDepthStencilSurface(&COMHandles.depthbuffer));

		init_sync();
		if (active_engine->use_effect()) {
			create_effect();
		}
		active_engine->init();
		initparams();
	}

	RECT scissorRect;
	D3DVIEWPORT9 viewport;
	D3DVIEWPORT9 display_viewport;
	int width, height;
	int canvas_width, canvas_height;
	char *program;

	void tree_pass(int treepass) {
		constantPool[3] = (float)treepass;
		COMHandles.matrix_stack->LoadIdentity();
		treecode();
		//interpret(program);
	}

	void pass(int effectpass, int treepass) {
		COMHandles.effect->BeginPass(effectpass);
		tree_pass(treepass);
		COMHandles.effect->EndPass();
	}

	void setfov()
	{
		float CAMERA_NEAR_Z = 0.125f;
		float CAMERA_FAR_Z = 1024.0f;
		float aspect = active_engine->getaspect();
		D3DXMatrixPerspectiveFovLH(&proj, constantPool[2], aspect, CAMERA_NEAR_Z, CAMERA_FAR_Z);
	}

static const char enginenames[] = "Atrium|TextObject|Haumea|Eris|Ikadalawampu|Points|DX11P|";

	RENDERDLL_API int __stdcall getengines(char *buf)
	{
		strcpy(buf, enginenames);
		return 7;
	}

	void init_engine(int engine_id)
	{
		switch (engine_id)
		{
		case 0:
			active_engine = new AtriumEngine();
			break;
		case 1:
			active_engine = new TextObjectEngine();
			break;
		case 2:
			active_engine = new HaumeaEngine();
			break;
		case 3:
			active_engine = new ErisEngine();
			break;
		case 4:
			active_engine = new IkadalawampuEngine();
			break;
		case 5:
			active_engine = new PointsEngine();
			break;
		case 6:
			active_engine = new DX11ParticlesEngine();
			break;
		}
		current_engine_id = engine_id;
	}

	RENDERDLL_API int __stdcall getparams(char *buf)
	{
		strcpy(buf, parambuf);
		return nparams;
	}

	RENDERDLL_API int __stdcall init(LPDIRECT3DDEVICE9 device, int engine_id, char *effect, char *sync, char *data)
	{
		if(!inited) {
			memset(&COMHandles, 0, sizeof(COMHandles));
			COMHandles.device = device;
			strncpy(effectfile, effect, 100);
			strncpy(syncfile, sync, 100);
			strncpy(datafile, data, 100);
			init_engine(engine_id);
			init2();
			inited = true;
		}
		return 0;
	}

	RENDERDLL_API int __stdcall reinit(int engine_id, char *effect, char *sync, char *data)
	{
		if (!inited) return 0;

		strncpy(effectfile, effect, 100);
		strncpy(syncfile, sync, 100);
		strncpy(datafile, data, 100);
		init_sync();

		if (active_engine->use_effect())
		{
			destroy_effect();
		}

		if (engine_id != current_engine_id)
		{
			active_engine->deinit();
			delete active_engine;
			init_engine(engine_id);
			if (active_engine->use_effect() && !create_effect())
			{
				return 0;
			}
			active_engine->init();
		} else {
			if (active_engine->use_effect() && !create_effect())
			{
				return 0;
			}
			active_engine->reinit();
		}
		initparams();

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
		width = scissorRect.right - scissorRect.left;
		height = scissorRect.bottom - scissorRect.top;

		//printf("(%d,%d)\n", width, height);

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
		float aspect = active_engine->getaspect();
		CHECK(COMHandles.device->SetRenderTarget(0, COMHandles.backbuffer));
		CHECK(COMHandles.device->SetDepthStencilSurface(COMHandles.depthbuffer));
		CHECK(COMHandles.device->SetScissorRect(&scissorRect));
		int border_offset = (int)((width - height * aspect) / 2);
		RECT rect = scissorRect;
		if(border_offset > 0) {
			rect.left += border_offset;
			rect.right -= border_offset;
			CHECK(COMHandles.device->SetScissorRect(&rect));
		} else {
			border_offset = (int)((height - width / aspect) / 2);
			rect.top += border_offset;
			rect.bottom -= border_offset;
			CHECK(COMHandles.device->SetScissorRect(&rect));
		}
		D3DVIEWPORT9 port = {rect.left, rect.top, rect.right-rect.left, rect.bottom-rect.top,
			0, 1
		};
		CHECK(COMHandles.device->SetViewport(&port));

		canvas_width = rect.right-rect.left;
		canvas_height = rect.bottom-rect.top;

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

		render_return = 0;

		program = prog;
		compileTree(prog);
		memcpy(constantPool, constants, sizeof(float)*256);
		memcpy(&constantPool[1], &paramvals[1], sizeof(float)*(nparams-1));
		
		//updatemusic();
		view_enter();

		active_engine->render();

		//restore state
		COMHandles.device->SetVertexShader(NULL);
		COMHandles.device->SetPixelShader(NULL);
		COMHandles.device->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE);
		CHECK(COMHandles.device->SetRenderTarget(0, COMHandles.backbuffer));
		CHECK(COMHandles.device->SetDepthStencilSurface(COMHandles.depthbuffer));
		COMHandles.device->SetTexture(0, 0);

		view_restore();

		float aspect = active_engine->getaspect();
		int border_offset = (int)((width - height * aspect) / 2);
		if(border_offset > 0) {
			D3DRECT hborders[2] = {
				{border_offset, 0, border_offset+1, height},
				{width - border_offset-1, 0, width - border_offset, height},
			};
			COMHandles.device->Clear(2, hborders, D3DCLEAR_TARGET, 0xFF0000, 1.0f, 0);
		}

		return render_return;
	}


	void __stdcall drawprimitive(float r, float g, float b, float a, int index)
	{
		active_engine->drawprimitive(r,g,b,a,index);
	}

	void __stdcall placelight(float r, float g, float b, float a, int index)
	{
		active_engine->placelight(r,g,b,a,index);
	}

	void __stdcall placecamera()
	{
		active_engine->placecamera();
	}

	float __stdcall frandom()
	{
		return active_engine->random();
	}
};
