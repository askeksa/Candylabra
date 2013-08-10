#include <d3dx9.h>
#include <dxerr.h>
#include <cstdio>

#if 1
static void check(char *n, int r) {
	if (r != D3D_OK) {
		char buff[512];
		sprintf_s(buff, 512, "%s returned %s\n", n, DXGetErrorString(r));
		MessageBox(0, buff, 0, 0);
		ExitProcess(1);
	}
}
#define CHECK(s) check(#s, s)

static ID3DXBuffer *errors;
static void checkcompile(char *statement, int error) {
	if (error != D3D_OK) {
		char buff[2048];
		sprintf_s(buff, 2048, "%s\nfailed with error %s\n%s", statement, DXGetErrorString(error), errors->GetBufferPointer());
		MessageBox(0, buff, 0, 0);
		ExitProcess(1);
	}
}
#define CHECKC(s) checkcompile(#s, s)
#define ERRORS &errors
#else
#define CHECK(s) (s)
#define CHECKC(s) (s)
#define ERRORS NULL
#endif

extern "C" {
	void uploadparams();
	void pass(int effectpass, int treepass);
	void tree_pass(int treepass);
	void view_display();
	void setfov();
	float __stdcall mentor_synth_random();
	float __stdcall amiga_random();
	extern D3DXMATRIXA16 proj;
	extern char datafile[];
}

extern int render_return;
