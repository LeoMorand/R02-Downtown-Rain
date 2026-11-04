// R02 rain ripples on puddles. Install into the existing Custom node only after baseline export.
// This file is NOT read by UE at runtime. World centimetres in, tangent-space normal out.
// One jittered cell grid; each cell carries two independently thinned event lanes so the pattern
// does not read as one-hit-per-cell. Each lane keeps the current and previous event alive.
const float kMinCellCm=8;
const float kMaxRadiusInCell=.48;              // ring never leaves its own cell's 3x3 neighbourhood
const float2 kSizeRange=float2(.25,2.0), kSpeedRange=float2(.1,2.0);
const float2 kRateRange=float2(.2,3.0);        // events per second per lane
const float kMaxEventRadiusScale=1.25;         // upper bound of eventRadius/radiusMax below
const float kCullSigma=3;                      // Gaussian ring is < exp(-9) beyond 3 widths
const float kMinWidthCm=1, kWidthPerFootprint=.6;
const float kSlopeScale=.18, kSlopeLimit=.18;
const float kInv24=1.0/16777216.0;             // 24-bit hash -> [0,1)
const uint kHashMask=0x00ffffffu;
float scatter=saturate(ArtistRandomness);
float cellSize=max(SpacingCm/sqrt(max(ArtistDensity,0.05)),kMinCellCm);
float radiusMax=min(max(RadiusCm*clamp(ArtistSize,kSizeRange.x,kSizeRange.y),1.0),cellSize*kMaxRadiusInCell);
float rate=clamp(Rate,kRateRange.x,kRateRange.y);
float2 p=WorldPos.xy;
float2 baseCell=floor(p/cellSize);
float footprint=max(length(ddx(p)),length(ddy(p)));
// All events have AA=0 beyond this bound. Evaluate derivatives BEFORE branching.
if(ArtistStrength<=0.0 || ArtistDensity<=0.0 || Density<=0.0 || footprint>=radiusMax*1.25)
    return float3(0,0,1);
float width=max(kMinWidthCm,footprint*kWidthPerFootprint);
// Farthest a cell's events can reach this pixel: largest ring plus its Gaussian tail.
float reach=radiusMax*kMaxEventRadiusScale+kCullSigma*width;
float speed=clamp(ArtistSpeed,kSpeedRange.x,kSpeedRange.y)*rate;
float2 slope=float2(0,0);
[unroll] for(int iy=-1;iy<=1;iy++){
[unroll] for(int ix=-1;ix<=1;ix++){
 float2 cell=baseCell+float2(ix,iy);
 // Skip the whole cell when the pixel is outside every ring it could hold (corner cells, mostly).
 float2 cellMin=cell*cellSize;
 float2 outside=max(max(cellMin-p,p-(cellMin+cellSize)),0);
 [branch] if(dot(outside,outside)<reach*reach){
 [unroll] for(int lane=0;lane<2;lane++){
  // Lane 0 keeps 1-scatter/2 of its events, lane 1 keeps scatter/2: total density is constant.
  float keepProbability=(lane==0)?(1.0-0.5*scatter):(0.5*scatter);
  [branch] if(keepProbability>0){
  uint cellHash=(uint)((int)cell.x)*1597334677u ^ (uint)((int)cell.y)*3812015801u ^ (uint)lane*2798796415u;
  uint phaseHash=cellHash ^ 2246822519u;
  // lowbias32-style integer finaliser (shared by all hashes below).
  phaseHash^=phaseHash>>16; phaseHash*=2146121005u;
  phaseHash^=phaseHash>>15; phaseHash*=2221713035u; phaseHash^=phaseHash>>16;
  float phaseOffset=float(phaseHash & kHashMask)*kInv24;
  float clock=Seconds*speed+phaseOffset;
  float cycle=floor(clock);
  [unroll] for(int prev=0;prev<2;prev++){
   float eventIndex=cycle-prev;
   float age=(clock-eventIndex)/rate;
   uint eventHash=cellHash ^ (uint)((int)eventIndex)*3266489917u;
   uint3 hash=eventHash ^ uint3(2747636419u,668265263u,374761393u);
   hash^=hash>>16; hash*=2146121005u;
   hash^=hash>>15; hash*=2221713035u; hash^=hash>>16;
   float3 random=float3(hash & kHashMask)*kInv24;
   uint3 hash2=hash ^ uint3(1274126177u,42595009u,197830471u);
   hash2^=hash2>>16; hash2*=2146121005u;
   hash2^=hash2>>15; hash2*=2221713035u; hash2^=hash2>>16;
   float3 variation=float3(hash2 & kHashMask)*kInv24;
   float keep=(variation.x<keepProbability)?1.0:0.0;
   // Both lifetime branches must fit the two stored event periods (1.95/rate < 2 periods).
   float lifetime=min(lerp(0.65+random.z*0.25,0.48+variation.y*0.42,scatter),1.95/rate);
   float alive=step(age,lifetime)*step(random.z,saturate(Density))*keep;
   [branch] if(alive>0){
    float phase=saturate(age/lifetime);
    float2 offset=lerp(0.15+random.xy*0.7,0.02+random.xy*0.96,scatter);
    float2 center=(cell+offset)*cellSize;
    float2 delta=p-center;
    float d=max(length(delta),0.001);
    float eventRadius=radiusMax*lerp(1.0,0.6+variation.z*0.65,scatter);
    float radius=eventRadius*(0.12+0.88*phase);
    float x=d-radius;
    [branch] if(abs(x)<kCullSigma*width){
     // Radial derivative of a Gaussian ring exp(-x^2/w^2).
     float envelope=exp(-x*x/(width*width));
     float fade=smoothstep(0.0,0.12,phase)*(1.0-phase);
     float antialias=1.0-smoothstep(eventRadius*0.35,eventRadius,footprint);
     float derivative=(-2.0*x/(width*width))*envelope;
     float amplitude=lerp(1.0,0.55+variation.y*0.9,scatter);
     slope+=delta/d*derivative*kSlopeScale*amplitude*fade*antialias;
    }
   }
  }
  }
 }
 }
}}
slope=clamp(slope*clamp(ArtistStrength,0.0,3.0),-kSlopeLimit,kSlopeLimit);
return normalize(float3(-slope,1.0));
