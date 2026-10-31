// Wet footprint decal: shoe-sole print with tread, drying from its edges inwards.
// UV: decal texture coordinates. On a decal oriented by the C++ side, U runs along the foot and
// V across it, so q below is (V,U): q.x across, q.y along. The print is drawn as a left sole
// (big toe towards -q.x); the C++ side mirrors the decal's local Y, which is V, for the right foot.
// Lifetime: DecalLifetimeOpacity, 1 while the print is fresh, falling to 0 over the fade-out.
// Returns opacity of the wet layer (darkening and gloss are applied through it).
const float2 kForeCentre=float2(-0.06,-0.42), kForeRadius=float2(0.90,0.56);  // ball and toes, leaning to the big toe
const float2 kHeelCentre=float2( 0.05, 0.62), kHeelRadius=float2(0.66,0.36);  // heel block
const float2 kArchCentre=float2( 0.22, 0.12), kArchHalf  =float2(0.40,0.34);  // waist, on the outer edge
const float kArchWater=0.55;        // the waist barely touches the ground: a fainter link
const float kTreadPerLength=7.0;    // tread bars along the full sole length (UV -1..1)
const float kTreadDepth=0.65;       // how much less water the grooves leave than the lugs
const float kDryReach=0.9;          // how far into the print the dry front travels by the end

float2 q=(UV*2-1).yx;
// Distance-like field of the sole: 1 inside the pads, 0 on the outline.
float fore=1-length((q-kForeCentre)/kForeRadius);
float heel=1-length((q-kHeelCentre)/kHeelRadius);
float2 a=abs(q-kArchCentre)/kArchHalf;
float arch=(1-max(a.x,a.y))*kArchWater;
float field=max(max(fore,heel),arch);

// Tread: bars across the sole. The lugs carry the water, the grooves between them stay lighter.
float bar=abs(frac(q.y*kTreadPerLength*0.5)-0.5)*2;          // 0 on a lug centre, 1 in a groove
float tread=1-kTreadDepth*smoothstep(0.55,0.85,bar);

// Drying: the threshold rises as the print ages, so the thin rim evaporates first and the
// thickest water, at the pad centres, goes last.
float dry=1-saturate(Lifetime);
float edge=max(EdgeSoftness,0.01);
float wet=smoothstep(dry*kDryReach,dry*kDryReach+edge,field);
return wet*tread*saturate(WetAmount);
