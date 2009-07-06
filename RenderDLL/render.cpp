
#include "main.h"
#include "comcall.h"
#include "Marching.h"
#include "MemoryFile.h"
#include <assert.h>

static void maketexts(char *texts, int size)
{
	LPD3DXMESH mesh = NULL;
	HDC hdc = CreateCompatibleDC( NULL );
	HFONT hFont;
	HFONT hFontOld;

	int t = 0;

	bool readfont = true;
	bool firstfont = true;
	for (int i = 0 ; i < N_OBJECTS ; i++)
	{
		float fontex;
		if (readfont)
		{
			char fontname[100];
			int fontsize;
			int n = sscanf(&texts[t], "%s %d %f\n", &fontname, &fontsize, &fontex);
			if (n >= 3)
			{
				while (t < size && texts[t] >= ' ') t++;
				while (t < size && texts[t] < ' ') t++;

				if (!firstfont) SelectObject(hdc, hFontOld);
				firstfont = false;
				hFont = CreateFont(fontsize, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, 
					OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, DEFAULT_QUALITY, DEFAULT_PITCH | FF_DONTCARE, fontname);
				hFontOld = (HFONT)SelectObject(hdc, hFont); 
			}
			readfont = false;
		}

		int next_t = t;
		while (next_t < size && texts[next_t] >= ' ') next_t++;

		if (next_t < size)
		{
			bool empty = next_t == t+3 && texts[t] == '-' && texts[t+1] == '-' && texts[t+2] == '-';
			texts[next_t++] = 0;
			while (next_t < size && texts[next_t] < ' ') next_t++;
			if (!empty)
			{
				CHECK(D3DXCreateText(COMHandles.device, hdc, &texts[t], 0.001f, fontex, &COMHandles.meshes[i], NULL, NULL));
			} else {
				readfont = true;
				i--;
			}
			t = next_t;
		} else {
			COMHandles.meshes[i] = NULL;
		}
	}

	SelectObject(hdc, hFontOld);

	DeleteObject( hFont );
	DeleteDC( hdc );
}

static void init_effect_and_stuff()
{
	CHECKC(D3DXCreateEffectCompilerFromFile("shaders.fx", NULL, NULL, D3DXSHADER_OPTIMIZATION_LEVEL3, &COMHandles.effectcompiler, ERRORS));

	MemoryFile object_texts("texts.txt", false);
	if (object_texts.getSize() > 0)
	{
		maketexts((char *)object_texts.getPtr(), object_texts.getSize());
	}
}

void render_init()
{
	init_effect_and_stuff();
}

void render_reinit()
{
	COMHandles.effectcompiler->Release();
	for (int i = 0 ; i < N_OBJECTS ; i++)
	{
		if (COMHandles.meshes[i]) COMHandles.meshes[i]->Release();
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

	view_display();
	CHECK(COMHandles.device->Clear(0, NULL, D3DCLEAR_ZBUFFER | D3DCLEAR_TARGET, 0, 1.0f, 0));
	setfov();
	//CHECK(COMHandles.effect->SetMatrixTranspose("vm", &proj));
	CHECK(COMHandles.matrix_stack->LoadMatrix(&proj));
	pass(0,0);

	CHECK(COMHandles.effect->End());
}

extern "C" {
/*
	void setposition(char *name, int index)
	{
		D3DXMATRIX *trans = COMHandles.matrix_stack->GetTop();
		float pos[3] = { trans->_41, trans->_42, trans->_43 };
		CHECK(COMHandles.effect->SetRawValue(name, pos, index*16, 12));
	}
*/
	void __stdcall drawprimitive(float r, float g, float b, float a, int index)
	{
		uploadparams();

		CHECK(COMHandles.effect->SetMatrixTranspose("m", COMHandles.matrix_stack->GetTop()));
		CHECK(COMHandles.effect->SetRawValue("c", &r, 0, 16));
		CHECK(COMHandles.effect->CommitChanges());

		if (COMHandles.meshes[index] != NULL) CHECK(COMHandles.meshes[index]->DrawSubset(0));
	}

	void __stdcall placelight(float r, float g, float b, float a, int index)
	{
/*
		setposition("ld", index);

		CHECK(COMHandles.effect->SetRawValue("lc", &r, index*16, 16));
		CHECK(COMHandles.effect->CommitChanges());
*/
	}

	void __stdcall placecamera()
	{
/*
		setposition("d", 0);

		setfov();

		COMHandles.matrix_stack->Push();
		D3DXMatrixInverse(COMHandles.matrix_stack->GetTop(), NULL, COMHandles.matrix_stack->GetTop());
		COMHandles.matrix_stack->MultMatrix(&proj);
		CHECK(COMHandles.effect->SetMatrixTranspose("vm", COMHandles.matrix_stack->GetTop()));
		COMHandles.matrix_stack->Pop();
*/
	}

};