sampler t;
float4x4 m,vp;
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


S v1(float4 p : POSITION, float3 n : NORMAL) {
	float4 tp = mul(m,p);
	S x = {
		mul(vp, tp),
		p.xyz,
		mul(m,float4(n,0)).xyz
	};
	return x;
}

float4 p1(S x): COLOR {
	return color;
}

technique
{
	pass
	{
		VertexShader = compile vs_2_0 v1();
		PixelShader = compile ps_2_0 p1();
	}
}
