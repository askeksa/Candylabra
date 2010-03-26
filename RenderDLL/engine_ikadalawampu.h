
#include "engine.h"

class IkadalawampuEngine : public Engine {
	int p_particles, p_colortables, p_lines, p_pixels;
	int lastcolor0,lastcolor1;

	void setposition(char *name, int index);
public:
	IkadalawampuEngine() {}

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
