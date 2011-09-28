
#include "engine.h"

#include <d3d9.h>

#define MAX_POINTS 1000000

#define USE_INSTANCING 0

struct PointVertex {
	float x,y,z,size2;
	float r,g,b,a;
};

struct PointTriVertex {
	struct PointVertex point;
	float ox,oy;
};

struct CornerVertex {
	float x,y;
};

#define POINTS_FVF (D3DFVF_XYZW | D3DFVF_TEX1 | D3DFVF_TEXCOORDSIZE4(0))
#define POINT_TRI_FVF (D3DFVF_XYZW | D3DFVF_TEX2 | D3DFVF_TEXCOORDSIZE4(0) | D3DFVF_TEXCOORDSIZE2(1))

class PointsEngine : public Engine {
	int render_width;
	int render_height;
	float last_fov;

	unsigned int *point_bucket_sizes;
	struct PointVertex *point_buckets;
#if USE_INSTANCING
	struct PointVertex *mapped_buffer;
#else
	struct PointTriVertex *mapped_buffer;
#endif
	void makeobjects();
	void prepare_render_surfaces();
	void blit_to_screen(int pass, IDirect3DTexture9 *from);
public:
	PointsEngine() : render_width(0), render_height(0), last_fov(0.0f) {}

	virtual void init();
	virtual void reinit();
	virtual void deinit();

	virtual void render();
	virtual void drawprimitive(float r, float g, float b, float a, int index);
	virtual void placelight(float r, float g, float b, float a, int index);
	virtual void placecamera();

	virtual float getaspect();
	virtual float random();
	//char *predefined_variables();
};
