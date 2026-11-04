// UE Material Custom node body. Inputs: Height(Texture2D), UV(float2),
// Offset(float), Strength(float). Output: float3, unnormalized.
// Original density B, sine branch disabled. No POM or detail normals here.
float h0 = Texture2DSample(Height, HeightSampler, UV).b;
float hx = Texture2DSample(Height, HeightSampler, UV + float2(Offset,0)).b;
float hy = Texture2DSample(Height, HeightSampler, UV + float2(0,Offset)).b;
return float3(-(hx-h0)*Strength, -(hy-h0)*Strength, 1);
