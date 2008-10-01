#define ITERATIONS 10
#define GRADIENT (1.0/64)
#define SHADOW_SAMPLES 5
#define N_LIGHTS 2

float4x4 m,vp,facep;
float3 campos[1];

float3 lightpos[N_LIGHTS];
float4 lightcol[N_LIGHTS];
float4 color = float4(1,1,1,1);

float detailfac = 1;
float detailstr = 1;
float gradient = 0.01;
float spread = 0.01;
float shadowedge = 2.0;
float ambient = 0.1;
float lpow = -1.0;
float randomfac = 1;
float specexp = 20;

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

float objectsizes[5] = { 0, 0, 0, 300, 0 };
//float objectsizes[5] = { 20000, 10000, 0, 100, 0 };

float4 r(float3 p : POSITION, float s : PSIZE) : COLOR0
{
	return frac(noise(p*100)*100);
}


float4 t0(float3 p : POSITION, float s : PSIZE) : COLOR0
{
	float3 r = (p-0.5)*2;
	return 0.5 + (0.5 - length(r));
}

float4 dt0(float3 p : POSITION, float s : PSIZE) : COLOR0
{
	return (8+noise(sin(p*2*3.1415926535)*8)+noise(sin(p*2*3.1415926535)*4)+noise(sin(p*2*3.1415926535)*2))/8;
}

float4 t1(float3 p : POSITION, float s : PSIZE) : COLOR0
{
/*	float3 r = p-0.5;
	return noise(normalize(r)*2) + noise(p*7)*0.5 - 2.0 + dot(r,r)*20; */
	
	float3 r = (p-0.5)*2;
	return 1 - (1.2 + noise(p*15)*0.05 - length(r) - 0.025/length(r.xy)
	 - 0.025/length(r.xz) - 0.025/length(r.zy));
}

float4 dt1(float3 p : POSITION, float s : PSIZE) : COLOR0
{
	return (8+noise(sin(p*2*3.1415926535)*8)+noise(sin(p*2*3.1415926535)*4)+noise(sin(p*2*3.1415926535)*2))/8;
}

/* tunnel object */
float4 t2(float3 p : POSITION, float s : PSIZE) : COLOR0
{
	float3 r = (p-0.5)*2;
	float w = length(r)-0.3;
	return 0.4+10*w*w + noise(normalize(r)*2)*0.4;
}

float4 dt2(float3 p : POSITION, float s : PSIZE) : COLOR0
{
	return (8+noise(sin(p*2*3.1415926535)*8)+noise(sin(p*2*3.1415926535)*4)+noise(sin(p*2*3.1415926535)*2))/8;
}

/* low-poly rocks in tunnel */
float4 t3(float3 p : POSITION, float s : PSIZE) : COLOR0
{
	float3 r = p-0.5;
	return 0.9 - (noise(p*3)*0.15 + length(r));
}

float4 dt3(float3 p : POSITION, float s : PSIZE) : COLOR0
{
	return (8+noise(sin(p*2*3.1415926535)*8)+noise(sin(p*2*3.1415926535)*4)+noise(sin(p*2*3.1415926535)*2))/8;
}

float shadow(int index, float3 v) {
	return saturate((texCUBE(cubetex[index], v).r - length(v))*shadowedge+1);
}

float random(float3 v) {
	return tex3D(randomtex, v*2373).r*randomfac;
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
	return objtex(p-g*gradient)-objtex(p+g*gradient);
}

float4 p(S s) : COLOR0 {
	//return random(s.v);
	//return tex3D(tex,s.t);

	//return float4(lightpos[0],1);
	//return float4((s.v-lightpos[0])*0.01+0.5,1);
	//return campos[0].x + saturate(texCUBE(cubetex[0], s.v-lightpos[0]).r*0.04);

	float3 cam = campos[0]-s.v;
	float3 texcoord = s.t;
	float3 normal = float3(grad(texcoord,float3(1,0,0)),grad(texcoord,float3(0,1,0)),grad(texcoord,float3(0,0,1)));
	float nl = length(normal);
	//return 0.3-nl*0.2;
	normal = normalize(mul(m,float4(normal,0)));

	float3 result = 0;
	for (int l = 0 ; l < N_LIGHTS ; l++)
	{
		float3 lightv = s.v - lightpos[l];
		float3 refl = normalize(reflect(lightv, normal));
		float spec = saturate(1-nl*20)*pow(dot(refl,normalize(cam)), specexp);
		float light = saturate(-dot(normalize(lightv),normal));
		float atten = 10.0/length(lightv);
		float fog = exp(length(cam)*-0.02);
		float3 col = color.rgb * (1 + color.a * (tex3D(detailtex,texcoord*detailfac)-0.5));

		float pshadow = 0;
		float a = random(lightv)*17;
		for (int j = 0 ; j < SHADOW_SAMPLES ; j++)
		{
			float3 dir = float3(sin(a*3),sin(a*5),sin(a*7));
			pshadow += shadow(l, lightv + normalize(dir)*spread);
			a += 1;
		}
		pshadow /= SHADOW_SAMPLES;
		//pshadow = 1;

		float vl = 0;
		float3 lstep = cam/ITERATIONS;
		float3 lcoord = lightv+random(lightv)*lstep;
		for (int i = 0 ; i < ITERATIONS ; i++) {
			vl += shadow(l, lcoord) * pow(length(lcoord),lpow);
			lcoord += lstep;
		}
		vl /= ITERATIONS;
		//vl = 0;

		float3 lc = lightcol[l].rgb;
		result += lc * (((ambient+pshadow*(light * col + spec))*atten)*fog + vl*length(cam)*lightcol[l].a);
	}
	return float4(sqrt(result),1);
	return float4(result/sqrt(length(result)),1);
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
