
#include "engine.h"

class AtriumEngine : public Engine {
	int render_width;
	int render_height;
	float last_fov;

	void makeobjects();
	void prepare_render_surfaces();
	void blit_to_screen(int pass);
public:
	AtriumEngine() : render_width(0), render_height(0), last_fov(0.0f) {}

	virtual void init();
	virtual void reinit();
	virtual void deinit();

	virtual void render();
	virtual void drawprimitive(float r, float g, float b, float a, int index);
	virtual void placelight(float r, float g, float b, float a, int index);
	virtual void placecamera();

	virtual float getaspect();
	virtual float random();
};
