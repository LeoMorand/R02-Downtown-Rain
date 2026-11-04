// Footstep ripple decal: two expanding Gaussian rings, written as a tangent-space normal.
// Same idea as the R02 rain ripples: the ring is a height bump, its radial derivative is the slope.
// UV: decal texture coordinates. Lifetime: DecalLifetimeOpacity, 1 at the step falling to 0.
// Output: tangent-space normal; Opacity (secondary output) limits the blend to the rings.
const float kStartRadius=0.10, kEndRadius=0.92;   // fraction of the decal half-size
const float kWidth=0.07;                          // ring width, same units
const float kSecondRingLag=0.22;                  // the inner ring follows a little later
const float kSlopeScale=0.06;

float age=1-saturate(Lifetime);
float2 q=UV*2-1;
float r=max(length(q),1e-3);
float2 slope=0;
float cover=0;
[unroll] for(int i=0;i<2;i++){
 float a=saturate(age-i*kSecondRingLag)/(1-i*kSecondRingLag);
 float radius=lerp(kStartRadius,kEndRadius,sqrt(a));     // fast at first, slowing as it spreads
 float x=r-radius;
 float envelope=exp(-x*x/(kWidth*kWidth));
 float fade=(1-a)*(1-a)*(i==0?1:0.6);
 // d/dr of exp(-x^2/w^2): positive inside the crest, negative outside.
 slope+=q/r*(-2*x/(kWidth*kWidth))*envelope*fade*kSlopeScale*Strength;
 cover=max(cover,envelope*fade);
}
Opacity=saturate(cover*2);
return normalize(float3(-slope,1));
