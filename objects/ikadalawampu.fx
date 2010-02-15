float4x4 m;

struct palette {
	int3 a,b,c,d;
};

palette palettes[3] = {
	0,0,0, 4,6,8, 9,4,2, 12,12,12,
	5,5,5, 11,6,8, 9,4,2, 15,15,15,
	0,0,0, 1,2,13, 1,9,1, 15,15,15
};

float4 c = float4(1,1,1,1);
float2 screensize = float2(320,200);

float p0,p1,pfade;

sampler tex;

struct S {
	float4 p : POSITION; //pos
	float2 s : TEXCOORD0; //parametric value
};

S v(float4 p : POSITION) {
	float4 t = mul(m,p);
	S s = {float4((t.xy)/(screensize*0.5),0.5,1.0),p.xy};
	return s;
}

float4 p(S s) : COLOR0 {
	float g = exp(-4.0*dot(s.s,s.s));
	float2 col = round(c.xy * g * 63)/63;
	return float4(col, 1.0/255.0, 1.0);
}

void ppv(float4 p : POSITION, out float4 tp : POSITION, out float2 ttc : TEXCOORD0) {
	tp = p;
	ttc = (p+1.0)*0.5;
}

float4 ppp(float2 tc : TEXCOORD0) : COLOR0 {
	//return float4(frac(tc*10.0),0,1);
	float2 coli = tex2D(tex, tc).xy;
	int2 pixelcoord = floor(tc*screensize);
	float2 dither = frac(pixelcoord*0.5);
	float ditherval = abs(dither.x-dither.y)+dither.y*0.5;
	//coli = floor(coli*15+ditherval)/15;
	palette pal0 = palettes[int(p0)];
	palette pal1 = palettes[int(p1)];
	float3 a = lerp(pal0.a,pal1.a,pfade);
	float3 b = lerp(pal0.b,pal1.b,pfade);
	float3 c = lerp(pal0.c,pal1.c,pfade);
	float3 d = lerp(pal0.d,pal1.d,pfade);
	float3 col0 = lerp(a,b,coli.x);
	float3 col1 = lerp(c,d,coli.x);
	float3 col = lerp(col0,col1,coli.y)/15.0;

	return float4(col,1.0);
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
