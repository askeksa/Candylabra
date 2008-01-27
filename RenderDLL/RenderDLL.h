// The following ifdef block is the standard way of creating macros which make exporting 
// from a DLL simpler. All files within this DLL are compiled with the RENDERDLL_EXPORTS
// symbol defined on the command line. this symbol should not be defined on any project
// that uses this DLL. This way any other project whose source files include this file see 
// RENDERDLL_API functions as being imported from a DLL, whereas this DLL sees symbols
// defined with this macro as being exported.
#ifdef RENDERDLL_EXPORTS
#define RENDERDLL_API __declspec(dllexport)
#else
#define RENDERDLL_API __declspec(dllimport)
#endif

// This class is exported from the RenderDLL.dll
class RENDERDLL_API CRenderDLL {
public:
	CRenderDLL(void);
	// TODO: add your methods here.
};

extern RENDERDLL_API int nRenderDLL;

RENDERDLL_API int fnRenderDLL(void);
