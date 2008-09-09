#include <assert.h>
#include "Marching.h"

#define INDEX_AT(x,y,z) (x + (y << TEX_BITS) + (z << (2*TEX_BITS)))
#define TEX_MASK ((1<<TEX_BITS)-1)

extern "C" {
	int tetra_corners[7] = {
		INDEX_AT(-1,-1,0),
		INDEX_AT(-1,0,0),
		INDEX_AT(-1,0,-1),
		INDEX_AT(0,0,-1),
		INDEX_AT(0,-1,-1),
		INDEX_AT(0,-1,0),
		INDEX_AT(-1,-1,0)
	};
};

static int indices[4];
static float* out;

//magic masks
const int mask1 = 0x8ECD49;
const int mask2 = 0x4DCE89;

// (i1,i2) is the diagonal of the cell cube
// (i1,i2,i3) run counterclockwise as seen from outside the tetrahedron
inline static void tetrahedron(const celltype *tex) {
	int mask = mask1;
	if(tex[indices[0]]&0x80)
		mask = mask2;

	int c = 0;
	for(int i = 0; i < 6; i++) {
		int i1 = indices[(mask&3)];
		mask>>=2;
		int i2 = indices[(mask&3)];
		mask>>=2;

		//vertex
		int v1 = tex[i1]*2-255;
		int v2 = tex[i2]*2-255;
		if((v1 ^ v2) < 0) {
			for(int j = 0; j < 3; j++) {
				float d = (v2-v1)<<(TEX_BITS);
				*out++ = (v2*(i1&TEX_MASK) - v1*(i2&TEX_MASK))/d - 0.5f;
				i1>>=TEX_BITS;
				i2>>=TEX_BITS;
			}
			c++;
		}
	}

	if(c == 4) {	//quad
		for(int i = 0; i < 3; i++)
			*out++ = out[-12];
		for(int i = 0; i < 3; i++)
			*out++ = out[-9];
	}
}

int __stdcall marching_cubes(const celltype *tex, float *org_out) {
	out=org_out;
	for(int index = TEX_SIZE*TEX_SIZE*TEX_SIZE; index >= 0; index--) {
		if((index & TEX_MASK) && (index&(TEX_MASK<<TEX_BITS)) && (index&(TEX_MASK<<(TEX_BITS*2)))) {
			for (int t = 0; t < 6; t++) {
				indices[0] = index;
				indices[1] = index+INDEX_AT(-1,-1,-1);
				indices[2] = index+tetra_corners[t];
				indices[3] = index+tetra_corners[t+1];
				
				tetrahedron(tex);
			}
		}
	}
	return (out-org_out)/3;
}
