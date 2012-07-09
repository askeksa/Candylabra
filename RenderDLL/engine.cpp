
#include "engine.h"
#include "main.h"
#include <assert.h>

char *Engine::predefined_variables() {
	return "time/seed/fov/pass/";
}

bool Engine::use_effect() {
	return true;
}
