
//#define PRINTPARTICLES

#define MAX_WIDTH 1920
#define MAX_HEIGHT 1080
#define MAX_PARTICLES (4*1024*1024)
#define MAX_SPAWN_PARTICLES 262144

#define INITGUID

#include "engine_dx11particles.h"
#include "main.h"
#include "comcall.h"
#include "MemoryFile.h"

#include <assert.h>
#include <varargs.h>
#include <Windows.h>

extern char effectfile[];

extern "C" {
	extern RECT scissorRect;
	extern float constantPool[256];
	extern bool effect_valid;
};


float GetSecs()
{	
	static LARGE_INTEGER frequency={0,0},t0,t;
	if (frequency.QuadPart==0)
	{
		QueryPerformanceFrequency(&frequency);
		QueryPerformanceCounter(&t0);
	}
	QueryPerformanceCounter(&t);
	float f= float(((double)(t.QuadPart-t0.QuadPart) / (double)frequency.QuadPart));
	return f;
}

float DX11ParticlesEngine::getaspect()
{
	return 16.0f / 9.0f;
}

void DX11ParticlesEngine::compileshaders() {
	effect_valid = true;
	for (int si = 0 ; si < MAX_SHADERS ; si++) {
		if (CS[si]) {
			CS[si]->Release();
			CS[si] = NULL;
		}

		ID3D10Blob* pErrorBlob = NULL;
		ID3D10Blob* pBlob = NULL;
		char entry[10];
		sprintf(entry, "_%d", si);
		HRESULT hr = D3DX11CompileFromFile(effectfile, NULL, NULL, entry, "cs_5_0", D3D10_SHADER_ENABLE_BACKWARDS_COMPATIBILITY, NULL, NULL, &pBlob, &pErrorBlob, NULL);
		if (!FAILED(hr))
		{
			CHECK(d3dDevice->CreateComputeShader((DWORD *)pBlob->GetBufferPointer(), pBlob->GetBufferSize(), NULL, &CS[si]));
			if (si == 0) {
				constructlayout(pBlob);
			}
		} else {
			char message[4096];
			sprintf(message, "unknown compiler error");
			if (pErrorBlob != NULL) {
				sprintf(message, "%s", pErrorBlob->GetBufferPointer());
			}
			if (strstr(message, "entrypoint not found") == 0) {
				MessageBox(0, message, "Error", MB_OK);
				effect_valid = false;
			}
		}
		if (pErrorBlob) pErrorBlob->Release();
		if (pBlob) pBlob->Release();
	}

}

void initOffsets(struct ParameterOffsets *po) {
	po->base_offset = -1;
	po->matrix = -1;
	po->color = -1;
	po->mask = -1;
	po->firstvar = -1;
	po->firsttoolvar = -1;
	po->numvars = 0;
	po->stride = -1;
}

void DX11ParticlesEngine::addPredefVar(unsigned index, const char *namefmt, ...) {
	va_list ap;
	va_start(ap, namefmt);
	while (predefVarsIndex < index) {
		predefVarsLength += sprintf(&predefVarsBuffer[predefVarsLength], "dummy%d/", predefVarsIndex);
		predefVarsIndex++;
	}
	predefVarsLength += vsprintf(&predefVarsBuffer[predefVarsLength], namefmt, ap);
	predefVarsLength += sprintf(&predefVarsBuffer[predefVarsLength], "/");
	predefVarsIndex++;
	va_end(ap);
}

