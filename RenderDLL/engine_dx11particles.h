
#include "engine.h"

#include <D3D11.h>
#include <d3dx11.h>
#include <D3Dcompiler.h>

typedef struct HWND__ *HWND;

class DX11ParticlesEngine : public Engine {
	int render_width;
	int render_height;
	float last_fov;

	bool resizing;

	HWND window;
	ID3D11Device *pd3dDevice;
	ID3D11DeviceContext *pImmediateContext;
	IDXGISwapChain *pSwapChain;
	ID3D11Texture2D *pBackBuffer;
	ID3D11UnorderedAccessView *pUAV;
	ID3D11Buffer *pConstants;
	ID3D11ComputeShader *pCS;
	ID3D11ShaderReflection *reflect;

	void compileshaders();
	void resizewindow1();
	void resizewindow2();

public:
	DX11ParticlesEngine() : render_width(0), render_height(0), last_fov(0.0f), window(0), resizing(false),
	pd3dDevice(0), pImmediateContext(0), pSwapChain(0), pBackBuffer(0), pUAV(0), pConstants(0), pCS(0),
	reflect(0) {}

	virtual void init();
	virtual void reinit();
	virtual void deinit();

	virtual void render();
	virtual void drawprimitive(float r, float g, float b, float a, int index);
	virtual void placelight(float r, float g, float b, float a, int index);
	virtual void placecamera();

	virtual float getaspect();
	virtual float random();

	virtual bool use_effect() { return false; }
};
