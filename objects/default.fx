float4x4 m,o;

float4 c = float4(1,1,1,1);

float spec;
float blur;

sampler tex;

struct S {
	float4 p : POSITION; //pos
	float4 s : TEXCOORD0; //screenspace pos
	float3 n : TEXCOORD1; //normal
	float f : TEXCOORD2;
};

S v(float4 p : POSITION, float3 n : NORMAL) {
	float4 t = mul(m,p);
	S s = {mul(o,t), t, mul((float3x3)m,n), 1-0.01*abs(n.z)};
	return s;
}

float4 p(S s) : COLOR0 {
	float l = saturate(1.0 + 0.8*dot(normalize(s.n),normalize(s.s)));
	return float4((c*l + spec*(1-l)*float4(1,1,0.8,1)*pow(1.2-l,10)).xyz,c.a);
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
		float a = i*(3.14159265358979/4);
		s += tex2D(tex, tc+0.0001*i*float2(3*cos(a),4*sin(a)));
	}
	float4 t = tex2D(tex, tc);
	s /= 10;
	//return float4(t.xyz*(1-abs(s.a-t.a)*200),1);
	//return float4(t.xyz*(1-blur)+s.yzx*blur,1);
	return float4(t.xyz,1);
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
