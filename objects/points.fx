float4x4 m,o;

float b,a;
float w,h;

sampler tex;

struct S {
	float4 p : POSITION;
	float s : PSIZE;
	float4 c : COLOR;
};

S v(float4 p : POSITION, float size : TEXCOORD0, float4 c : TEXCOORD1) {
	float4 t = mul(o,p);
	S s = {t,h*size/t.w,c};
	return s;
}

float4 p(S s, float2 c : TEXCOORD0) : COLOR {
	//float l = saturate(-0.8*dot(normalize(s.n),normalize(s.s)));
	//return float4((c*l + spec*pow(l,10)).xyz,c.a);
	float2 cc = c-0.5;
	return dot(cc,cc) < 0.25 ? s.c : 0;
}

void ppv(float4 p : POSITION, float2 tc : TEXCOORD0, out float4 tp : POSITION, out float2 ttc : TEXCOORD0) {
	tp = p;
	ttc = tc;
}

float4 ppp(float2 tc : TEXCOORD0) : COLOR0 {
	float4 t = tex2D(tex, tc);
	return t;
}

float4 pp1p(float2 tc : TEXCOORD0) : COLOR0 {
	float4 s = 0;
	for (float i = -6.5 ; i <= 6.5 ; i+=1) {
		float4 t = tex2D(tex, tc+float2(i*0.0018,0));
		t.rgb *= t.a;
		s += t * 0.17 * exp(-i*i*0.1);
	}
	return s;
}

float4 pp2p(float2 tc : TEXCOORD0) : COLOR0 {
	float4 s = 0;
	for (float i = -6.5 ; i <= 6.5 ; i+=1) {
		float4 t = tex2D(tex, tc+float2(0,i*0.0032));
		s += t * 0.17 * exp(-i*i*0.1);
	}
	s.xyz *= b;
	s.a *= a;
	return s;
}


technique {
	pass {
		AlphaBlendEnable = false;
		AlphaTestEnable = true;
		POINTSPRITEENABLE = true;
		VertexShader = compile vs_2_0 v();
		PixelShader = compile ps_2_0 p();
	}

	pass {
		AlphaBlendEnable = true;
		SrcBlend = ONE;
		DestBlend = ONE;
		VertexShader = compile vs_2_0 v();
		PixelShader = compile ps_2_0 p();
	}

	pass {
		AlphaBlendEnable = false;
		AlphaTestEnable = false;
		VertexShader = compile vs_2_0 ppv();
		PixelShader = compile ps_2_0 pp1p();
	}

	pass {
		VertexShader = compile vs_2_0 ppv();
		PixelShader = compile ps_2_0 ppp();
	}

	pass {
		AlphaBlendEnable = true;
		SrcBlend = SRCALPHA;
		DestBlend = INVSRCALPHA;
		VertexShader = compile vs_2_0 ppv();
		PixelShader = compile ps_2_0 pp2p();
	}
}
