%include "comcall.nh"
%include "constants.nh"

global _uploadMesh@0
global _draw@0
global _lockedmeshes
global ?DemoInit@@YAXXZ
global _lockmesh

;extern _random@0
;extern ?EffectData@@3PADA
;extern _EffectDataEnd
extern __imp__D3DXCreateBox@24
extern __imp__D3DXCreateSphere@24
extern __imp__D3DXCreateCylinder@32
extern __imp__D3DXSaveMeshToXA@28
extern __imp__D3DXCreateMatrixStack@8
extern __imp__D3DXVec3TransformCoordArray@24
extern __imp__D3DXVec3TransformNormalArray@24
extern __imp__D3DXMatrixLookAtLH@16
extern __imp__D3DXMatrixMultiply@12
extern __imp__D3DXCreateRenderToEnvMap@28
extern __imp__D3DXCreateEffectFromFileA@32
extern __imp__D3DXCreateEffect@36
extern __imp__D3DXMatrixPerspectiveFovLH@20
extern __imp__D3DXWeldVertices@28
extern __imp__D3DXComputeNormals@8
extern __imp__ExitProcess@4
extern _printf
%ifdef DEBUG
extern _loadMeshDataFromFile@0
%endif
;extern _generateMusic@0
extern _proj

global _num_faces
global _num_vertices
global _composite_iptr
global _composite_vptr

struc lockedmesh
	.num_faces		resd 1
	.iptr			resd 1
	.num_vertices	resd 1
	.vptr			resd 1
endstruc

section crap bss align=4
_num_faces:			resd 1
_num_vertices:		resd 1
_composite_iptr:	resd 1
_composite_vptr:	resd 1

section lockmshs bss align=4
_lockedmeshes:
	resb lockedmesh_size*256
	
section misc data align=1
shaders_fx_string: db "shaders.fx", 0

section lockmesh code align=1
;edi: where to write the next lockedmesh
;ebp: mesh handle
_lockmesh:
	;; lockedmeshes[index].num_faces = mesh->GetNumFaces();
	comcall ebp, GetNumFaces
	stosd
	
	;; mesh->LockIndexBuffer(D3DLOCK_READONLY, (void**)&lockedmeshes[index].iptr);
	push edi
	push byte D3DLOCK_READONLY
	comcall ebp, LockIndexBuffer
	scasd

	;; lockedmeshes[index].num_vertices = mesh->GetNumVertices();
	comcall ebp, GetNumVertices
	stosd

	;; mesh->LockVertexBuffer(D3DLOCK_READONLY, (void**)&lockedmeshes[index].vptr);
	push edi
	push byte D3DLOCK_READONLY
	comcall ebp, LockVertexBuffer
	scasd
	
	ret

	
section upmesh code align=1
;eax: mesh index
_uploadMesh@0:
	pusha
	imul eax, byte lockedmesh_size
	lea ebx, [_lockedmeshes+eax]	;; ebx: lockedmesh
	
	;; copy and expand indices
	mov eax, dword [ebx]	;eax: num faces
	mov esi, dword [ebx+4]
	mov edi, dword [_composite_iptr]
	add dword [_num_faces], eax
	lea ecx, [eax*2+eax]
	.index_loop:
		xor eax, eax
		lodsw
		add eax, dword [_num_vertices]
		stosd
		loop .index_loop
	mov dword [_composite_iptr], edi
	
	mov esi, dword [ebx+12]	;mesh vptr
	mov edi, dword [_composite_vptr]
	
	;; transform positions
	comcall [comhandle(matrix_stack)], GetTop
	push dword [ebx+8]	;num vertices
	push eax
	push byte D3DVERTEX_SIZE
	push esi
	push byte VERTEX_SIZE
	push edi
	call dword [__imp__D3DXVec3TransformCoordArray@24]
	
	add esi, byte 3*FLOAT_SIZE
	add edi, byte 3*FLOAT_SIZE
	
	;; transform normals
	comcall [comhandle(matrix_stack)], GetTop
	push dword [ebx+8]	;num vertices
	push eax
	push byte D3DVERTEX_SIZE
	push esi
	push byte VERTEX_SIZE
	push edi
	call dword [__imp__D3DXVec3TransformNormalArray@24]
	
	;num_vertices += mesh->num_vertices
	mov ecx, dword [ebx+8]	;num vertices
	add dword [_num_vertices], ecx
	
	add edi, byte 3*FLOAT_SIZE
	mov eax, ebp
	
	.colorloop:
		stosd
		add edi, byte VERTEX_SIZE-4
		loop .colorloop
		
	sub edi, byte 6*FLOAT_SIZE
	mov dword [_composite_vptr], edi
	popa
	ret
	
section draw code align=1
_draw@0:
	pusha
	;; CHECK(COMHandles.device->SetVertexShaderConstantF(0, (float *)&vertex_data, sizeof(vertex_data)/16));
	push byte 4		;; number of float4's
	push _proj
	push byte 0
	comcall [comhandle(d3dd)], SetVertexShaderConstantF
	
	;; CHECK(COMHandles.device->SetPixelShaderConstantF(0, (float *)&pixel_data, sizeof(pixel_data)/16));
	;push byte 1		;; number of float4's
	;push _pixel_data
	;push byte 0
	;comcall [comhandle(d3dd)], SetPixelShaderConstantF
	
	;; COMHandles.device->SetFVF(MY_FVF);
	push byte MY_FVF
	comcall [comhandle(d3dd)], SetFVF
	
	;; COMHandles.device->SetIndices(COMHandles.composite_index);
	push dword [comhandle(composite_index)]
	comcall [comhandle(d3dd)], SetIndices
	
	;; COMHandles.device->SetStreamSource(0, COMHandles.composite_vertex, 0, sizeof(vertex));
	push byte VERTEX_SIZE
	push byte 0
	push dword [comhandle(composite_vertex)]
	push byte 0
	comcall [comhandle(d3dd)], SetStreamSource
	
	;; COMHandles.device->DrawIndexedPrimitive(D3DPT_TRIANGLELIST, 0, 0, num_vertices, 0, num_faces);
	push dword [_num_faces]
	push byte 0
	push dword [_num_vertices]
	push byte 0
	push byte 0
	push byte D3DPT_TRIANGLELIST
	comcall [comhandle(d3dd)], DrawIndexedPrimitive
	
	popa
	ret
