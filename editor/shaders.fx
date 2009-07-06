float4x4 m;

float4 c = float4(1,1,1,1);

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
	return c*l + (1-c)*pow(l,8);
}

technique {
	pass {
		VertexShader = compile vs_3_0 v();
		PixelShader = compile ps_3_0 p();
	}
}
