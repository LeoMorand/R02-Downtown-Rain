// R02 rain ripples, baked tier. Samples T_RippleFlipbook (Tools/R02/bake_ripple_flipbook.py):
// a seamlessly tiling, looping 8x4 atlas of ripple slopes. World centimetres in, tangent normal out.
// Two rotated layers at different scales hide the tile repeat; each layer was baked with half the
// event density, so together they match the procedural version. Adjacent frames are blended.
// Density, size and randomness are fixed at bake time; strength and speed stay live.
// ArtistDensity is only read as an off switch, matching the procedural tier: zero means no ripples.
const float2 kGrid=float2(8,4);               // atlas columns, rows
const float kFrames=32;
const float kTileCm=121.0996;                 // one tile = 5 cells of the baked cell size
const float kLoopSeconds=2.6059;              // at the baked ArtistSpeed (downpour preset)
const float kBakedSpeed=0.767253;             // ArtistSpeed used for the bake
const float kSlopeRange=0.5;                  // RG encoding: slope / range * 0.5 + 0.5
const float kSlopeScale=1, kSlopeLimit=.18;
const float kLayerScale=0.731;                // second layer tile size relative to the first
const float2x2 kRotate37=float2x2(0.7986,-0.6018,0.6018,0.7986);
const float2 kFadeCm=float2(2.7,7.6);         // pixel footprint over which ripples fade to flat

float2 p=WorldPos.xy;
float footprint=max(length(ddx(p)),length(ddy(p)));
if(ArtistStrength<=0.0 || ArtistDensity<=0.0 || footprint>=kFadeCm.y)
    return float3(0,0,1);
float distanceFade=1-smoothstep(kFadeCm.x,kFadeCm.y,footprint);

// Unwrapped tile coordinates: their derivatives give correct mips across the frac() seam.
float2 uvA=p/kTileCm;
float2 uvB=mul(kRotate37,p)/(kTileCm*kLayerScale);
float2 dxA=ddx(uvA)/kGrid, dyA=ddy(uvA)/kGrid;
float2 dxB=ddx(uvB)/kGrid, dyB=ddy(uvB)/kGrid;

// Speed slider rescales time; layer B runs half a loop behind so the layers never sync.
float t=Seconds*clamp(ArtistSpeed,0.1,2.0)/kBakedSpeed/kLoopSeconds;
float2 slope=0;
[unroll] for(int layer=0;layer<2;layer++){
 float frameF=frac(t+layer*0.5)*kFrames;
 float f0=floor(frameF), f1=fmod(f0+1,kFrames), w=frameF-f0;
 float2 cell0=float2(fmod(f0,kGrid.x),floor(f0/kGrid.x));
 float2 cell1=float2(fmod(f1,kGrid.x),floor(f1/kGrid.x));
 float2 local=frac(layer==0?uvA:uvB);
 float2 dx=layer==0?dxA:dxB, dy=layer==0?dyA:dyB;
 float2 s0=Flipbook.SampleGrad(FlipbookSampler,(cell0+local)/kGrid,dx,dy).rg;
 float2 s1=Flipbook.SampleGrad(FlipbookSampler,(cell1+local)/kGrid,dx,dy).rg;
 float2 s=(lerp(s0,s1,w)*2-1)*kSlopeRange;
 // The second layer is rotated: rotate its slope back into world axes.
 slope+=layer==0?s:mul(s,kRotate37);
}
slope=clamp(slope*kSlopeScale*clamp(ArtistStrength,0.0,3.0)*distanceFade,-kSlopeLimit,kSlopeLimit);
return normalize(float3(-slope,1.0));
