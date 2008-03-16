%include "constants.nh"
%include "comcall.nh"

extern _proj
extern __imp__D3DXMatrixPerspectiveFovLH@20
extern __imp__D3DXCreateMatrixStack@8
extern _lockedmeshes
extern _lockmesh
extern __imp__D3DXCreateBox@24
extern __imp__D3DXCreateSphere@24
extern __imp__D3DXCreateCylinder@32
extern __imp__D3DXWeldVertices@28
extern __imp__D3DXComputeNormals@8
extern _num_faces
extern _num_vertices
extern _syncinit@0

global _dllinit@0

section demoinit code align=1
_dllinit@0:
	pusha
	call _syncinit@0

	;; ---------------------------------
	;; init mesh
	;; ---------------------------------
	;; COMHandles.device->CreateIndexBuffer(MAX_FACES*3*sizeof(int), D3DUSAGE_DYNAMIC, D3DFMT_INDEX32, D3DPOOL_SYSTEMMEM, &COMHandles.composite_index, NULL);
	push byte 0
	push comhandle(composite_index)
	push byte D3DPOOL_SYSTEMMEM
	push byte D3DFMT_INDEX32
	push D3DUSAGE_DYNAMIC
	push MAX_FACES*3*INT_SIZE
	comcall [comhandle(d3dd)], CreateIndexBuffer
	
	;; COMHandles.device->CreateVertexBuffer(MAX_VERTICES*sizeof(vertex), D3DUSAGE_DYNAMIC, MY_FVF, D3DPOOL_SYSTEMMEM, &COMHandles.composite_vertex, NULL);
	push byte 0
	push comhandle(composite_vertex)
	push byte D3DPOOL_SYSTEMMEM
	push byte MY_FVF
	push D3DUSAGE_DYNAMIC
	push MAX_VERTICES*VERTEX_SIZE
	comcall [comhandle(d3dd)], CreateVertexBuffer
	
	;; D3DXCreateMatrixStack(0, &COMHandles.matrix_stack);
	push comhandle(matrix_stack)
	push byte 0
	call dword [__imp__D3DXCreateMatrixStack@8]
	
	mov edi, _lockedmeshes
	
	;; D3DXCreateBox(COMHandles.device, 1.0f, 1.0f, 1.0f, &mesh, NULL);
	push eax		;mesh handle
	mov eax, esp
	push byte 0
	push eax
	push 0x3f800000
	push 0x3f800000
	push 0x3f800000
	push dword [comhandle(d3dd)]
	call dword [__imp__D3DXCreateBox@24]
	pop ebp	;mesh handle
	call _lockmesh
	
	;; D3DXCreateSphere(COMHandles.device, 1.0f, 8,8, &mesh, NULL);
	push eax
	mov eax, esp
	push byte 0
	push eax
	push byte 8
	push byte 8
	push 0x3f800000
	push dword [comhandle(d3dd)]
	call dword [__imp__D3DXCreateSphere@24]
	pop ebp
	call _lockmesh
	
	;; D3DXCreateCylinder(COMHandles.device, 1.0f, 1.0f, 1.0f, 8,8, &mesh, NULL);
	push eax
	mov eax, esp
	push byte 0
	push eax
	push byte 8
	push byte 8
	push 0x3f800000
	push 0x3f800000
	push 0x3f800000
	push dword [comhandle(d3dd)]
	call dword [__imp__D3DXCreateCylinder@32]
	pop ebp
	call _lockmesh

	; Smooth Box
	push eax		;mesh handle
	mov eax, esp
	push byte 0
	push eax
	push 0x3f800000
	push 0x3f800000
	push 0x3f800000
	push dword [comhandle(d3dd)]
	call dword [__imp__D3DXCreateBox@24]
	pop ebp	;mesh handle

	push byte 0 ; ppVertexRemap
	push byte 0 ; pFaceRemap
	push byte 0 ; pAdjacencyOut
	push byte 0 ; pAdjacencyIn
	push byte 0 ; pEpsilons
	push byte 1 ; flags = D3DXWeldEpsilons_WELDALL
	push ebp
	call dword [__imp__D3DXWeldVertices@28]

	push byte 0 ; pAdjacency
	push ebp
	call dword [__imp__D3DXComputeNormals@8]

	call _lockmesh
	
	;; TODO: enable bilinear filtering?	
	
	popa
	ret
