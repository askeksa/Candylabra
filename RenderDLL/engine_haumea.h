
#include "engine.h"

class HaumeaEngine : public Engine {
	void setposition(char *name, int index);
public:
	HaumeaEngine() {}

	virtual void init();
	virtual void reinit();
	virtual void deinit();

	virtual void render();
	virtual void drawprimitive(float r, float g, float b, float a, int index);
	virtual void placelight(float r, float g, float b, float a, int index);
	virtual void placecamera();

	virtual float getaspect();
};