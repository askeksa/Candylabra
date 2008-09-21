float4x4 fvm,vm,m;
float3 d;

float3 ld[2];
float4 lc[2];
float4 c;

float detailfac = 1;
float detailstr = 1;

texture _tex;
texture _detailtex;
texture _randomtex;
texture _cubetex0;
texture _cubetex1;

sampler3D to = sampler_state { MagFilter = Linear; Texture = <_tex>; };
sampler3D td = sampler_state { MagFilter = Linear; Texture = <_detailtex>; };
sampler3D tr = sampler_state { Texture = <_randomtex>; };
samplerCUBE tc[2] = {
	sampler_state { Texture = <_cubetex0>; },
	sampler_state { Texture = <_cubetex1>; },
};

struct S {
	float4 p : POSITION; //pos
	float3 v : TEXCOORD0; //wordspace pos
	float3 t : TEXCOORD1; //texture coord
};

S v(float4 p : POSITION) {
	float4 tp = mul(m,p);
	S s = {mul(vm, tp), tp.xyz, p.xyz+0.5};
	return s;
}




float objectsizes[5] = { 0, 0, 0, 200, 0 };
//float objectsizes[5] = { 20000, 10000, 0, 100, 0 };

float4 r(float3 p : POSITION) : COLOR0
{
	return frac(noise(p*100)*100);
}


float4 dt0(float3 p : POSITION) : COLOR0
{
	return (3+noise(sin(p*6.2832)*8)+noise(sin(p*6.2832)*4)+noise(sin(p*6.2832)*2))/6;
}
float4 dt1(float3 p : POSITION) : COLOR0
{
	return (3+noise(sin(p*6.2832)*8)+noise(sin(p*6.2832)*4)+noise(sin(p*6.2832)*2))/6;
}
float4 dt2(float3 p : POSITION) : COLOR0
{
	return (3+noise(sin(p*6.2832)*8)+noise(sin(p*6.2832)*4)+noise(sin(p*6.2832)*2))/6;
}
float4 dt3(float3 p : POSITION) : COLOR0
{
	return (3+noise(sin(p*6.2832)*8)+noise(sin(p*6.2832)*4)+noise(sin(p*6.2832)*2))/6;
}

float4 t0(float3 p : POSITION) : COLOR0
{
	float3 r = (p-0.5)*2;
	return 0.5 + (0.05 - length(r));
}
float4 t1(float3 p : POSITION) : COLOR0
{
	float3 r = (p-0.5)*2;
	return 1 - (1.2 + noise(p*15)*0.05 - length(r) - 0.025/length(r.xy)
	 - 0.025/length(r.xz) - 0.025/length(r.zy));
}



/* tunnel object */
float4 t2(float3 p : POSITION) : COLOR0
{
	float3 r = (p-0.5)*2;
	float w = length(r)-0.3;
	return 0.4+10*w*w + noise(normalize(r)*2)*0.4;
}



/* low-poly rocks in tunnel */
float4 t3(float3 p : POSITION) : COLOR0
{
	float3 r = p-0.5;
	return 0.9 - (noise(p*3)*0.15 + length(r));
}



float sh(int i, float3 p) {
	return saturate((texCUBE(tc[i], p).r - length(p))*8+1);
}

float z(float3 p) {
//	v=normalize(v);
//	return frac(v.x*v.y*v.z*999999)*2; // save the random texture
	return tex3D(tr, p*2373).r*2;
}


float o(float3 p)
{
	return (tex3D(to, p).r + tex3D(td, p*detailfac) * detailstr);
}

float g(float3 p, float3 g)
{
	return o(p-g/64)-o(p+g/64);
}

float4 p(S s) : COLOR0 {
	float3 cam = d-s.v;
	float3 n = normalize(mul(m,float4(g(s.t,float3(1,0,0)),g(s.t,float3(0,1,0)),g(s.t,float3(0,0,1)),0)));

	float3 q = 0;
	for (int i = 0 ; i < 2 ; i++)
	{
		float3 lv = s.v - ld[i];

		float3 ls = cam/10;
		float3 ll = lv+z(lv)*ls-ls;
		float vl = 
			sh(i, ll += ls) / dot(ll,ll)+
			sh(i, ll += ls) / dot(ll,ll)+
			sh(i, ll += ls) / dot(ll,ll)+
			sh(i, ll += ls) / dot(ll,ll)+
			sh(i, ll += ls) / dot(ll,ll)+
			sh(i, ll += ls) / dot(ll,ll)+
			sh(i, ll += ls) / dot(ll,ll)+
			sh(i, ll += ls) / dot(ll,ll)+
			sh(i, ll += ls) / dot(ll,ll)+
			sh(i, ll += ls) / dot(ll,ll);
	
		float a = z(lv)*17;
		q += lc[i].rgb // light color
			*((0.01 // ambient
			+(
			sh(i, lv + normalize(sin(a++*float3(3,5,7)))/2)+
			sh(i, lv + normalize(sin(a++*float3(3,5,7)))/2)+
			sh(i, lv + normalize(sin(a++*float3(3,5,7)))/2)+
			sh(i, lv + normalize(sin(a++*float3(3,5,7)))/2)+
			sh(i, lv + normalize(sin(a++*float3(3,5,7)))/2)
			) // shadow map on surface
			*(saturate(-dot(n,normalize(lv))) // diffuse light
			*c.rgb // surface color
			+c.a*pow(saturate(-dot(n,normalize(normalize(lv)-normalize(cam)))), 64) // specular
			))+vl*length(cam) // volumetric light
			*lc[i].a // volumetric light strength
			);
	}

	return float4(sqrt(q),1);
}






float4 b(S s) : COLOR0 {
	return 0;
}

struct T {
	float4 p : POSITION;
	float3 v : TEXCOORD0;
};

T cube_v(float4 p : POSITION, uniform int i) {
	p = mul(m,p);
	T s = {
		mul(fvm, float4(p.xyz-ld[i],1)),
		p.xyz-ld[i]
	};
	return s;
}

float4 cube_p(T s) : COLOR0 {
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
		PixelShader = compile ps_3_0 b();
	}
}
