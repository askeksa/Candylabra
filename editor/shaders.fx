sampler t;
float4 glow : register(c0);
float4 shad : register(c1);
float4 misc : register(c2);
float4x4 proj : register(c0);

struct S {
	float4 p : POSITION;	//p: pos
	float3 p2 : TEXCOORD0;	//p2: pos
	float3 n : TEXCOORD1;	//n: normal
	float4 c : COLOR;		//c: vertex color
};

S f1(float4 p : POSITION) {	//vs_pp
	S x = {
		p,
		p.xyz,
		p.xyz,
		p,
	};
	return x;
}

float4 f2(S x): COLOR {
	float2 y=((x.n.xy*float2(1,-1)+1)/2).yx+float2(1.0f/1024,1.0f/1024);
	return (tex2D(t, y)*2 + tex2D(t, y+glow) + tex2D(t, y-glow))*misc.y;
}

S f3(float4 p : POSITION, float3 n : NORMAL, float4 c : COLOR) {
	S x = {
		mul(proj, p),
		p.xyz,
		normalize(n),
		c
	};
	return x;
}

float4 f4(S x): COLOR {
	x.p2.z *= shad.x;
	float i = 1+dot(x.n, normalize(x.p2));
	return float4(((i*shad.y+shad.z)*x.c+pow(i, shad.w)*misc.x).rgb, x.c.a);
}

float4 f5(S x): COLOR {
	float2 y=((x.n.xy*float2(1,-1)+1)/2).yx+float2(1.0f/1024,1.0f/1024);
	float4 c = tex2D(t, y);
	return c*c.a*2;
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
	
	pass
	{
		VertexShader = compile vs_2_0 f1();
		PixelShader = compile ps_2_0 f5();
	}
	
	pass
	{
		VertexShader = compile vs_2_0 f3();
		PixelShader = null;
	}
}
