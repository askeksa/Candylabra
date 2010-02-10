//.     KEEBOARDERS   LOONEES @ KEENDERGARDEN09 
#define ITERATIONS 10

float4x4 m,vm,fvm;
float3 d;

float3 ld[2];
float4 lc[2];
float4 c = float4(1,1,1,1);

float fade = 0;

sampler tex;

texture _cubetex0;
texture _cubetex1;

samplerCUBE tc[2] = {
	sampler_state { Texture = <_cubetex0>; },
	sampler_state { Texture = <_cubetex1>; },
};


struct S {
	float4 p : POSITION;
	float3 v : TEXCOORD0;
	float3 t : TEXCOORD1;
	float3 n : TEXCOORD2;
};

S v(float4 p : POSITION, float3 n : NORMAL) {
	float4 tp = mul(m,p);
	S s = {mul(vm, tp), tp.xyz, p.xyz+0.5, n};
	return s;
}



float sh(int i, float3 p) {
	return max(0, texCUBE(tc[i], p).r - length(p)) / dot(p,p);
}

float z(float3 p) {
	return frac(length(p)*2373);
}


float4 p(S s) : COLOR0 {
	float3 cam = d-s.v;
	float3 n = normalize(s.n);

	float3 q = 0;
	for (int i = 0 ; i < 2 ; i++)
	{
		float3 lv = s.v - ld[i];

		float3 ls = cam/ITERATIONS;
		float3 ll = lv+z(lv)*ls-ls;
		float vl = 0;
		for (int j = 0 ; j < ITERATIONS ; j++) {
			vl += sh(i, ll += ls);
		}
		q += lc[i].rgb
			*(
			  c.a*pow(max(0, -dot(n,normalize(normalize(lv)-normalize(cam)))), 64)
			  +
			  vl*length(cam)/ITERATIONS
			  *lc[i].a
			);
	}

	return float4(q,1);
}



struct T {
	float4 p : POSITION;
	float3 v : TEXCOORD0;
};

T cube_v(float4 p : POSITION, uniform int i) {
	T s;
	p = mul(m,p);
	s.p = mul(fvm, float4(p.xyz-ld[i],1));
	s.v = p.xyz-ld[i];
	return s;
}

float4 cube_p(T s) : COLOR0 {
	return length(s.v);
}

void ppv(float4 p : POSITION, float2 tc : TEXCOORD0, out float4 tp : POSITION, out float2 ttc : TEXCOORD0) {
	tp = p;
	ttc = tc;
}
float4 ppp(float2 tc : TEXCOORD0) : COLOR0 {
	float3 r=tex2D(tex, tc).xyz;
	for (int i=1; i<16; i++)
	{
		float4 t=log2(i*1.28);
		t.xy = tc + float2(sin(i*2)*i*0.001f, cos(i*2)*i*.0013f);
		r += tex2Dlod(tex, t).xyz/float(i);
	}
	return float4(r*fade,1);
}

technique {
	pass {
		VertexShader = compile vs_3_0 cube_v(0);
		PixelShader = compile ps_3_0 cube_p();
	}

	pass {
		VertexShader = compile vs_3_0 cube_v(1);
		PixelShader = compile ps_3_0 cube_p();
	}

	pass {
		VertexShader = compile vs_3_0 v();
		PixelShader = compile ps_3_0 p();
	}

	pass {
		VertexShader = compile vs_3_0 ppv();
		PixelShader = compile ps_3_0 ppp();
	}
}
