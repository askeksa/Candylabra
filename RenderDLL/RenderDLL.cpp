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
		printf("%s returned %s\n", n, DXGetErrorString(r));
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
	void __stdcall syncinit() {
		mf = new MemoryFile("sync");
		int* ptr = (int*)mf->getPtr();
		noteSamples = *ptr++;
		numChannels = *ptr++;
		numRows = *ptr++;
		notes = (unsigned char*)ptr;
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

float constantPool[256];

RENDERDLL_API int __stdcall renderobj(LPDIRECT3DDEVICE9 device, char* program, float* constants) {
	if(!inited) {
		COMHandles.device = device;
		dllinit();
		inited = true;
	}
	
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
		channelDeltas[i] = (channelDeltas[i] + offset) / 44100.0f;
	}


	memcpy(constantPool, constants, sizeof(float)*256);
	interpret(program);

	COMHandles.device->SetFVF(MY_FVF);
	COMHandles.device->SetIndices(COMHandles.composite_index);
	COMHandles.device->SetStreamSource(0, COMHandles.composite_vertex, 0, sizeof(vertex));
	COMHandles.device->DrawIndexedPrimitive(D3DPT_TRIANGLELIST, 0, 0, num_vertices, 0, num_faces);

	return 0;
}
};