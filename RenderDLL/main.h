#include <d3dx9.h>

extern "C" {
	void uploadparams();
	void pass(int effectpass, int treepass);
	void view_display();
	extern D3DXMATRIXA16 proj;
}