void DX11ParticlesEngine::handleVar(struct ParameterOffsets *po, const char *name, unsigned offset, unsigned size, ID3D11ShaderReflectionType *type) {
	D3D11_SHADER_TYPE_DESC tdesc;
	type->GetDesc(&tdesc);
	printf("%s %d\n", name, offset);
	switch (tdesc.Class) {
	case D3D10_SVC_SCALAR:
		switch (tdesc.Type) {
		case D3D10_SVT_FLOAT:
			if (po->firsttoolvar == -1) {
				po->firsttoolvar = predefVarsIndex;
				po->firstvar = offset;
			}
			addPredefVar(po->firsttoolvar + (offset - po->firstvar), name);
			po->numvars = offset - po->firstvar + 1;
			break;
		case D3D10_SVT_INT:
			if (strcmp(name, "mask") == 0) {
				po->mask = offset;
				break;
			}
			/* Fall through */
		default:
			printf("Unsupported scalar type for variable %s: %d\n", name, tdesc.Type);
			break;
		}
		break;
	case D3D10_SVC_VECTOR:
		switch (tdesc.Type) {
		case D3D10_SVT_FLOAT:
			if (strcmp(name, "mcolor") == 0) {
				if (tdesc.Columns == 4) {
					po->color = offset;
				} else {
					printf("Color variable with less than 4 components\n");
				}
				break;
			}
			if (po->firsttoolvar == -1) {
				po->firsttoolvar = predefVarsIndex;
				po->firstvar = offset;
			}
			for (unsigned vi = 0 ; vi < tdesc.Columns ; vi++) {
				addPredefVar(po->firsttoolvar + (offset + vi - po->firstvar), "%s%d", name, vi+1);
			}
			po->numvars = offset + tdesc.Columns - po->firstvar;
			break;
		default:
			printf("Unsupported vector type for variable %s: %d\n", name, tdesc.Type);
			break;
		}
		break;
	case D3D10_SVC_MATRIX_ROWS:
	case D3D10_SVC_MATRIX_COLUMNS:
		switch (tdesc.Type) {
		case D3D10_SVT_FLOAT:
			if (po->matrix == -1) {
				po->matrix = offset;
			} else {
				printf("Duplicate matrix declaration %s\n", name);
				break;
			}
			break;
		default:
			printf("Unsupported matrix type for variable %s: %d\n", name, tdesc.Type);
			break;
		}
		break;
	case D3D10_SVC_STRUCT:
		struct ParameterOffsets *spo;
		if (strcmp(name, "spawners") == 0) {
			spo = &spawner;
		} else if (strcmp(name, "affectors") == 0) {
			spo = &affector;
		} else {
			printf("Unrecognized struct variable %s\n", name);
			break;
		}
		spo->base_offset = offset;
		spo->stride = (size / tdesc.Elements + 3) & -4;
		for (unsigned sti = 0 ; sti < tdesc.Members ; sti++) {
			ID3D11ShaderReflectionType *stype = type->GetMemberTypeByIndex(sti);
			D3D11_SHADER_TYPE_DESC stdesc;
			stype->GetDesc(&stdesc);
			handleVar(spo, type->GetMemberTypeName(sti), stdesc.Offset / 4, 0, stype);
		}
		break;
	default:
		printf("Unsupported class for variable %s: %d\n", name, tdesc.Class);
		break;
	}
}

void layoutline(int val, const char *name, const char *field) {
	if (val != -1) printf("#define %s_%s %d\n", name, field, val);
}

void printlayout(struct ParameterOffsets *po, const char *name) {
	layoutline(po->base_offset, name, "OFFSET");
	layoutline(po->stride, name, "STRIDE");
	layoutline(po->matrix, name, "MATRIX");
	layoutline(po->color, name, "COLOR");
	layoutline(po->mask, name, "MASK");
	layoutline(po->firstvar, name, "FIRSTVAR");
	layoutline(po->firsttoolvar, name, "FIRSTTOOLVAR");
	layoutline(po->numvars, name, "NUMVARS");
}

