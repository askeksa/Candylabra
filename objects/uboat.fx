/*

TODO:

+correct z test for particles
+unite caustics and shadow in a function
+determine light color by angle to sun
+multiplicative absoption in trace
+exponential absorption for objects
+specular
+trace starting color from absorption color and light color/direction
particle size variation?
particle intensity absorption
particles lit by sun rays?
+use background color

*/

float4x4 m,vp,ivp,sp; // model->world, world->clip, clip->world, world->shadow
float4 c,l;
float3 e,s;
float
	t, // time
	h, // specular strength
	b, // beam strength
	f; // trace step length

texture t0,t1,t2,t3;
sampler
	dt= sampler_state { MinFilter=Point; MagFilter = Point; Texture = <t1>; },
	ct= sampler_state { MinFilter=Point; MagFilter = Point; Texture = <t2>; },
	st= sampler_state { MagFilter = Point; Texture = <t0>; },
	lt= sampler_state { MagFilter = Point; Texture = <t3>; };

float4 hash(float3 p)
{
  //p = sin(p*float4(123,456,789,7913));
	//p.x += p.y * .57 + p.z * .21;
	//return frac(p.x * p.x * float4(13,117,1119,12345))-.5;
	p.x += p.y * 57 + p.z * 21;
  return frac(p.x * p.x * float4(.013,.01017,.0119,.0021));
}

float4 lp(float3 p) 
{
	float4 i = mul(sp,float4(p,1));
	i/=i.w;
	i.xy=i.xy*float2(.5,-.5)+.5;
	return i;	
}

float cau(float4 i) {
	float a=0,w;
	for (w=0;w<5;w++) {
		a += sin(dot(i.xy, float2(cos(w),sin(w)))*99 + t * (1 + w/7));
	}
	return 1 + a * .2;
}

float sh(float4 i) {
	return (any(i.xy<0 || i.xy>1)) ? 1 : step(i.z,tex2Dlod(st,float4(i.xy,0,0)).x);
}

//object
void v2(float4 pi : POSITION, out float4 po : POSITION, out float4 p : TEXCOORD0) {
	p = mul(m,pi);
	po = mul(vp,p); 
	//p = mul(sp,p); 
}

float4 p1(float4 tc : TEXCOORD0) : COLOR0 
{
	float3 n=-normalize(cross(ddx(tc.xyz),ddy(tc.xyz))); //world space normal
	return float4(
		// diffuse
		((dot(n,normalize(s))*.5+.5)*c.xyz +
		// specular
		h*pow(saturate(dot(n,normalize(normalize(s)+normalize(e-tc.xyz)))),20))
		// light
		* cau(lp(tc.xyz))*l
		// fog
		,length(tc-e)/16);
}   

//shadow
void v1(float4 pi : POSITION, out float4 po : POSITION, out float4 p : TEXCOORD0) {
	p = mul(m,pi);
	po = mul(sp,p); 
}
//genbrug af p1...
//float4 p2(float4 tc : TEXCOORD0) : COLOR0 
//{
//   return 1;
//}   

void v35(float4 pi : POSITION, out float4 po : POSITION, out float4 p : TEXCOORD0) {
	p = po = mul(m,pi); 
}

// trace
float4 p3(float4 tc : TEXCOORD0) : COLOR0 
{
	tc/=tc.w;
	float4 u,p = mul(ivp,float4(tc.xy,tex2D(dt,tc.xy*float2(.5,-.5)+.5).x,1));
	p/=p.w;
	float3 dir = e-p,a=0;
	float d= length(dir),i;
	dir/=d;
	if (d>10) {p.xyz= e-dir*10;d=10;}
	i=hash(sin(p*100)).x*f;
	while (i<d)
	{
		u = lp(p+i*dir);
		a += b*cau(u)*sh(u)*f*l.xyz*(2+dot(dir,normalize(s)));
		a *= pow(c, f);
		i += f;
	}
	return float4(a,0);
}  

// particles
void v4(float4 pi : POSITION, out float4 po : POSITION, out float4 p : TEXCOORD0) {
	p = hash(mul(m,pi).xyz);
	pi.x=p.w;
	p.xyz+=(sin(p.yzx*14+t*.5)+sin(p.zxy*9+t*.5))*.01; 
	p.x += h/10;
	//p.y+=t*.1;
	p = float4( fmod(p.xyz*10-e+1000,10) -5 + e ,1);
	pi.x *= cau(lp(p.xyz))*sh(lp(p.xyz));
	po = p = mul(vp, p);
	p.xyz/=p.w;
	p.w = pi.x;
	//p.w=0;
}

float4 p4(float4 tc : TEXCOORD0) : COLOR0 
{
	if (tex2D(dt,tc.xy*float2(.5,-.5)+.5).x < tc.z) discard;
	return float4(0,0,0,tc.w*(1-tc.z));
}

// blur
float4 p5(float4 tc : TEXCOORD0) : COLOR0 
{
	float2 o,u = tc.xy*float2(.5,-.5)/tc.w+.5;
	float w,ws=0;
	float4 a=0,cc;
				//,p = mul(ivp,float4(tc.xy,tex2D(dt,u).x,1));p/=p.w; 

	for (o.y=-4;o.y<=4;o.y++)
	for (o.x=-4;o.x<=4;o.x++)
	{ 
		cc = tex2D(lt,float2(u+ o/float2(800,480)));
		//cc-= cc.w;
		//cc.xyz += cc.w;
		w = 1./(1+dot(o,o));
		a+=  cc*w;
		ws += w;
	}
	a/=ws;
	a += b*a.w;

	cc = tex2D(ct,u);
	return (sqrt(cc*pow(c,cc.w*16) + a) - dot(tc.xy,tc.xy)*.2)*f;
}   

technique {
	pass {
		//ALPHATESTENABLE = 0;
		//ALPHABLENDENABLE = 0;
		VertexShader = compile vs_3_0 v1();
		PixelShader = compile ps_3_0 p1();
	}

	pass {
		VertexShader = compile vs_3_0 v2();
		PixelShader = compile ps_3_0 p1();
	}

	pass {
		VertexShader = compile vs_3_0 v35();
		PixelShader = compile ps_3_0 p3();
	}

	pass {
		//ALPHABLENDENABLE = 1;
		//SRCBLEND = ONE;
		//DESTBLEND = ONE;
		//POINTSPRITEENABLE = 0;
		//FillMode = POINT;
		VertexShader = compile vs_3_0 v4();
		PixelShader = compile ps_3_0 p4();
	}

	pass {
		//FillMode = SOLID;
		VertexShader = compile vs_3_0 v35();
		PixelShader = compile ps_3_0 p5();
	}
}
