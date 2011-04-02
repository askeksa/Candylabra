#ifndef _OBJGEN_H_
#define _OBJGEN_H_

struct d3dvertex {
	D3DXVECTOR3 pos;
	D3DXVECTOR3 normal;
};


struct lockedmesh {
	int num_faces;
	WORD* iptr;
	int num_vertices;
	d3dvertex* vptr;
};


extern "C" {
	void __stdcall initmesh();
	void __stdcall interpret(char* program);
	void __stdcall compileTree(char* program);
	void treecode(void);
	void __stdcall draw();
	void __stdcall render();
	extern lockedmesh lockedmeshes[];
};

#endif