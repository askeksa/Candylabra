#define ITERATIONS 10
#define GRADIENT (1.0/64)
#define SHADOW_SAMPLES 5
#define N_LIGHTS 2

float4x4 m,vp,facep;
float3 campos;

float3 lightpos[N_LIGHTS];
float4 lightcol[N_LIGHTS];
float4 color = float4(1,1,1,1);

float detailfac = 1;
float detailstr = 1;

texture _tex;
texture _detailtex;
texture _randomtex;
texture _cubetex0;
texture _cubetex1;

sampler3D tex = sampler_state { MagFilter = Linear; Texture = <_tex>; };
sampler3D detailtex = sampler_state { MagFilter = Linear; Texture = <_detailtex>; };
sampler3D randomtex = sampler_state { Texture = <_randomtex>; };
samplerCUBE cubetex[N_LIGHTS] = {
	sampler_state { Texture = <_cubetex0>; },
	sampler_state { Texture = <_cubetex1>; },
};


float4 r(float3 p : POSITION, float s : PSIZE) : COLOR0
{
	return frac(noise(p*100)*100);
}


float4 t0(float3 p : POSITION, float s : PSIZE) : COLOR0
{
	float3 r = p-0.5;
	return noise(normalize(r)*2) + noise(p*7) - 2.0 + dot(r,r)*20;
}

float4 dt0(float3 p : POSITION, float s : PSIZE) : COLOR0
{
	return 0.5 + 0.5 * noise(sin(p*2*3.1415926535)*float3(7,1,7));
}

float4 t1(float3 p : POSITION, float s : PSIZE) : COLOR0
{
	float3 r = p-0.5;
	return noise(normalize(r)*2)*0.2 + 0.05/length(r) - 0.4;
}


float shadow(float3 v) {
	return saturate((texCUBE(cubetex[0], v).r - length(v))*100+1);
}

float random(float3 v) {
	return tex3D(randomtex, v*2373).r;
}


struct S {
	float4 p : POSITION; //pos
	float3 v : TEXCOORD0; //wordspace pos
	float3 t : TEXCOORD1; //texture coord
};

S v(float4 p : POSITION) {
	float4 tp = mul(m,p);
	S s = {mul(vp, tp), tp.xyz, p.xyz+0.5};
	return s;
}

float objtex(float3 p)
{
	return tex3D(tex, p).r + tex3D(detailtex, p*detailfac) * detailstr;
}

float grad(float3 p, float3 g)
{
	return objtex(p-g*GRADIENT)-objtex(p+g*GRADIENT);
}

float4 p(S s) : COLOR0 {
	//return tex3D(tex,s.t);

	float3 cam = campos-s.v;
	float3 texcoord = s.t;
	float3 normal = float3(grad(texcoord,float3(1,0,0)),grad(texcoord,float3(0,1,0)),grad(texcoord,float3(0,0,1)));
	float nl = length(normal);
	//return 0.3-nl*0.2;
	normal = normalize(mul(m,float4(normal,0)));

	float4 color = 0;
	for (int l = 0 ; l < N_LIGHTS ; l++)
	{
		float3 lightv = s.v - lightpos[l];
		float3 refl = normalize(reflect(lightv, normal));
		float spec = pow(dot(refl,normalize(cam)), 20.0);
		float light = saturate(-dot(normalize(lightv),normal));
		float atten = 1.0f/sqrt(length(lightv));
		float fog = 1;//exp(length(cam)*-0.05);

		float pshadow = 0;
		float a = random(lightv)*17;
		for (int j = 0 ; j < SHADOW_SAMPLES ; j++)
		{
			float3 dir = float3(sin(a*3),sin(a*5),sin(a*7));
			pshadow += shadow(lightv + normalize(dir)*0.005) / SHADOW_SAMPLES;
			a += 1;
		}
		pshadow = 1;

		float vl = 0;
		float3 lstep = cam/ITERATIONS;
		float3 lcoord = lightv+random(lightv)*lstep;
		for (int i = 0 ; i < ITERATIONS ; i++) {
			vl += shadow(lcoord)/length(lcoord);
			lcoord += lstep;
		}

		color += lightcol[l] * (((0.01+pshadow*(light + spec))*atten)*fog + vl*length(cam)*lightcol[l].a);
	}
	return color/sqrt(length(color.rgb));
}

float4 dummyp(S s) : COLOR0 {
	return 0;
}

struct cube_s {
	float4 p : POSITION;
	float3 v : TEXCOORD0;
};

cube_s cube_v(float4 p : POSITION, uniform int index) {
	cube_s s;
	p = mul(m,p);
	s.p = mul(facep, float4(p.xyz-lightpos[index],1));
	s.v = p.xyz-lightpos[index];
	return s;
}

float4 cube_p(cube_s s) : COLOR0 {
	return length(s.v);
}

technique {
	pass {
		VertexShader = compile vs_3_0 cube_v(0);
		PixelShader = compile ps_3_0 cube_p();
	}

	pass {
		VertexShader = compile vs_3_0 cube_v(1);
		PixelShader = compile ps_3_0 cube_p();
	}

	pass {
		VertexShader = compile vs_3_0 v();
		PixelShader = compile ps_3_0 p();
	}

	pass {
		VertexShader = compile vs_3_0 v();
		PixelShader = compile ps_3_0 dummyp();
	}
}
