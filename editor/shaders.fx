float4x4 m;

float4 c = float4(1,1,1,1);

float spec;

sampler tex;

struct S {
	float4 p : POSITION; //pos
	float3 v : TEXCOORD0; //screenspace pos
	float3 n : TEXCOORD1; //normal
};

S v(float4 p : POSITION, float3 n : NORMAL) {
	float4 tp = mul(m,p);
	S s = {tp, tp.xyz/tp.w, mul((float3x3)m,n)};
	return s;
}

float4 p(S s) : COLOR0 {
	float3 n = normalize(s.n);
	float l = 0.2 + 0.8*saturate(-n.z);
	return c*l + spec*(1-c)*pow(l,8);
}

void ppv(float4 p : POSITION, float2 tc : TEXCOORD0, out float4 tp : POSITION, out float2 ttc : TEXCOORD0) {
	tp = p;
	ttc = tc;
}

float4 ppp(float2 tc : TEXCOORD0) : COLOR0 {
	float4 s = 0;
	int i;
	for (i = 1 ; i < 20 ; i+=2)
	{
		s += tex2D(tex, tc+0.0002*i*float2(3*cos(i),4*sin(i)));
	}
	return float4((tex2D(tex, tc)/*2-s*0.1*/).xyz,1);
}


technique {
	pass {
		VertexShader = compile vs_2_0 v();
		PixelShader = compile ps_2_0 p();
	}

	pass {
		VertexShader = compile vs_2_0 ppv();
		PixelShader = compile ps_2_0 ppp();
	}
}
