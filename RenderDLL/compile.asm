
%include "comcall.nh"
%include "constants.nh"

extern _constantPool
extern _drawprimitive@20
extern _placelight@20
extern _placecamera@0
extern _channelDeltas
extern _channelCounts
extern _timerFac
extern _channelFac
extern _nodecount
extern _subexpcount
extern __imp__MessageBoxA@16
global _compileTree@4
global _treecode

%macro mb 1
	jmp %%box
%%text:
	db %1,0
%%box:
	pusha
	push byte 0
	push byte 0
	push %%text
	push byte 0
	call [__imp__MessageBoxA@16]
	popa
%endmacro

%macro emb 1
	jmp %%emit
%%text:
	db %1,0
%%box:
	pusha
	push byte 0
	push byte 0
	push %%text
	push byte 0
	call [__imp__MessageBoxA@16]
	popa
%%endbox:
%%emit:
	push esi
	push ecx
	mov esi, %%box
	mov ecx, %%endbox-%%box
	rep movsb
	pop ecx
	pop esi
%endmacro


section snips text align=1
	_snips:
section snipoffs data align=1
	_snipoffs:

%macro snip 1
	section snips
	_snip_%1:
	section snipoffs
	_snipoff_%1:
		db _snip_%1-_snips
	_snip_id_%1 equ _snipoff_%1-_snipoffs
	section snips
%endmacro

%macro emit 1
	mov al, _snip_id_%1
	call emitCode@4
%endmacro

section emitcode text align=1

emitCode@4:
	; al = snip ID
	; edi = dest
	push esi

	movzx eax, al
	mov eax, [_snipoffs+eax]
	sub ah, al
	movzx ecx, ah
	movzx eax, al
	lea esi, [_snips+eax]
	rep movsb
	mov eax, [esp+8]
	add dword [edi-4], eax

	pop esi
	ret 4

%define NUMTICKSlog 12
%define NUMTICKS (1<<NUMTICKSlog)
%define NUMTRACKS 12

%define FIRSTNOTE -256

section half data align=4
_half: dd 0.5

section sclparam data align=4
_param_scales:
times 2 dd  0x40c90fdb	;2pi Rotate		1.0 is a full revolution
times 2 dd	0x3f800000	;1   Scale
times 2 dd	0x3f800000	;1   Translate
;dd  0x437f0000	;255 Primitive color

section realdata data align=4
_rand_scale: dd 0.000030517578125	;1/32768

section jumptab bss align=64
_jump_locations:
.align16
	resd 256

section treecod bss align=64
_innertreecode:
.align16
	resb 1000000

section treecode text align=1
_treecode:
	pusha
	mov [_nodecount], dword 0
	mov [_subexpcount], dword 0
	call _innertreecode
	popa
	ret

	; Zero-operand operations
snip random
	mov eax, dword [_constantPool+4]
	imul eax, 16307
	add eax, byte 17
	mov [_constantPool+4], eax
	shr eax, 14
	push eax
	fild word [esp]
	fmul dword [_rand_scale]
	pop eax

	; One-operand operations
snip mat
	push eax
	fistp dword [esp]
	pop ebp
	comcall	dword [comhandle(matrix_stack)], GetTop
	fld dword [eax + ebp*4]
snip sin
	fmul	dword [_param_scales+0*4]
	fsin
snip clamp
	fldz
	fcomi st0, st1
	fcmovb st0, st1 ; move original value if greater than 0
	fstp st1
snip round
	frndint
snip abs
	fabs
snip log
	fld1
	fxch st1
	fyl2x
snip exp
	fld1
	fld st1
	fprem
	fstp st1
	f2xm1
	fld1
	faddp st1
	fscale
	fstp st1

	; Two-operand operations
snip add
	faddp st1
snip sub
	fsubp st1
snip mul
	fmulp st1
snip div
	fdivp st1
snip mod
	fprem
	fstp st1
snip noteat
	fld st0
	fimul dword [_timerFac]
	fsub dword [_half]
	push eax
	fistp dword [esp]
	pop ebp
	fxch st0,st1
	push eax
	fistp dword [esp]
	pop eax

	mov edx, [_channelFac]
	shl ebp, byte 2
	cmp ebp, edx
	jl .noteat_before_end
	mov ebp, edx
	sub ebp, byte 4
.noteat_before_end:
	mul edx
	add eax, ebp
	cmp eax, 5000000*4
	jge .oor_noteat
	fsub dword [_channelDeltas+eax]
.oor_noteat:

snip mov_ebx
	mov ebx, 0
snip fld_const
	fld dword [_constantPool]
snip fstp_const
	fstp dword [_constantPool]
snip pop_const
	pop dword [_constantPool]
snip push_const
	push dword [_constantPool]
snip pushfloat
	fmul dword [_param_scales+ebx*4]
	push eax
	fstp dword [esp]
snip store_index
	fistp dword [esp+4*4]

;snip matrix_push
;	comcall dword [comhandle(matrix_stack)], Push
snip matrix_pop
	comcall dword [comhandle(matrix_stack)], Pop
snip repeat1
	dec word [dword 0]
snip repeat3
	inc word [dword 0]
snip repeat2
	jz .recur_end
	call [_jump_locations]
.recur_end:
snip call
	; Call opcode and relative target adjustment
	db 0xe8
	dd (_snip_call-_snip_conditional)
snip conditional
	fldz
	fcomip st0,st1
	cmova eax, ebx
	fstp st0
	movzx eax, al
	call [_jump_locations+eax*4]
snip end


section compexp text align=1

compileExp:
	inc dword [_subexpcount]
	xor eax, eax
	lodsb
	cmp al, 0xF0
	jae .not_constant
		shl eax, 2
		push eax
		emit fld_const
		ret
