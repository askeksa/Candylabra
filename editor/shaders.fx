sampler t;
float4 w;
float4x4 proj : register(c0);

struct S {
	float4 p : POSITION;	//p: pos
	float3 n : TEXCOORD0;	//n: normal
	float4 c : COLOR;		//c: vertex color
};

S f1(float4 p : POSITION) {	//vs_pp
	S x = {
		p,
		p.xyz,
		float4(1,1,1,1),
	};
	return x;
}

float4 f2(S x): COLOR {
	float2 y=((x.n.xy*float2(1,-1)+1)/2).yx+float2(1.0f/512,1.0f/512);
	return (tex2D(t, y)*2 + tex2D(t, y+w) + tex2D(t, y-w))*0.27;
}

S f3(float4 p : POSITION, float3 n : NORMAL, float4 c : COLOR) {
	S x = {
		mul(proj, p),
		n,
		c
	};
	return x;
}

float4 f4(S x): COLOR {
	return -x.n.z;
}

technique
{
	pass
	{
		VertexShader = compile vs_2_0 f1();
		PixelShader = compile ps_2_0 f2();
	}
	
	pass
	{
		VertexShader = compile vs_2_0 f3();
		PixelShader = compile ps_2_0 f4();
	}
}
