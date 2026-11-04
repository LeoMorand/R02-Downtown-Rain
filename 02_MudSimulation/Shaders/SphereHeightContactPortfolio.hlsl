// Rigid visual sphere placement against the same height stored in normal RT A.
// Axis-aligned height field. The simulation/collision root is not moved.
float radius = max(RadiusCm, 0.0);
float2 centerUV = (ObjectCenter.xy - SimCenter.xy) / max(WorldSize.xy, float2(0.001,0.001)) + 0.5;
if (Enabled <= 0.0 || radius <= 0.0 || HeightCm < 0.0 ||
    any(WorldSize.xy <= 0.0) || any(centerUV < 0.0) || any(centerUV > 1.0))
    return float3(0,0,0);

float4 centerData = Texture2DSampleLevel(HeightTexture, HeightTextureSampler, centerUV, 0);
float support = SimCenter.z + (centerData.a - 1.0) * HeightCm + radius;

// This candidate is exact on a plane: contact XY = -R*N.xy.
float3 n = centerData.rgb * 2.0 - 1.0;
if (dot(n,n) > 0.000001) {
    n = normalize(n);
    float2 probeUV = centerUV - radius * n.xy / WorldSize.xy;
    if (n.z > 0.0 && all(probeUV >= 0.0) && all(probeUV <= 1.0)) {
        float h = Texture2DSampleLevel(HeightTexture, HeightTextureSampler, probeUV, 0).a;
        support = max(support, SimCenter.z + (h - 1.0) * HeightCm + radius * n.z);
    }
}

// Sample the footprint, including the rim; not a certified continuous solver.
[unroll] for (int ring = 1; ring <= 4; ++ring) {
    float r = radius * (ring * 0.25);
    float cap = sqrt(max(radius * radius - r * r, 0.0));
    [unroll] for (int direction = 0; direction < 16; ++direction) {
        float angle = direction * 0.392699081698724;
        float2 sampleUV = centerUV + r * float2(cos(angle),sin(angle)) / WorldSize.xy;
        if (all(sampleUV >= 0.0) && all(sampleUV <= 1.0)) {
            float h = Texture2DSampleLevel(HeightTexture, HeightTextureSampler, sampleUV, 0).a;
            support = max(support, SimCenter.z + (h - 1.0) * HeightCm + cap);
        }
    }
}
// Blend the visual correction to the unmodified input pose at the finite domain edge.
// This is a visual handoff, not rigid-body support outside the height field.
float2 edgeCm = min(centerUV, 1.0-centerUV) * WorldSize.xy;
float edgeT = saturate(min(edgeCm.x,edgeCm.y) / max(radius*4.0,0.001));
float edgeWeight = edgeT*edgeT*(3.0-2.0*edgeT);
return float3(0,0,(support - ObjectCenter.z) * saturate(Enabled) * edgeWeight);
