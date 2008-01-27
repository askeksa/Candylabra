%include "comcall.nh"
%include "constants.nh"

global _interpret@4
extern _uploadMesh@0
extern _constantPool
extern _composite_iptr
extern _composite_vptr
extern _num_vertices
extern _num_faces

;opcode types:
;1: fanout
;	children
;   byte 0

;2: repeat/call
;	byte label
;   byte repeats+1

;3: primitive
;   expr b,g,r

;4: assign
;   expr value
;   byte var

;5: conditional
;   expr condition
;   byte leftlabel
;   byte rightlabel

;6: rotate
;   expr roll
;   expr pitch
;   expr yaw

;7: scale
;   expr z,y,x

;8: translate
;   expr z,y,x

;parseParam
;esi: expression data
;ebx: constant pool
section parsepar code align=1
_parseParam:
	xor eax, eax
	lodsb
	test al, al
	js .not_constant
		;load constant
		fld dword [ebx+eax*4]
		ret
	.not_constant:
	;;unary operations
	;load first argument
	push eax
	call _parseParam
	pop eax
	
	and al, 0x7F
	dec eax
	jne .not_sin
	fmul	dword [_param_scales+0*4]
	fsin
	ret
	.not_sin:
	dec eax
	jne .not_clamp
	fldz
	fcomip st1
	jc .dont_clamp
	fstp st0
	fldz
	.dont_clamp
	ret	
	.not_clamp:
	dec eax
	jne .not_exp
		;; exp function - argh!
		fld1
		fld st1
		fprem
		fstp st1
		f2xm1
		fld1
		faddp st1
		fscale
		fstp st1
		ret
	.not_exp
	dec eax
	jne .not_round
		frndint
		;fld1
		;fld st1
		;fprem
		;fstp st1
		;fsubp st1
		ret
	.not_round
	
	;;binary operations
	;load second argument
	push eax
	call _parseParam
	pop eax
	
	dec eax
	jne .not_add
	faddp st1
.not_add:
	dec eax
	jne .not_sub
	fsubp st1
.not_sub:
	dec eax
	jne .not_mul
	fmulp st1
.not_mul:
	dec eax
	jne .not_div
	fdivp st1
.not_div:
	ret	

section sclparam data align=4
_param_scales:
dd  0x40c90fdb	;2pi Rotate		1.0 is a full revolution
dd	0x3f800000	;1   Scale
dd	0x3f800000	;1   Translate
dd  0x437f0000	;255 Primitive color

section jumptable bss align=4
_jump_locations: resd 256


section interpre code align=1
_interpret@4:
	pusha
	
	;; COMHandles.matrix_stack->LoadIdentity();
	comcall [comhandle(matrix_stack)], LoadIdentity
	
	;; Lock composite buffers
	;; COMHandles.composite_index->Lock(0, 0, (void**)&composite_iptr, 0);
	push byte D3DLOCK_DISCARD
	push _composite_iptr
	push byte 0
	push byte 0
	comcall [comhandle(composite_index)], Lock
	
	;; COMHandles.composite_vertex->Lock(0, 0, (void**)&composite_vptr, 0);
	push byte D3DLOCK_DISCARD
	push _composite_vptr
	push byte 0
	push byte 0
	comcall [comhandle(composite_vertex)], Lock
	
	
	mov ebx, _constantPool
	mov esi, dword [esp+9*4]
	;fill jumptable
	xor edx, edx
	mov dword [_num_vertices], edx
	mov dword [_num_faces], edx
	mov al, byte 0xFF
	mov edi, esi
	.fill_table:
		repne scasb
		mov dword [_jump_locations+edx*4], edi
		inc edx
		cmp byte [edi], 0xFE
		jne .fill_table
	
	mov esi, dword [esp+9*4]
	call _traverse
	
	comcall [comhandle(composite_index)], Unlock
	comcall [comhandle(composite_vertex)], Unlock
	popa
	ret 4

;;esi: program pointer
section traverse code align=1
_traverse:
	xor eax, eax
	lodsb
	test al, al
	jns .not_label
	lodsb
	.not_label:
	
	dec eax
	jnz .not_fanout
	;; ----------------
	;; fanout
	;; ----------------
	.fanout_loop:
		comcall dword [comhandle(matrix_stack)], Push
		call _traverse
		comcall dword [comhandle(matrix_stack)], Pop
		cmp byte [esi], byte 0
		jne .fanout_loop
	lodsb
	ret

.not_fanout
	dec eax
	jnz .not_call
	;; ----------------
	;; repeat/call
	;; ----------------
	xor eax, eax
	lodsb

	push esi
	dec byte [esi]
	jz .recur_end

	;recurse
	mov esi, dword [_jump_locations+eax*4]
	call _traverse

	.recur_end
	pop esi
	inc byte [esi]
	lodsb
	ret

.not_call:
	dec eax
	jnz .not_primitive
	;; ----------------
	;; primitive
	;; ----------------
	lodsb
	push eax
	
	push byte 3
	pop edx
	push byte 3
	pop ecx

	;unpack arguments
.unpack_loop_primitive:
	call _parseParam
	push eax
	fmul dword [_param_scales+edx*4]
	fistp dword [esp]
	loop .unpack_loop_primitive

	mov al,255
	shl	eax,8
	pop	ecx
	mov al,cl
	shl	eax,8
	pop	ecx
	mov al,cl
	shl	eax,8
	pop	ecx
	mov al,cl
	mov	ebp,eax

	pop eax
	call _uploadMesh@0		;TODO: is jmp better?
	ret
	
.not_primitive:
	dec eax
	jnz .not_assign

	;; ----------------
	;; assignment
	;; ----------------
	call _parseParam
	xor eax, eax
	lodsb
	push dword [ebx+eax*4]
	fstp dword [ebx+eax*4]
	push eax
	call _traverse
	pop eax
	pop dword [ebx+eax*4]
	ret
	
.not_assign:
	dec eax
	jnz .not_conditional

	;; ----------------
	;; conditional
	;; ----------------
	call _parseParam
	xor eax, eax
	lodsb
	mov edx, eax
	xor eax, eax
	lodsb
	push esi
	fldz
	fcomip st0,st1
	cmova eax, edx
	fstp st0

	mov esi, dword [_jump_locations+eax*4]
	call _traverse

	pop esi
	ret	
	
.not_conditional:
	;; ----------------
	;; transform
	;; rotate, scale or translate
	;; ----------------
	dec eax
	mov edx, eax
	push byte 3
	pop ecx

	;unpack arguments
	.unpack_loop:

	call _parseParam
	push eax
	fmul dword [_param_scales+edx*4]
	fstp dword [esp]
	loop .unpack_loop

	lea edx, [cc_RotateLocal+edx*2]	;exploit layout of rotate, scale, translate

	mov		eax, [comhandle(matrix_stack)]
	push	eax
	mov		eax, [eax]
	call	[eax + edx*4]

	call _traverse

	ret