.not_constant:
	sub al, 0xF0
	je .emit

	push eax
	call compileExp
	pop eax

	cmp al, _snip_id_add
	jb .emit

	push eax
	call compileExp
	pop eax
.emit:
	push byte 0
	call emitCode@4
	ret


section comptree text align=1

_compileTree@4:
	;int3
	pusha

	mov esi, [esp+9*4]
	mov edi, _innertreecode

	mov ebx, _jump_locations

.sectionloop:
	cmp byte [esi], 0xff
	jne .not_label
	inc esi
	jmp .sectionloop
.not_label:
	cmp byte [esi], 0xfe
	je .end

	mov [_nodecount], dword 0
	mov [_subexpcount], dword 0

	call compileNode

	mov ax, 0x0581 ; add dword [address], imm32
	stosw
	mov eax, _nodecount
	stosd
	mov eax, [_nodecount]
	stosd

	mov ax, 0x0581 ; add dword [address], imm32
	stosw
	mov eax, _subexpcount
	stosd
	mov eax, [_subexpcount]
	stosd

	; emit ret
	mov al, 0xc3
	stosb
	; mark label
	mov [ebx], edi
	add ebx, byte 4

	jmp .sectionloop
.end:
	popa
	ret 4

section compnode text align=1

compileNode:
	inc dword [_nodecount]
	xor eax, eax
	lodsb

	dec eax
	jnz .not_fanout
	;; ----------------
	;; fanout
	;; ----------------
	;emb "fanout"
	.fanout_loop:
		call compileNode
		cmp byte [esi], byte 0
		jg .fanout_loop
	lodsb
	ret
.not_fanout:

	dec eax
	jnz .not_savetrans
	;; ----------------
	;; fix
	;; ----------------
	;emb "fix"
	push byte (cc_Push-cc_Pop)*4
	emit matrix_pop
	call compileNode
	push byte 0
	emit matrix_pop
	ret
.not_savetrans:

	dec eax
	jnz .not_repeat
	;; ----------------
	;; repeat/call
	;; ----------------
	;emb "repeat"
	lodsb
	shl eax, 2
	push eax
	push esi
	emit repeat1
	emit repeat2
	push esi
	lodsb
	lodsb
	emit repeat3
	ret
.not_repeat:

	dec eax
	jnz .not_primitive
	;; ----------------
	;; primitive
	;; ----------------
	;;emb "primitive"
	; push byte
	mov al, 0x6a
	stosb
	movsb

	push byte 2
	emit mov_ebx
	call compileExp
	push byte 0
	emit pushfloat
	call compileExp
	push byte 0
	emit pushfloat
	call compileExp
	push byte 0
	emit pushfloat
	call compileExp
	push byte 0
	emit pushfloat

	mov eax, _drawprimitive@20
	sub eax, edi
	push eax
	emit call
	ret
.not_primitive:

	dec eax
	jnz .not_dynamic_primitive
	;; ----------------
	;; dynamic primitive
	;; ----------------
	;;emb "dynamic primitive"
	; push dummy (eax)
	mov al, 0x50
	stosb

	push byte 2
	emit mov_ebx
	call compileExp
	push byte 0
	emit pushfloat
	call compileExp
	push byte 0
	emit pushfloat
	call compileExp
	push byte 0
	emit pushfloat
	call compileExp
	push byte 0
	emit pushfloat
	call compileExp
	push byte 0
	emit store_index

	mov eax, _drawprimitive@20
	sub eax, edi
	push eax
	emit call
	ret
.not_dynamic_primitive:

	dec eax
	jnz .not_light
	;; ----------------
	;; light
	;; ----------------
	;;emb "light"
	; push byte
	mov al, 0x6a
	stosb
	movsb

	push byte 2
	emit mov_ebx
	call compileExp
	push byte 0
	emit pushfloat
	call compileExp
	push byte 0
	emit pushfloat
	call compileExp
	push byte 0
	emit pushfloat
	call compileExp
	push byte 0
	emit pushfloat

	mov eax, _placelight@20
	sub eax, edi
	push eax
	emit call
	ret
.not_light:

	dec eax
	jnz .not_camera
	;; ----------------
	;; camera
	;; ----------------
	;;emb "camera"
	mov eax, _placecamera@0
	sub eax, edi
	push eax
	emit call
	ret
.not_camera:

	dec eax
	jnz .not_assign
	;; ----------------
	;; assignment
	;; ----------------
	;emb "assign"
	call compileExp
	xor eax, eax
	lodsb
	shl eax, 2
	push eax
	emit fstp_const
	call compileNode
	ret
.not_assign:

	dec eax
	jnz .not_local_assign
	;; ----------------
	;; local assignment
	;; ----------------
	;emb "localassign"
	call compileExp
	xor eax, eax
	lodsb
	shl eax, 2
	push eax
	push eax
	push eax
	emit push_const
	emit fstp_const

	call compileNode

	emit pop_const
	ret
.not_local_assign:

	dec eax
	jnz .not_conditional
	;; ----------------
	;; conditional
	;; ----------------
	;emb "conditional"
	call compileExp

	; mov bl, label
	mov al, 0xb3
	stosb
	movsb

	; mov al, label
	mov al, 0xb0
	stosb
	movsb

	push byte 0
	emit conditional
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
	;emb "transform"

	dec eax

	lea ecx, [(cc_Rotate-cc_Pop)*4 + eax*4]
	push ecx

	push eax
	emit mov_ebx

	call compileExp
	push byte 0
	emit pushfloat
	call compileExp
	push byte 0
	emit pushfloat
	call compileExp
	push byte 0
	emit pushfloat

	emit matrix_pop
	call compileNode
	ret
