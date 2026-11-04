// R02 candidate. Install into the existing Custom node only after baseline export.
// This file is NOT read by UE. No asset has been modified by creating it.
// World centimetres; two independently thinned candidates per cell.
float scatter=saturate(ArtistRandomness);
float cellSize=max(SpacingCm/sqrt(max(ArtistDensity,0.05)),8.0);
float radiusMax=min(max(RadiusCm*clamp(ArtistSize,0.25,2.0),1.0),cellSize*0.48);
float rate=clamp(Rate,0.2,3.0);
float2 p=WorldPos.xy;
float2 baseCell=floor(p/cellSize);
float footprint=max(length(ddx(p)),length(ddy(p)));
// All events have AA=0 beyond this bound. Evaluate derivatives BEFORE branching.
if(ArtistStrength<=0.0 || ArtistDensity<=0.0 || Density<=0.0 || footprint>=radiusMax*1.25)
    return float3(0,0,1);
float2 slope=float2(0,0);
[unroll] for(int iy=-1;iy<=1;iy++){
[unroll] for(int ix=-1;ix<=1;ix++){
 float2 cell=baseCell+float2(ix,iy);
 [unroll] for(int lane=0;lane<2;lane++){
  uint cellHash=(uint)((int)cell.x)*1597334677u ^ (uint)((int)cell.y)*3812015801u ^ (uint)lane*2798796415u;
  uint phaseHash=cellHash ^ 2246822519u;
  phaseHash^=phaseHash>>16; phaseHash*=2146121005u;
  phaseHash^=phaseHash>>15; phaseHash*=2221713035u; phaseHash^=phaseHash>>16;
  float phaseOffset=float(phaseHash & 0x00ffffffu)*(1.0/16777216.0);
  float clock=Seconds*clamp(ArtistSpeed,0.1,2.0)*rate+phaseOffset;
  float cycle=floor(clock);
  [unroll] for(int prev=0;prev<2;prev++){
   float eventIndex=cycle-prev;
   float age=(clock-eventIndex)/rate;
   uint eventHash=cellHash ^ (uint)((int)eventIndex)*3266489917u;
   uint3 hash=eventHash ^ uint3(2747636419u,668265263u,374761393u);
   hash^=hash>>16; hash*=2146121005u;
   hash^=hash>>15; hash*=2221713035u; hash^=hash>>16;
   float3 random=float3(hash & 0x00ffffffu)*(1.0/16777216.0);
   uint3 hash2=hash ^ uint3(1274126177u,42595009u,197830471u);
   hash2^=hash2>>16; hash2*=2146121005u;
   hash2^=hash2>>15; hash2*=2221713035u; hash2^=hash2>>16;
   float3 variation=float3(hash2 & 0x00ffffffu)*(1.0/16777216.0);
   float keepProbability=(lane==0)?(1.0-0.5*scatter):(0.5*scatter);
   float keep=(variation.x<keepProbability)?1.0:0.0;
   // Both lifetime branches must fit the two stored event periods.
   // Old code capped only the random branch, dropping live events when Rate>2.
   float lifetime=min(lerp(0.65+random.z*0.25,0.48+variation.y*0.42,scatter),1.95/rate);
   float phase=saturate(age/lifetime);
   float alive=step(age,lifetime)*step(random.z,saturate(Density))*keep;
   float2 offset=lerp(0.15+random.xy*0.7,0.02+random.xy*0.96,scatter);
   float2 center=(cell+offset)*cellSize;
   float2 delta=p-center;
   float d=max(length(delta),0.001);
   float eventRadius=radiusMax*lerp(1.0,0.6+variation.z*0.65,scatter);
   float radius=eventRadius*(0.12+0.88*phase);
   float width=max(1.0,footprint*0.6);
   float x=d-radius;
   float envelope=exp(-x*x/(width*width));
   float fade=smoothstep(0.0,0.12,phase)*(1.0-phase);
   float antialias=1.0-smoothstep(eventRadius*0.35,eventRadius,footprint);
   float derivative=(-2.0*x/(width*width))*envelope;
   float amplitude=lerp(1.0,0.55+variation.y*0.9,scatter);
   slope+=delta/d*derivative*0.18*amplitude*fade*alive*antialias;
  }
 }
}}
slope=clamp(slope*clamp(ArtistStrength,0.0,3.0),-0.18,0.18);
return normalize(float3(-slope,1.0));
