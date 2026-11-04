// Breaks up the smooth 12-anchor wetness field into an irregular capillary front.
// P is skeletal mesh component space (cm). Returns float2(perturbed wetness, fibre noise).
// Jitter is scaled by 4W(1-W): fully dry and fully wet regions stay exactly 0 and 1.
struct FWetNoise
{
    float Hash(float3 p) { p = frac(p*0.3183099+0.1); p *= 17.0; return frac(p.x*p.y*p.z*(p.x+p.y+p.z)); }
    float Value(float3 x)
    {
        float3 i = floor(x); float3 f = frac(x); f = f*f*(3.0-2.0*f);
        return lerp(lerp(lerp(Hash(i),               Hash(i+float3(1,0,0)), f.x),
                         lerp(Hash(i+float3(0,1,0)), Hash(i+float3(1,1,0)), f.x), f.y),
                    lerp(lerp(Hash(i+float3(0,0,1)), Hash(i+float3(1,0,1)), f.x),
                         lerp(Hash(i+float3(0,1,1)), Hash(i+1.0),           f.x), f.y), f.z);
    }
};
FWetNoise N;
float front = 0.65*N.Value(P*0.06) + 0.35*N.Value(P*0.17+17.0);   // ~16 cm and ~6 cm blotches
float fibre = N.Value(P*0.9);                                      // ~1 cm roughness breakup
float w = saturate(W);
return float2(saturate(w + (front-0.5)*Breakup*saturate(4.0*w*(1.0-w))), fibre);
