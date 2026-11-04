// Wet cotton albedo. Water fills the air gaps between fibres, so less light scatters back
// out of the surface: the colour gets darker and more saturated rather than uniformly dimmed.
// Thin light fabric also turns translucent and shows the skin underneath.
// A darker tide line forms where the wet front moves forward. It appears only where
// wetness changes across the surface, so uniform half-wet or fully wet states get no rim.
float w = saturate(WF.x);
float3 dry = max(Dry, 0.0);
float lum = dot(dry, float3(0.2126, 0.7152, 0.0722));
// Light cloth mostly turns translucent rather than dark; dark cloth darkens fully.
// The stock dark-grey shirt (linear luminance ~0.07) counts as dark cloth; linear 0.35+ (light grey to white) as light.
float lightness = smoothstep(0.1, 0.35, lum);
float absorption = lerp(clamp(Absorption, 0.05, 1.0), lerp(clamp(Absorption, 0.05, 1.0), 1.0, 0.5), lightness);
float3 wet = max(lerp(lum.xxx, dry, Saturation), 0.0) * absorption;
float showThrough = ShowThrough * w * w * lightness;               // bright cloth shows more skin
wet = lerp(wet, Skin * absorption * 1.4, showThrough);
float pixelCm = max(length(float2(length(ddx(P)), length(ddy(P)))), 1e-4);
float gradientPerCm = length(float2(ddx(w), ddy(w))) / pixelCm;
float band = smoothstep(0.05, 0.25, w) * (1.0 - smoothstep(0.3, 0.6, w));
// The 12-anchor field changes ~1.0 over ~40 cm (0.025/cm); 40 maps that to full strength.
// Dark cloth shows blotchy wet patches, not a rim; keep 40% of the tide line there.
float tideLine = Edge * lerp(0.4, 1.0, lightness) * band * saturate(gradientPerCm * 40.0);
return lerp(dry, wet, smoothstep(0.0, 1.0, w)) * (1.0 - tideLine);
