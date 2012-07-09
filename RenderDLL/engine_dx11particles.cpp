
#define INITGUID

#include "engine_dx11particles.h"
#include "main.h"
#include "comcall.h"
#include "MemoryFile.h"

#include <assert.h>
#include <Windows.h>

extern char effectfile[];

extern "C" {
	extern RECT scissorRect;
	extern float constantPool[256];
	extern bool effect_valid;
};

float DX11ParticlesEngine::getaspect()
{
	return 16.0f / 9.0f;
}

void DX11ParticlesEngine::compileshaders() {
	if (pCS) {
		pCS->Release();
		pCS = NULL;
	}

	ID3D10Blob* pErrorBlob = NULL;
	ID3D10Blob* pBlob = NULL;
	HRESULT hr = D3DX11CompileFromFile(effectfile, NULL, NULL, "cs_5_0", "cs_5_0", D3D10_SHADER_DEBUG, NULL, NULL, &pBlob, &pErrorBlob, NULL);
	if (!FAILED(hr))
	{
		CHECK(pd3dDevice->CreateComputeShader((DWORD *)pBlob->GetBufferPointer(), pBlob->GetBufferSize(), NULL, &pCS));
		CHECK(D3DReflect(pBlob->GetBufferPointer(), pBlob->GetBufferSize(), IID_ID3D11ShaderReflection, (void **)&reflect));
		effect_valid = true;
	} else {
		char message[4096];
		sprintf(message, "unknown compiler error");
		if (pErrorBlob != NULL) {
			sprintf(message, "%s", pErrorBlob->GetBufferPointer());
		}
		MessageBox(0, message, "Error", MB_OK);
		effect_valid = false;
	}
	if (pErrorBlob) pErrorBlob->Release();
	if (pBlob) pBlob->Release();
}

void DX11ParticlesEngine::resizewindow1() {
	IDirect3DSwapChain9 *toolswapchain;
	D3DPRESENT_PARAMETERS toolpresentparams;
	CHECK(COMHandles.device->GetSwapChain(0, &toolswapchain));
	CHECK(toolswapchain->GetPresentParameters(&toolpresentparams));
	HWND toolwindow = toolpresentparams.hDeviceWindow;
	TITLEBARINFO tb;
	tb.cbSize = sizeof(TITLEBARINFO);
	GetTitleBarInfo(toolwindow, &tb);

	int	height = scissorRect.bottom - scissorRect.top;
	int width = (int)(height * getaspect());
	int top = tb.rcTitleBar.bottom + scissorRect.top;
	int left = (scissorRect.right + scissorRect.left) / 2 - width / 2;
	render_width = width;
	render_height = height;

	SetWindowPos(window, HWND_TOPMOST, left,top, width,height, 0);
}

void DX11ParticlesEngine::resizewindow2() {
	//MessageBox(0, "Resize 2", "Error", MB_OK);
	pImmediateContext->ClearState();
	if (pUAV) {
		pUAV->Release();
		pBackBuffer->Release();
		pUAV = NULL;
	}
	CHECK(pSwapChain->ResizeBuffers(2, 0,0, DXGI_FORMAT_R8G8B8A8_UNORM, 0));

	CHECK(pSwapChain->GetBuffer(0, __uuidof(ID3D11Texture2D), (LPVOID *)&pBackBuffer));
	CHECK(pd3dDevice->CreateUnorderedAccessView(pBackBuffer, NULL, &pUAV));
}

void DX11ParticlesEngine::init()
{
	int width = 42;
	int height = 42;
	window = CreateWindowA("edit", 0, WS_POPUP|WS_VISIBLE, 10,10, width,height,0/*toolwindow*/,0,0,0);

	int SwapChainDesc[] = { 
		width,height,0,0,DXGI_FORMAT_R8G8B8A8_UNORM,0,0,  // bufferdesc (w,h,refreshrate,format, scanline, scaling
		1,0, // sampledesc (count, quality)
		DXGI_USAGE_UNORDERED_ACCESS,
		2, // buffercount
		(int)window, // hwnd
		1,0,0 // windowed, swap_discard, flags
	};

	CHECK(D3D11CreateDeviceAndSwapChain(NULL, D3D_DRIVER_TYPE_HARDWARE, NULL, D3D11_CREATE_DEVICE_DEBUG, 0, 0, D3D11_SDK_VERSION,
		(DXGI_SWAP_CHAIN_DESC*)&SwapChainDesc[0], &pSwapChain, &pd3dDevice, NULL, &pImmediateContext));

	D3D11_BUFFER_DESC ConstBufferDesc = {16, D3D11_USAGE_DEFAULT,D3D11_BIND_CONSTANT_BUFFER,0, 0,0}; // 16,0,4,0,0,0
	CHECK(pd3dDevice->CreateBuffer(&ConstBufferDesc, NULL, &pConstants));

	compileshaders();

	render_width = 0;
	render_height = 0;
}

void DX11ParticlesEngine::reinit()
{
	compileshaders();
}

void DX11ParticlesEngine::deinit()
{
	if (window) {
		pd3dDevice->Release();
		ShowWindow(window, SW_HIDE);
		DestroyWindow(window);
		window = NULL;
	}
}


void DX11ParticlesEngine::render()
{
	if (scissorRect.bottom - scissorRect.top != render_height) {
		resizewindow1();
		resizewindow2();
		resizing = true;
	} else if (resizing) {
		resizing = false;
	}

	MSG msg;
	if (PeekMessage(&msg, window, 0, 0, PM_REMOVE)) {
		//MessageBox(0, "Message", "Error", MB_OK);
		if ((msg.message & 0xffff) == WM_SIZE) {
			resizewindow2();
		}
	}

	pImmediateContext->CSSetUnorderedAccessViews(0, 1, &pUAV, 0);
	pImmediateContext->CSSetConstantBuffers(0, 1, &pConstants);
	pImmediateContext->CSSetShader(pCS, NULL, 0);
	pImmediateContext->UpdateSubresource(pConstants,0,0,&constantPool[0],4,4);
	pImmediateContext->Dispatch( render_width/16, render_height/16, 1);
	pSwapChain->Present(0, 0);
}

void DX11ParticlesEngine::drawprimitive(float r, float g, float b, float a, int index)
{
}

void DX11ParticlesEngine::placelight(float r, float g, float b, float a, int index)
{
}

void DX11ParticlesEngine::placecamera()
{
}

float DX11ParticlesEngine::random()
{
	return mentor_synth_random();
}
