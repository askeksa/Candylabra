float4x4 m,o;

float spec= .9, // specular styrke
tabs = 15, // punkter i filter
size=1, // radius af filter 
add=.1, // positiv: vægt af bloom, negativ: vægt af outlines
sa, //sinescroll amp
sp, // sinescoll phase (tid)
md=50, // back color dist
dz=1; // z part of "view direction"

sampler tex
{
Filter = point;
addressu = clamp;
addressv = clamp;
};

void v(float4 pi : POSITION, out float4 po : POSITION, out float4 p : TEXCOORD0) {
	pi.y+= sin(pi.x+sp)*sa;
	p = mul(m,pi);
	po = mul(o,p); 
}
void pv(float4 p : POSITION, float2 tc : TEXCOORD0, out float4 tp : POSITION, out float2 ttc : TEXCOORD0) 
{
	tp = p;
	ttc = tc;
}
float4 p(float4 tc : TEXCOORD0) : COLOR0 
{
   return float4(normalize(cross(ddx(tc),ddy(tc))).xy*.5+.5, frac(tc.z), floor(tc.z)/256);
}   


float4 snz(float2 p)
{ float4 x=tex2Dgrad(tex,p,0,0);
  x.w = (x.w*256+x.z);
  x.xy=x.xy*2-1;
  x.z=sqrt(1-dot(x.xy,x.xy));
  return x;
}
float4 sh(float2 tc, float4 n)
{   
  float3 d= float3(.5-tc.xy,dz),
  l= saturate(.8*dot(n.xyz,normalize(d)));
  return lerp(float4(.9,.6,.01,.01),0,min(1,length(d)*n.w/md)) *(1-l.x) + spec*l.x*pow(.2+l.x,10);
}

float4 pp(float2 tc : TEXCOORD0) : COLOR0 
{
   float4 nz = snz(tc), nz2,
          s = 0, bz=0, nd=0;
   for (float i=1; i < tabs; i++)
   {
      float a = i*4+dot(tc,nz.zw)*12;
      nz2= snz(tc+.0001*size*i*float2(3*cos(a),4*sin(a)));
      if (abs(nz.w-nz2.w)<.5) s += nz2;
      //bz+= (add<0) ? min(abs(nz.w-nz2.w),.5) : max(0,sh(tc,nz2)-.6); // bloom/zdist
      bz+= min(abs(nz.w-nz2.w),.5); // bloom/zdist
      if (dot(nz.xyz,nz2.xyz)<.6 || abs(nz.w-nz2.w)>.3) nd++;
   }
   s.xyz=normalize(s.xyz);
   
   if (tabs>8)
     //if (add<0)
	   return sh(tc,s)*saturate(2+bz*add);
     //else
     //  return sh(tc,s)+bz*add;
   
   tc= sin(tc*800);
   return step(.5,(nz.z+.3-tc.x*tc.y*.5))*(1-nd*.4);
   
}

technique {
	pass {
		AlphaTestEnable=FALSE;
		AlphaBlendEnable=FALSE;
		VertexShader = compile vs_3_0 v();
		PixelShader = compile ps_3_0 p();
	}

	pass {
		AlphaTestEnable=FALSE;
		VertexShader = compile vs_3_0 pv();
		PixelShader = compile ps_3_0 pp();
	}
}