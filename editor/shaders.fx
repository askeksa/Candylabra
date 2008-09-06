sampler t;
float4x4 proj;
float4 color = float4(1,1,1,1);
float nstr = 1;

struct S {
	float4 p : POSITION;	//p: pos
	float3 p2 : TEXCOORD0;	//p2: pos
	float3 n : TEXCOORD1;	//n: normal
};

S v1(float4 p : POSITION, float3 n : NORMAL) {
	S x = {
		mul(proj, p),
		p.xyz,
		n,
	};
	return x;
}

float4 p1(S x): COLOR {
	return color * nstr;//lerp(1.0,float4(x.n,1),nstr);
}

technique
{
	pass
	{
		VertexShader = compile vs_2_0 v1();
		PixelShader = compile ps_2_0 p1();
	}
}
