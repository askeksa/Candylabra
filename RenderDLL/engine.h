
#ifndef __ENGINE_H__
#define __ENGINE_H__

virtual class Engine {
public:
	virtual void init() = 0;
	virtual void reinit() = 0;
	virtual void deinit() = 0;

	virtual void render() = 0;
	virtual void drawprimitive(float r, float g, float b, float a, int index) = 0;
	virtual void placelight(float r, float g, float b, float a, int index) = 0;
	virtual void placecamera() = 0;

	virtual float getaspect() = 0;
};

#endif
