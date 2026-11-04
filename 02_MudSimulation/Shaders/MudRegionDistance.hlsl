// Shared analytic region used by the visible cutout and sphere handoff.
// Inputs: Position, RegionCenter, RegionSize, RegionSettings, Shape.
// Positive inside, cm. Ellipse/blob distances are approximations, not exact SDFs.
float2 p = Position.xy - RegionCenter.xy;
float c = cos(RegionSettings.x), s = sin(RegionSettings.x);
p = float2(c*p.x + s*p.y, -s*p.x + c*p.y);
float2 halfSize = max(RegionSize.xy * 0.5, float2(0.5,0.5));
float insideCm = 1000000.0;
if (Shape > 0.5 && Shape < 1.5) {
    float radius = saturate(RegionSize.z) * min(halfSize.x,halfSize.y);
    float2 q = abs(p) - (halfSize-radius);
    insideCm = radius - length(max(q,0.0)) - min(max(q.x,q.y),0.0);
} else if (Shape >= 1.5) {
    float2 n = p/halfSize;
    float theta = atan2(n.y,n.x);
    float radial = 1.0;
    if (Shape > 2.5) {
        float seed = RegionSettings.z;
        float waves = 0.5*sin(3.0*theta+seed) + 0.3*sin(5.0*theta-1.7*seed) + 0.2*sin(9.0*theta+0.7*seed);
        radial += clamp(RegionSettings.y,0.0,0.45)*waves;
    }
    insideCm = (radial-length(n))*min(halfSize.x,halfSize.y);
}
