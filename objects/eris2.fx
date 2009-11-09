//.Text
#define ITERATIONS 10

float4x4 m,vm,fvm;
float3 d;

float3 ld[2];
float4 lc[2];
float4 c = float4(1,1,1,1);

float ambi = 0;
float diff = 0;
float fade = 0;

texture _cubetex0;
texture _cubetex1;

samplerCUBE tc[2] = {
	sampler_state { Texture = <_cubetex0>; },
	sampler_state { Texture = <_cubetex1>; },
};

struct S {
	float4 p : POSITION; //pos
	float3 v : TEXCOORD0; //worldspace pos
	float3 t : TEXCOORD1; //objectspace pos
	float3 n : TEXCOORD2; //normal
};

S v(float4 p : POSITION, float3 n : NORMAL) {
	float4 tp = mul(m,p);
	S s = {mul(vm, tp), tp.xyz, p.xyz+0.5, n};
	return s;
}


float sh(int i, float3 p) {
	return saturate((texCUBE(tc[i], p).r - length(p))) / dot(p,p);
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
//		vl = 0;
		q += lc[i].rgb // light color
			*((
			((ambi + diff*saturate(-dot(n,normalize(lv)))) // amibient/diffuse light
			*c.rgb // surface color
			+c.a*pow(saturate(-dot(n,normalize(normalize(lv)-normalize(cam)))), 64) // specular
			))+
			  vl*length(cam)/ITERATIONS // volumetric light
			  *lc[i].a // volumetric light strength
			);
	}

	return float4(sqrt(q)*fade,1);
}




float4 dummyp(S s) : COLOR0 {
	return 0;
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

technique {
	pass {
		VertexShader = compile vs_2_0 cube_v(0);
		PixelShader = compile ps_2_0 cube_p();
	}

	pass {
		VertexShader = compile vs_2_0 cube_v(1);
		PixelShader = compile ps_2_0 cube_p();
	}

	pass {
		VertexShader = compile vs_2_0 v();
		PixelShader = compile ps_3_0 p();
	}

	pass {
		VertexShader = compile vs_2_0 v();
		PixelShader = compile ps_2_0 dummyp();
	}
}
