
#include "main.h"
#include "comcall.h"

void render_init()
{
	CHECK(D3DXCreateBox(COMHandles.device, 1.0f, 1.0f, 1.0f, &COMHandles.boxmesh, NULL));
}

void render_main()
{
	view_display();

	COMHandles.effect->Begin(0, 0);
	COMHandles.device->Clear(0, NULL, D3DCLEAR_ZBUFFER|D3DCLEAR_TARGET, 0, 1.0f, 0);
	COMHandles.effect->SetMatrixTranspose("vp", &proj);
	pass(0,0);
	COMHandles.effect->End();
}

extern "C" {

	void __stdcall drawprimitive(float r, float g, float b, float a, int ptype)
	{
		uploadparams();

		COMHandles.effect->SetMatrixTranspose("m", COMHandles.matrix_stack->GetTop());

		COMHandles.effect->SetRawValue("color", &r, 0, 16);
		COMHandles.effect->CommitChanges();

		COMHandles.boxmesh->DrawSubset(0);
	}

	void __stdcall placecamera()
	{
		COMHandles.matrix_stack->Push();
		COMHandles.matrix_stack->MultMatrix(&proj);
		COMHandles.effect->SetMatrixTranspose("vp", COMHandles.matrix_stack->GetTop());
		COMHandles.matrix_stack->Pop();
	}

};