void DX11ParticlesEngine::constructlayout(ID3D10Blob *blob) {
	initOffsets(&global);
	initOffsets(&spawner);
	initOffsets(&affector);

	predefVarsIndex = 0;
	predefVarsLength = 0;
	addPredefVar(0, "time");
	addPredefVar(1, "seed");
	addPredefVar(2, "fov");
	addPredefVar(3, "pass");

	CHECK(D3DReflect(blob->GetBufferPointer(), blob->GetBufferSize(), IID_ID3D11ShaderReflection, (void **)&reflect));
	ID3D11ShaderReflectionConstantBuffer *cb = reflect->GetConstantBufferByIndex(0);
	D3D11_SHADER_BUFFER_DESC cbdesc;
	cb->GetDesc(&cbdesc);
	printf("%s\n", cbdesc.Name);
	for (unsigned cbi = 0 ; cbi < cbdesc.Variables ; cbi++) {
		ID3D11ShaderReflectionVariable *cbv = cb->GetVariableByIndex(cbi);
		D3D11_SHADER_VARIABLE_DESC vdesc;
		cbv->GetDesc(&vdesc);
		ID3D11ShaderReflectionType *vt = cbv->GetType();
		handleVar(&global, vdesc.Name, vdesc.StartOffset / 4, vdesc.Size / 4, vt);
	}

	printlayout(&global, "GLOBAL");
	printlayout(&spawner, "SPAWNER");
	printlayout(&affector, "AFFECTOR");
	fflush(stdout);

	if (Constants) {
		Constants->Release();
		Constants = NULL;
	}
	if (constantBuffer) {
		free(constantBuffer);
		constantBuffer = NULL;
	}
	D3D11_BUFFER_DESC ConstBufferDesc = {cbdesc.Size, D3D11_USAGE_DEFAULT,D3D11_BIND_CONSTANT_BUFFER,0, 0,0};
	CHECK(d3dDevice->CreateBuffer(&ConstBufferDesc, NULL, &Constants));
	constantBuffer = (int *)malloc(cbdesc.Size);
	constantBufferSize = cbdesc.Size;
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
	ImmediateContext->ClearState();
	if (TargetUAV) {
		TargetUAV->Release();
		BackBuffer->Release();
		TargetUAV = NULL;
	}
	CHECK(SwapChain->ResizeBuffers(2, 0,0, DXGI_FORMAT_R8G8B8A8_UNORM, 0));

	CHECK(SwapChain->GetBuffer(0, __uuidof(ID3D11Texture2D), (LPVOID *)&BackBuffer));
	CHECK(d3dDevice->CreateUnorderedAccessView(BackBuffer, NULL, &TargetUAV));
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
		(DXGI_SWAP_CHAIN_DESC*)&SwapChainDesc[0], &SwapChain, &d3dDevice, NULL, &ImmediateContext));

#ifdef PRINTPARTICLES
	D3D11_BUFFER_DESC ConstDesc={
		16, //UINT ByteWidth;
    D3D11_USAGE_STAGING, // D3D11_USAGE Usage;
    0, //UINT BindFlags;
    D3D11_CPU_ACCESS_READ, // UINT CPUAccessFlags;
    0, // UINT MiscFlags;
		0}; //UINT StructureByteStride;
	CHECK(d3dDevice->CreateBuffer( &ConstDesc, NULL, &DebugCount));
#endif

	// screen int buffer
	D3D11_BUFFER_DESC sbDesc;
	sbDesc.BindFlags =D3D11_BIND_UNORDERED_ACCESS;
	sbDesc.BindFlags |= D3D11_BIND_SHADER_RESOURCE;
	sbDesc.Usage = D3D11_USAGE_DEFAULT;
	sbDesc.MiscFlags =D3D11_RESOURCE_MISC_BUFFER_STRUCTURED;
	sbDesc.CPUAccessFlags	= 0;
	sbDesc.StructureByteStride	= 4;
	sbDesc.ByteWidth		= 4 * MAX_WIDTH * MAX_HEIGHT;
	CHECK(d3dDevice->CreateBuffer( &sbDesc, NULL, &ZBuffer ));

	// particle buffers
	sbDesc.StructureByteStride	= (3+3+4+1)*4;
	sbDesc.ByteWidth		= (3+3+4+1)*4*MAX_PARTICLES;
	CHECK(d3dDevice->CreateBuffer( &sbDesc, NULL, &ParticleBuffer ));
	CHECK(d3dDevice->CreateBuffer( &sbDesc, NULL, &ParticleBuffer2 ));
	
	// uavs for particles+z
	D3D11_UNORDERED_ACCESS_VIEW_DESC uavdesc;
	uavdesc.Format= DXGI_FORMAT_UNKNOWN;
	uavdesc.ViewDimension = D3D11_UAV_DIMENSION_BUFFER; 
	uavdesc.Buffer.FirstElement=0; 
	uavdesc.Buffer.Flags = 0;
	uavdesc.Buffer.NumElements= MAX_WIDTH * MAX_HEIGHT;
	CHECK(d3dDevice->CreateUnorderedAccessView(ZBuffer, &uavdesc, &ZBufferUAV ));
	uavdesc.Buffer.Flags = D3D11_BUFFER_UAV_FLAG_COUNTER;//D3D11_BUFFER_UAV_FLAG_APPEND; 
	uavdesc.Buffer.NumElements= MAX_PARTICLES;
	CHECK(d3dDevice->CreateUnorderedAccessView(ParticleBuffer, &uavdesc, &ParticleUAV ));
	CHECK(d3dDevice->CreateUnorderedAccessView(ParticleBuffer2, &uavdesc, &Particle2UAV ));

	compileshaders();

	render_width = 0;
	render_height = 0;

	last_time = GetSecs();
}

