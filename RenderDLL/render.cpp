
#include "render.h"

Engine *active_engine;

void render_init()
{
	active_engine->init();
}

void render_reinit()
{
	active_engine->reinit();
}

void render_deinit()
{
	active_engine->deinit();
}

void render_main()
{
	active_engine->render();
}

void __stdcall drawprimitive(float r, float g, float b, float a, int index)
{
	active_engine->drawprimitive(r,g,b,a,index);
}

void __stdcall placelight(float r, float g, float b, float a, int index)
{
	active_engine->placelight(r,g,b,a,index);
}

void __stdcall placecamera()
{
	active_engine->placecamera();
}
