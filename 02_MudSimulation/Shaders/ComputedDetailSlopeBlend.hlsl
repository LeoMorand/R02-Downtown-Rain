// Base is a tangent-space unit normal; Detail.xy is a masked slope vector.
// Ignore Detail.z: the legacy tile sum carries an unwanted flat-Z bias.
float3 n = normalize(Base);
float2 slope = Detail.xy * max(Strength, 0.0);
return normalize(float3(n.xy + slope * n.z, n.z));
