float4x4 m,o;

//float b,a;
float w,h;

sampler tex;

struct S {
	float4 p : POSITION;
	float4 c : COLOR;
	float2 o : TEXCOORD0;
};

S v(float3 p : POSITION, float sqs : TEXCOORD0, float4 c : TEXCOORD1, float2 o : TEXCOORD2) {
	p.xy += sqrt(sqs)*o;
	float4 t = p.xyzz * float4(1,1.78125,0,1);
	S s = {t,c,o};
	return s;
}

float4 p(S s) : COLOR {
	float d = dot(s.o,s.o);
	return float4(s.c.xyz, s.c.a * exp2(-d*24+2));
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
/*
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
*/

technique {
	pass {
		AlphaBlendEnable = true;
		AlphaTestEnable = false;
		SrcBlend = SRCALPHA;
		DestBlend = INVSRCALPHA;
		ZEnable = false;
		//ZWriteEnable = false;
		VertexShader = compile vs_2_0 v();
		PixelShader = compile ps_2_0 p();
	}
/*
	pass {
		AlphaBlendEnable = true;
		AlphaTestEnable = false;
		SrcBlend = ONE;
		DestBlend = ONE;
		//ZWriteEnable = false;
		VertexShader = compile vs_2_0 v();
		PixelShader = compile ps_2_0 p();
	}
*/
	pass {
		AlphaBlendEnable = false;
		AlphaTestEnable = false;
		//ZWriteEnable = true;
		VertexShader = compile vs_2_0 ppv();
		PixelShader = compile ps_2_0 ppp();
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
		PixelShader = compile ps_2_0 ppp();
	}
}
