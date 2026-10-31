// Standalone DXC syntax harness for ripple_flipbook.hlsl; does not reproduce Unreal's generated material.
Texture2D Flipbook;
SamplerState FlipbookSampler;
cbuffer Parameters : register(b0) {
 float Seconds;
 float ArtistSpeed;
 float ArtistStrength;
 float ArtistDensity;
};
float3 main(float3 WorldPos : TEXCOORD0) : SV_Target0 {
#include "ripple_flipbook.hlsl"
}
