// Standalone DXC syntax harness; does not reproduce Unreal's generated material.
cbuffer Parameters : register(b0) {
 float ArtistRandomness;
 float SpacingCm;
 float ArtistDensity;
 float RadiusCm;
 float ArtistSize;
 float Rate;
 float ArtistStrength;
 float Density;
 float ArtistSpeed;
 float Seconds;
};
float3 main(float3 WorldPos : TEXCOORD0) : SV_Target0 {
#include "ripple_candidate.hlsl"
}
