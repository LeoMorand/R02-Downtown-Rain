// UE Custom node, float3 result: ParallaxUV.xy and PixelDepthOffset.z.
// Tangent/local branch only. Desktop high-quality path, channel B.
// Inputs: Height, UV, HeightRatio, ReferencePlane, MinSteps, MaxSteps,
// ViewTS, ViewWS, VertexNormal, WorldPos, CameraForward, RebuildHeightScale.
float ratio = HeightRatio * RebuildHeightScale;
float2 travel = ratio * (-ViewTS.xy / ViewTS.z);
float2 startUV = UV - (1.0 - ReferencePlane) * travel;
float steps = lerp(MaxSteps, MinSteps, saturate(abs(dot(ViewWS, VertexNormal))));
float stepHeight = 1.0 / steps;
float2 stepUV = stepHeight * travel;
float2 gradX = ddx(startUV);
float2 gradY = ddy(startUV);

float ray = 1.0;
float prevRay = 1.0;
float prevHeight = 1.0;
float2 offset = 0.0;
float hitHeight = 0.0; // Defined fallback; original has undefined miss output.
for (int iteration = 0; iteration < (int)floor(steps) + 2; ++iteration)
{
    float sampled = Texture2DSampleGrad(Height, HeightSampler,
                                      startUV + offset, gradX, gradY).b;
    if (ray < sampled)
    {
        float weight = (sampled - ray) / ((prevRay - prevHeight) + (sampled - ray));
        hitHeight = prevRay * weight + ray * (1.0 - weight);
        offset -= weight * stepUV;
        break;
    }
    prevRay = ray;
    ray -= stepHeight;
    offset += stepUV;
    prevHeight = sampled;
}

float rayDistance = length(float3(offset, (1.0 - hitHeight) * ratio));
float uvPerWorld = max(length(gradX) / length(ddx(WorldPos)),
                      length(gradY) / length(ddy(WorldPos)));
float depth = rayDistance / (uvPerWorld / abs(dot(CameraForward, ViewWS)));
return float3(startUV + offset, depth);
