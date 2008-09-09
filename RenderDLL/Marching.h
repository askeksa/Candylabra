#define TEX_BITS 6
#define TEX_SIZE (1 << TEX_BITS)

typedef unsigned char celltype;

int __stdcall marching_cubes(const celltype *tex, float *out);

extern "C" {
	int __stdcall marching_cubes_asm(const celltype *tex, float *out);
};


/*
12 14 13
31 41 21
21 23 24
42 32 12
31 34 32
23 43 13
41 42 43
34 24 14

12 14-32
32-14 34

23-41 21
43 41-23

12 42-13
13-42 43

31-24 21
34 24-31

13 23-14
14-23 24

41-32 31
42 32-41

*/