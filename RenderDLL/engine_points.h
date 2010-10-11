
#include "engine.h"

#include <d3d9.h>

#define MAX_POINTS 200000

struct PointVertex {
	float x,y,z,size;
	float r,g,b,a;
};

#define POINTS_FVF (D3DFVF_XYZ | D3DFVF_TEX2 | D3DFVF_TEXCOORDSIZE1(0) | D3DFVF_TEXCOORDSIZE4(1))

class PointsEngine : public Engine {
	int render_width;
	int render_height;
	float last_fov;

	int n_points;
	struct PointVertex *mapped_buffer;

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
	char *predefined_variables();
};
