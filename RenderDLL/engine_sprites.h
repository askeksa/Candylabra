
#include "engine.h"

class SpritesEngine : public Engine {
	int render_width;
	int render_height;

	void makesprites(char *path, int size);
	void prepare_render_surfaces();
	void blit_to_screen(int pass);
public:
	SpritesEngine();

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
