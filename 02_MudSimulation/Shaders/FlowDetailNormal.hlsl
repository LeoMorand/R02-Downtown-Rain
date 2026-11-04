// Flow.xy = displacement in simulation UV per cycle. Flow.zw = phase, weight0.
float2 gradX = ddx(UV), gradY = ddy(UV);
float2 motion = Flow.xy * UVScale;
float phase1 = frac(Flow.z + 0.5);
float2 P0 = UV - motion * (Flow.z - 0.5);
float2 P1 = UV - motion * (phase1 - 0.5);
float h00 = Texture2DSampleGrad(Height, HeightSampler, P0, gradX, gradY).b;
float hx0 = Texture2DSampleGrad(Height, HeightSampler, P0 + float2(Offset,0), gradX, gradY).b;
float hy0 = Texture2DSampleGrad(Height, HeightSampler, P0 + float2(0,Offset), gradX, gradY).b;
float h01 = Texture2DSampleGrad(Height, HeightSampler, P1, gradX, gradY).b;
float hx1 = Texture2DSampleGrad(Height, HeightSampler, P1 + float2(Offset,0), gradX, gradY).b;
float hy1 = Texture2DSampleGrad(Height, HeightSampler, P1 + float2(0,Offset), gradX, gradY).b;
float2 slope0 = -float2(hx0-h00, hy0-h00) * Strength;
float2 slope1 = -float2(hx1-h01, hy1-h01) * Strength;
return TileScale * float3(lerp(slope1, slope0, Flow.w), 1);
