// Original current variant: InputRangeIs-0-to-1=False. RGB output.
// Inputs: FlowTexture, FlowVector, DensityMultiplier, Strength, Speed, TimeValue, UV.
float phase0 = frac(TimeValue * Speed);
float phase1 = frac(TimeValue * Speed + 0.5);
float2 movement = -FlowVector.rg * DensityMultiplier * Strength;
float2 uv0 = (UV + movement * (phase0 - 0.5) + 1.0) * 0.5;
float2 uv1 = (UV + movement * (phase1 - 0.5) + 1.0) * 0.5;
float weight = abs((phase0 - 0.5) * 2.0);
return lerp(Texture2DSample(FlowTexture, FlowTextureSampler, uv0).rgb,
            Texture2DSample(FlowTexture, FlowTextureSampler, uv1).rgb, weight);
