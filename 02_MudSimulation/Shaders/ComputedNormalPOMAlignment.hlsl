// Phase01 material Custom expression source (not a standalone compute shader).
// Asset: /Game/MudStudy/Professional/Phase01/M_Surface_AlignmentAB
// Inputs: NormalTexture (TextureObject), World/Center (float3), Size (float3),
//         ParallaxUV (float2, the SAME POM result used by the surface),
//         AlignToPOM (scalar: 0 = baseline, 1 = candidate).
// Output: float3 world-space normal; existing World->Tangent node follows.
// Scope: existing axis-aligned XY test plane; rotated/scaled surfaces unverified.
// Keep mip 0 and decode unchanged so A/B isolates sample coordinates.
float2 worldUV = (World.xy - Center.xy) / max(Size.xy, float2(0.001, 0.001)) + 0.5;
float2 uv = lerp(worldUV, ParallaxUV, saturate(AlignToPOM));
return normalize(Texture2DSampleLevel(NormalTexture, NormalTextureSampler, uv, 0).rgb * 2 - 1);
