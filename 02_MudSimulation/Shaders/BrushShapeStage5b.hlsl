// Independent algebra for selected Painter 2.0 geometric footprint.
// FieldHeight and DensityNoise are explicit upstream sampled values.
float vz=clamp(Velocity.z,-VelocityClamp,VelocityClamp);
float z=NegativePuncture>0.5 ? min(vz,0.1) : vz;
float puncture=Puncture*saturate(Age*0.1);
float expansion=1+z*z*clamp(puncture*20,1,10)*saturate(abs(puncture*10));
float radius=expansion*ObjectSize/(0.002*max(WorldExtents.x,WorldExtents.y))*BrushSize;
float2 delta=(UV-Position)*Aspect;
float exponent=-2000/(radius*radius);
float pointKernel=exp2(dot(delta,delta)*exponent);
float kernel=pointKernel;
float speed=length(Velocity);
if (Interpolate>0.5 && Age>0.25 && speed!=0 && speed<=InterpolationLimit)
{
    float2 start=(PreviousPosition+OffsetDelta*0.01)*Aspect;
    float2 segment=Position*Aspect-start;
    float2 q=UV*Aspect-start;
    float segmentLength=length(segment);
    float projection=clamp(dot(q,normalize(segment)),0,segmentLength);
    float lineKernel=exp2((dot(q,q)-projection*projection)*exponent);
    kernel=max(pointKernel,lineKernel);
}
float field=saturate(kernel);
if (FadeByZ>0.5)
    field*=1-saturate(10/ZFadeScale*abs(PositionZ-0.5-FieldHeight/max(WorldExtents.x,WorldExtents.y)));
float halfWidth=0.5*clamp(Hardness+min(ObjectSize*HardnessBySize,0.5),0,0.95);
float mask=smoothstep(halfWidth,1-halfWidth,DensityNoise*field);
return float3(kernel,mask,radius);
