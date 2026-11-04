// TranslucentBlend selected by Ninja_Painter 2.0 (both call sites).
// Alpha is an independent brush weight; density is Source.z.
float3 rgb = Source.rgb * Source.a + Dest.rgb * (1 - pow(Source.a, BlendPow));
if (Additive > 0.5) rgb = Source.rgb + Dest.rgb;
float alpha = max(Source.a, Dest.a);
return OutputAlpha > 0.5 ? float3(alpha, alpha, alpha) : rgb;
