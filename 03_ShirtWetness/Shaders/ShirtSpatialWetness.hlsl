// Bone-bound, UV-independent reconstruction of twelve persistent CPU wetness cells.
// P and anchor XYZ use skeletal mesh component space in centimetres; A.w is wetness.
// Inverse-distance weighting (power 4) preserves uniform fields and stays within [0,1].
// No time-based fake wetness: history is owned by StormfallShirtWetnessComponent.
const int kAnchorCount=12;                    // must match the component's cell count
const float kMinDistSq=1.0;                   // 1 cm^2 floor avoids the singularity at an anchor
if (Enable < 0.5) return saturate(LegacyWetness);
float4 anchors[kAnchorCount] = { A0,A1,A2,A3,A4,A5,A6,A7,A8,A9,A10,A11 };
float sum = 0.0;
float weights = 0.0;
[unroll] for (int i=0; i<kAnchorCount; ++i)
{
    float3 d = P - anchors[i].xyz;
    float r2 = max(dot(d,d), kMinDistSq);
    float w = rcp(r2*r2);
    sum += saturate(anchors[i].w)*w;
    weights += w;
}
return saturate(sum / max(weights, 1e-12));