void DX11ParticlesEngine::reinit()
{
	compileshaders();

	last_time = GetSecs();
}

void DX11ParticlesEngine::deinit()
{
	if (window) {
		d3dDevice->Release();
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

	constantBuffer[1] = 0;
	constantBuffer[2] = 0;
	constantBuffer[3] = render_width;
	constantBuffer[4] = render_height;
	tree_pass(0);
	memcpy(&constantBuffer[global.firstvar], &constantPool[global.firsttoolvar], global.numvars*4);
	float time = GetSecs();
	*(float *)&constantBuffer[6] *= (time - last_time);
	last_time = time;

	ID3D11UnorderedAccessView *tuav=ParticleUAV;ParticleUAV=Particle2UAV;Particle2UAV=tuav;
	
	ID3D11UnorderedAccessView* ppUAV[4]= {ParticleUAV, Particle2UAV,ZBufferUAV,TargetUAV};
	UINT counts[4]={-1,0,0,0}; // flot dx at kræve uint og -1 værdier (for keep)..
	ImmediateContext->ClearUnorderedAccessViewUint(ZBufferUAV,(unsigned int*)&counts[0]); // clear to -1
	ImmediateContext->CSSetUnorderedAccessViews(0, 4, ppUAV, counts);
	
	ImmediateContext->UpdateSubresource(Constants, 0,0,constantBuffer, constantBufferSize,constantBufferSize);		
	ImmediateContext->CopyStructureCount(Constants,0,ParticleUAV);  // set first uint to count
	ImmediateContext->CSSetConstantBuffers( 0, 1, &Constants );

#ifdef PRINTPARTICLES
	ImmediateContext->CopyStructureCount(DebugCount,0,ParticleUAV);  
	D3D11_MAPPED_SUBRESOURCE mapped;
	ImmediateContext->Map(DebugCount, 0, D3D11_MAP_READ, 0, &mapped);
	char buffer[100]; sprintf(buffer,"%d\n", *(int*)mapped.pData);
	OutputDebugString(buffer);
	ImmediateContext->Unmap(DebugCount, 0);
#endif

	ImmediateContext->CSSetShader( CS[0], 0, 0 ); // spawn
	ImmediateContext->Dispatch( MAX_SPAWN_PARTICLES/256, 1, 1);
	ImmediateContext->CSSetShader( CS[1], 0, 0 ); // simulate/render
	ImmediateContext->Dispatch( MAX_PARTICLES/256, 1, 1);
  
	ImmediateContext->CSSetShader( CS[2], 0, 0 ); // postproc
	ImmediateContext->Dispatch( (render_width+15)/16, (render_height+15)/16, 1);

	SwapChain->Present(0, 0);
}

void DX11ParticlesEngine::putParams(struct ParameterOffsets *po, const float *color, int mask, int *count) {
	int offset = po->base_offset + (*count) * po->stride;
	if (po->matrix != -1) memcpy(&constantBuffer[offset + po->matrix], COMHandles.matrix_stack->GetTop(), 16*4);
	if (po->color != -1) memcpy(&constantBuffer[offset + po->color], color, 4*4);
	if (po->mask != -1) constantBuffer[offset + po->mask] = mask;
	memcpy(&constantBuffer[offset + po->firstvar], &constantPool[po->firsttoolvar], po->numvars*4);
	(*count)++;
}

void DX11ParticlesEngine::drawprimitive(float r, float g, float b, float a, int index)
{
	putParams(&spawner, &r, index, &constantBuffer[1]);
	//printf("Spawn %f particles\n", *(float *)&constantBuffer[spawner.base_offset + (constantBuffer[1]-1) * spawner.stride + 27]);
}

void DX11ParticlesEngine::placelight(float r, float g, float b, float a, int index)
{
	putParams(&affector, &r, index, &constantBuffer[2]);
	//printf("%d affectors\n", constantBuffer[2]);
}

void DX11ParticlesEngine::placecamera()
{
	if (global.matrix != -1) memcpy(&constantBuffer[global.matrix], COMHandles.matrix_stack->GetTop(), 16*4);
}

float DX11ParticlesEngine::random()
{
	return mentor_synth_random();
}
