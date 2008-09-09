#define ITERATIONS 10
#define GRADIENT (1.0/64)
#define SHADOW_SAMPLES 5
#define N_LIGHTS 2

float4x4 m,vp,facep;
float3 campos;

float3 lightpos[N_LIGHTS];
float4 lightcol[N_LIGHTS];

sampler t;
float4 color = float4(1,1,1,1);

struct S {
	float4 p : POSITION;	//p: pos
	float3 p2 : TEXCOORD0;	//p2: pos
	float3 n : TEXCOORD1;	//n: normal
};

float4 t0(float3 p : POSITION, float s : PSIZE) : COLOR0
{
	float3 r = p-0.5;
	return noise(normalize(r)*2)*0.2 + 0.05/length(r) - 0.4;
}


float4 r(float3 p : POSITION, float s : PSIZE) : COLOR0
{
	return frac(noise(p*100)*100);
}


S v(float4 p : POSITION, float3 n : NORMAL) {
	float4 tp = mul(m,p);
	S x = {
		mul(vp, tp),
		p.xyz,
		mul(m,float4(n,0)).xyz
	};
	return x;
}

float4 p(S x): COLOR {
	return color*(lightcol[0]+lightcol[1]);
}

float4 dummyp(S s) : COLOR0 {
	return 0;
}

struct cube_s {
	float4 p : POSITION;
	float3 v : TEXCOORD0;
};

cube_s cube_v(float4 p : POSITION) {
	cube_s s;
	p = mul(m,p);
	s.p = mul(facep, float4((p.xyz-lightpos[0])*100,1));
	s.v = p.xyz-lightpos[0];
	return s;
}

float4 cube_p(cube_s s) : COLOR0 {
	return length(s.v);
}

technique {
	pass {
		VertexShader = compile vs_3_0 cube_v();
		PixelShader = compile ps_3_0 cube_p();
	}

	pass {
		VertexShader = compile vs_3_0 v();
		PixelShader = compile ps_3_0 p();
	}

	pass {
		VertexShader = compile vs_3_0 v();
		PixelShader = compile ps_3_0 dummyp();
	}
}
