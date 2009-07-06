%include "comcall.nh"
%include "constants.nh"

global _interpret@4
extern _constantPool
extern _channelDeltas
extern _channelCounts
extern _frandom@0
extern _drawprimitive@20
extern _placelight@20
extern _placecamera@0

;parseParam
;esi: expression data
;ebx: constant pool
section parsepar code align=1
_parseParam:
	xor eax, eax
	lodsb
	cmp eax, dword 0xF0
	jg .not_constant
		;load constant
		fld dword [ebx+eax*4]
		ret
	.not_constant:
	sub eax, dword 0xF0
		dec eax
		jne .not_rand
		call _frandom@0
		ret
	.not_rand
	
	;;unary operations
	;load first argument
	push eax
	call _parseParam
	pop eax
	
	
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
	jne .not_round
	frndint
	ret
.not_round

	;;binary operations
	;load second argument
	push eax
	call _parseParam
	pop eax
	dec eax
	jne .not_pow
	fyl2x
	;; pow function - argh!
	fld1
	fld st1
	fprem
	fstp st1
	f2xm1
	fld1
	faddp st1
	fscale
	fstp st1
.not_pow
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
	dec eax
	jne .not_modulus
	fprem
	fstp st1
.not_modulus:
	dec eax
	jne .not_delta
	
	push eax
	fistp dword [esp]
	pop ebp
	push eax
	fistp dword [esp]
	pop eax
	shl eax, 9
	fld dword [_channelDeltas+eax+ebp*4]
	ret
.not_delta
	dec eax
	jne .not_count
	
	push eax
	fistp dword [esp]
	pop ebp
	push eax
	fistp dword [esp]
	pop eax
	shl eax, 9
	fild dword [_channelCounts+eax+ebp*4]
	ret
.not_count
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
	;comcall [comhandle(matrix_stack)], LoadIdentity
	
	mov ebx, _constantPool
	mov esi, dword [esp+9*4]
	;fill jumptable
	xor edx, edx
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

	popa
	ret 4


;opcode types:
;1: fanout
;	children
;   byte 0

;2: fix
;	children
;	byte 0

;3: repeat/call
;	byte label
;   word repeats+1

;4: primitive
;   expr b,g,r,a

;5: assign
;   expr value
;   byte var

;6: local assign
;   expr value
;   byte var

;7: conditional
;   expr condition
;   byte leftlabel
;   byte rightlabel

;8: nop

;9: rotate
;   expr roll
;   expr pitch
;   expr yaw

;10: scale
;   expr z,y,x

;11: translate
;   expr z,y,x


;;esi: program pointer
section traverse code align=1
_traverse:
	xor eax, eax
.skip_label:
	lodsb
	test al, al
	js .skip_label
	
	dec eax
	jnz .not_fanout
	;; ----------------
	;; fanout
	;; ----------------
	.fanout_loop:
		call _traverse
		cmp byte [esi], byte 0
		jne .fanout_loop
	lodsb
	ret

.not_fanout
	dec eax
	jnz .not_savetrans

	;; ----------------
	;; fanout with fix
	;; ----------------
	.fanout_savetrans_loop:
		comcall dword [comhandle(matrix_stack)], Push
		call _traverse
		comcall dword [comhandle(matrix_stack)], Pop
		cmp byte [esi], byte 0
		jne .fanout_savetrans_loop
	lodsb
	ret

.not_savetrans:
	dec eax
	jnz .not_call
	;; ----------------
	;; repeat/call
	;; ----------------
	lodsb

	push esi
	dec word [esi]
	jz .recur_end

		;recurse
		mov esi, dword [_jump_locations+eax*4]
		call _traverse

	.recur_end
	pop esi
	inc word [esi]
	lodsb
	lodsb
	ret

.not_call:
	dec eax
	jnz .not_primitive
	;; ----------------
	;; primitive
	;; ----------------
	lodsb
	push eax		;primitive index
	
	push byte 1
	pop edx
	push byte 4
	pop ecx

	;unpack arguments
.unpack_loop_primitive:
	call _parseParam
	push eax
	fmul dword [_param_scales+edx*4]
	fstp dword [esp]
	loop .unpack_loop_primitive

	call _drawprimitive@20
	ret

.not_primitive:
	dec eax
	jnz .not_light
	;; ----------------
	;; light
	;; ----------------
	lodsb
	push eax		;light index
	
	push byte 1
	pop edx
	push byte 4
	pop ecx

	;unpack arguments
.unpack_loop_light:
	call _parseParam
	push eax
	fmul dword [_param_scales+edx*4]
	fstp dword [esp]
	loop .unpack_loop_light

	call _placelight@20
	ret
	
.not_light:
	dec eax
	jnz .not_camera

	;; ----------------
	;; camera
	;; ----------------
	call _placecamera@0
	ret
	
.not_camera:
	dec eax
	jnz .not_assign

	;; ----------------
	;; assignment
	;; ----------------
	call _parseParam
	xor eax, eax
	lodsb
	fstp dword [ebx+eax*4]
	call _traverse
	ret
	
.not_assign:
	dec eax
	jnz .not_local_assign

	;; ----------------
	;; local assignment
	;; ----------------
	call _parseParam
	xor eax, eax
	lodsb
	push dword [ebx+eax*4]
	push eax
	fstp dword [ebx+eax*4]
	call _traverse
	pop eax
	pop dword [ebx+eax*4]
	ret
	
.not_local_assign:
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
	dec eax
	jnz .not_nopleaf

	ret

.not_nopleaf:
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
