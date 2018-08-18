float4x4 m;

float4 c = float4(1,1,1,1);

float2 tsize;

sampler tex;

struct S {
	float4 p : POSITION; //pos
	float2 t : TEXCOORD0; //texcoord
};

S v(float4 p : POSITION, float2 t : TEXCOORD0) {
	p.y *= tsize.y / tsize.x;
	float4 pos = mul(m,p);
	pos.xzw = float3(pos.x / (16.0/9.0), 1.0, pos.z);
	S s = {pos, t};
	return s;
}

float4 p(S s) : COLOR0 {
	float4 a = tex2D(tex, s.t);
	float3 b = 0;
	for (int i = 0; i < 3; i++) {
		b += a.rgb * (.5-cos((c.x + float(i)/3.0)*2.0*3.14159))/1.5;
		a.rgb = a.gbr;
	}
	a.rgb = b.rgb;
	float grey = (a.r + a.g + a.b) / 3.0;
	a.rgb = lerp(grey, a.rgb, c.y * 2.0);
	a.rgb *= c.z * 2.0;
	a.rgba *= c.a * 2.0;
	return a;
}

void ppv(float4 p : POSITION, float2 tc : TEXCOORD0, out float4 tp : POSITION, out float2 ttc : TEXCOORD0) {
	tp = p;
	ttc = tc;
}

float4 ppp(float2 tc : TEXCOORD0) : COLOR0 {
	return float4(tex2D(tex, tc).xyz,1);
}

technique {
	pass {
		AlphaBlendEnable=TRUE;
		SrcBlend=ONE;
		DestBlend=INVSRCALPHA;
		ZEnable=FALSE;
		CullMode=NONE;
		VertexShader = compile vs_2_0 v();
		PixelShader = compile ps_2_0 p();
	}

	pass {
		VertexShader = compile vs_2_0 ppv();
		PixelShader = compile ps_2_0 ppp();
	}
}
