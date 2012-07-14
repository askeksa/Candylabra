
#define MAX_SHADERS 5

#include "engine.h"

#include <D3D11.h>
#include <d3dx11.h>
#include <D3Dcompiler.h>

typedef struct HWND__ *HWND;

struct ParameterOffsets {
	int base_offset;
	int matrix;
	int color;
	int mask;
	int firstvar;
	int firsttoolvar;
	int numvars;
	int stride;
};

class DX11ParticlesEngine : public Engine {
	int render_width;
	int render_height;
	float last_fov;
	float last_time;

	bool resizing;

	HWND window;
	ID3D11Device *d3dDevice;
	ID3D11DeviceContext *ImmediateContext;
	IDXGISwapChain *SwapChain;
	ID3D11Texture2D *BackBuffer;
	ID3D11UnorderedAccessView *TargetUAV;
	ID3D11Buffer *Constants, *ZBuffer, *ParticleBuffer, *ParticleBuffer2;
	ID3D11UnorderedAccessView *ZBufferUAV, *ParticleUAV, *Particle2UAV;
	ID3D11ComputeShader *CS[MAX_SHADERS];
	ID3D11ShaderReflection *reflect;

	ID3D11Buffer *DebugCount;

	struct ParameterOffsets global, spawner, affector;
	int *constantBuffer;
	int constantBufferSize;

	char predefVarsBuffer[4096];
	unsigned predefVarsIndex;
	unsigned predefVarsLength;

	void compileshaders();
	void constructlayout(ID3D10Blob *blob);
	void resizewindow1();
	void resizewindow2();
	void addPredefVar(unsigned index, const char *namefmt, ...);
	void handleVar(struct ParameterOffsets *po, const char *name, unsigned offset, unsigned size, ID3D11ShaderReflectionType *type);
	void putParams(struct ParameterOffsets *po, const float *color, int index, int *count);

public:
	DX11ParticlesEngine() : render_width(0), render_height(0), last_fov(0.0f), last_time(0), window(0), resizing(false),
		d3dDevice(0), ImmediateContext(0), SwapChain(0), BackBuffer(0), TargetUAV(0), Constants(0),
		reflect(0), constantBuffer(0)
	{
		for (int i = 0 ; i < MAX_SHADERS ; i++) {
			CS[i] = NULL;
		}
	}

	virtual void init();
	virtual void reinit();
	virtual void deinit();

	virtual void render();
	virtual void drawprimitive(float r, float g, float b, float a, int index);
	virtual void placelight(float r, float g, float b, float a, int index);
	virtual void placecamera();

	virtual float getaspect();
	virtual float random();

	virtual char *predefined_variables() {
		return predefVarsBuffer;
	}
	virtual bool use_effect() { return false; }
};
