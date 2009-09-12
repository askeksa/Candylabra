
#include "engine.h"

extern "C" {
	void render_init();
	void render_reinit();
	void render_deinit();
	void render_main();
	void __stdcall drawprimitive(float r, float g, float b, float a, int index);
	void __stdcall placelight(float r, float g, float b, float a, int index);
	void __stdcall placecamera();
}

extern Engine *active_engine;
