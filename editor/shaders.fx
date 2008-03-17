sampler t;
float4 w : register(c0);
float4 w2 : register(c1);
float4 w3 : register(c2);
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
		float4(1,1,1,1),
	};
	return x;
}

float4 f2(S x): COLOR {
	float2 y=((x.n.xy*float2(1,-1)+1)/2).yx+float2(1.0f/1024,1.0f/1024);
	return (tex2D(t, y)*2 + tex2D(t, y+w) + tex2D(t, y-w))/4;
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
	x.p2.z *= w2.x;
	float3 v = normalize(x.p2);
	float i = 1+dot(x.n, v);
	return float4(((i*w2.y+w2.z)*(x.c+pow(i, w2.w)*0.5f)).rgb, x.c.a);
}

float4 f5(S x): COLOR {
	float2 y=((x.n.xy*float2(1,-1)+1)/2).yx+float2(1.0f/1024,1.0f/1024);
	float4 c = tex2D(t, y);
	return c*c.a*10;
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
}
