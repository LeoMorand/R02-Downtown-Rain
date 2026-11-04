// Signed exported solver velocity -> simulation UV per second.
// UVRate = SimSpeed / (grid resolution * fixed dt) for the current square grid.
// Export edge damping is already present in Velocity; do not remove it.
float period = max(Period, 0.001);
float clock = TimeOverride >= 0.0 ? TimeOverride : TimeValue;
float phase = frac(clock / period);
float phaseRamp = 1.0 - abs(phase * 2.0 - 1.0);
float weight0 = phaseRamp * phaseRamp * (3.0 - 2.0 * phaseRamp);
// Validation override is disabled when TestVelocity.z = 0.
float2 advectVelocity = lerp(Velocity.xy, TestVelocity.xy, saturate(TestVelocity.z));
return float4(advectVelocity * UVRate * period, phase, weight0);
