%include "constants.nh"
%include "comcall.nh"

extern _proj
extern __imp__D3DXMatrixPerspectiveFovLH@20
extern __imp__D3DXCreateMatrixStack@8
extern __imp__D3DXCreateBox@24
extern __imp__D3DXCreateSphere@24
extern __imp__D3DXCreateCylinder@32
extern __imp__D3DXWeldVertices@28
extern __imp__D3DXComputeNormals@8
extern _constantPool

global _rand_scale
global _frandom@0

section realdata data align=4
_rand_scale: dd 0.000030517578125	;1/32768

section rand code align=1
_frandom@0:
	mov eax, dword [_constantPool+4]
	imul eax, 16307
	add eax, byte 17
	mov [_constantPool+4], eax
	shr eax, 14
	push eax
	fild word [esp]
	fmul dword [_rand_scale]
	pop eax
	ret
