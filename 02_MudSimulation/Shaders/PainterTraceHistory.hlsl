Value=0;
#if GPU_SIMULATION
float2 UV;Grid.ExecutionIndexToUnit(UV);
int nx,ny;Grid.GetNumCells(nx,ny);float2 Aspect=float2(nx,ny)/max(nx,ny);
float2 WorldExtents=float2(2000,2000),OffsetDelta=-WorldOffsetDelta;
float4 accumulator=0;
int count;Positions.Length(count);
int strokeIndex=0;
// A separate imprint channel: fluid XYZ is unchanged.
float traceImprint=0;
// AutoAdjustNeighborCellNumber uses world centimetres / 100 for this 20m preset.
float2 neighborCenter=(floor(UV*20)+0.5)/20;
for(int index=0;index<count;index++){
float4 positionRecord,previousRecord,velocityRecord;
Tracker.GetPreviousVector4Value<Attribute=TrackedPosition>(index,0,positionRecord);
Tracker.GetPreviousVector4Value<Attribute=TrackedPrevious>(index,0,previousRecord);
Tracker.GetPreviousVector4Value<Attribute=TrackedVelocity>(index,0,velocityRecord);
float2 Position=positionRecord.xy,PreviousPosition=previousRecord.xy;
float PositionZ=positionRecord.z,ObjectSize=positionRecord.w;
// Match Hash-1's active interaction volume and Hash-2's local candidate list.
if(any(positionRecord.xy<=0)||any(positionRecord.xy>=1)||PositionZ<0.475||PositionZ>0.525)continue;
float2 neighborSegment=Position-PreviousPosition;
float segmentT=saturate(dot(neighborCenter-PreviousPosition,neighborSegment)/max(dot(neighborSegment,neighborSegment),1e-20));
float neighborDistance=length(neighborCenter-(PreviousPosition+neighborSegment*segmentT));
float neighborRadius=ObjectSize*0.01;
if(round((neighborDistance-neighborRadius)*5)/5>=2*neighborRadius)continue;
if(strokeIndex>=256)break;
float3 Velocity=velocityRecord.xyz;float Age=velocityRecord.w;
float VelocityClamp=2,NegativePuncture=0,Puncture=0.05,BrushSize=1;
float InterpolationLimit=100,Interpolate=1,Hardness=0,HardnessBySize=0;
float ZFadeScale=5,FadeByZ=0,FieldHeight=0;
float VelocityPower=1.6,VelocityZMultiplier=1,VelocityXYMultiplier=1;
float SlowVelocityThreshold=0.4,BrushStrength=1,DensityEnable=1,InputFeedback=0.05;
float2 noiseUV=UV+WorldOffset;
float4 velocityNoiseSample,densityNoiseSample;
NoiseTexture.SampleTexture2D(noiseUV*30+SimTime*0.1,0,velocityNoiseSample);
NoiseTexture.SampleTexture2D(noiseUV*3+trunc(SimTime*40)*0.1,0,densityNoiseSample);
float2 VelocityNoise=(velocityNoiseSample.xy-0.5)*0.1*VelocityNoiseAmount;
float DensityNoise=max(pow(max(densityNoiseSample.r,0),2),1-DensityNoiseAmount);
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
// Physics-asset foot/ankle origins sit above the sole: full weight through
// 20 cm, fade out by 40 cm, rather than weakening a planted ankle at 13 cm.
float contactWeight=(1-smoothstep(20,40,abs((PositionZ-0.5)*2000)));
float movingWeight=saturate(length(Velocity.xy)*20);
traceImprint=max(traceImprint,field*contactWeight*movingWeight);
float halfWidth=0.5*clamp(Hardness+min(ObjectSize*HardnessBySize,0.5),0,0.95);
float mask=smoothstep(halfWidth,1-halfWidth,DensityNoise*field);

// Append after BrushShapeStage5b, omitting that file's final return.
float2 safeVelocity=clamp(Velocity.xy,-VelocityClamp,VelocityClamp);
float2 shapedVelocity=sign(safeVelocity)*pow(abs(safeVelocity),VelocityPower);
float slow=length(Velocity)<SlowVelocityThreshold ? pow(length(Velocity),1.5) : 1;
float baseStrength=slow*BrushStrength*DensityEnable;
float zContribution=vz*VelocityZMultiplier;
float punctureVelocity=(NegativePuncture>0.5 ? -zContribution : abs(zContribution))*10+puncture;
float strength=baseStrength*(1+punctureVelocity*0.1);
float2 q=(UV-(PreviousPosition+OffsetDelta*0.01))*Aspect;
float2 outward=100*(q+VelocityNoise)*punctureVelocity*pow(1-field,2)*(baseStrength+1-DensityEnable);
float feedback=max(InputFeedback-0.5,0);
float velocityWeight=pow(max((strokeIndex==0?mask:field)-feedback*0.1,0),1-min(feedback*2,0.9));
float2 velocity=(shapedVelocity+outward)*velocityWeight*(min(pow(max(strength,0),0.25),1)+1-DensityEnable);
float density=strength*mask;
float3 result=clamp(float3(velocity,density),float3(-VelocityClamp,-VelocityClamp,-1),float3(VelocityClamp,VelocityClamp,1))*float3(VelocityXYMultiplier,VelocityXYMultiplier,1);
float opacity=saturate(density+pow(max(1-InputFeedback,0),3));


if(strokeIndex>0)opacity=saturate(density+10*density*pow(1-InputFeedback,3));
// SelectivelyKillDensity is initialized to 1 before entering the loop.
// With SimplePainterMode=false and ForceAdditiveStrokeBlending=false,
// the original takes TranslucentBlend even for the first input stroke.
accumulator.xyz=result*opacity+accumulator.xyz*(1-opacity);
accumulator.w=max(accumulator.w,opacity);
strokeIndex++;
}
float4 history;Grid.SamplePreviousGridVector4Value<Attribute=State>(UV+WorldOffsetDelta,history);
if(strokeIndex==0)accumulator=float4(0,0,0,pow(0.95,3));
// Runtime GPU inspection: InputFeedback is .05 after preset initialization.
float3 painted=accumulator.xyz*accumulator.w+history.xyz*(1-accumulator.w);
float4 mesh;Sdf.SamplePreviousGridVector4Value<Attribute=State>(UV,mesh);
painted.xy=mesh.xy*mesh.z+painted.xy*(1-mesh.z);painted.z=max(mesh.z,painted.z);
float edgeValue=saturate(100-0.01-max(abs(UV.x*200-100),abs(UV.y*200-100)));
// Painter W was not consumed by Composite/Divergence/PainterTexture.
// Retain world-space imprints without transporting them with the fluid.
float traceDecay=exp2(-max(DeltaTime,0)/max(TrailHalfLifeSeconds,0.1));
float trace=max(saturate(history.w)*traceDecay,saturate(traceImprint*max(TrailImprintGain,0)));
Value=float4(painted,trace)*(edgeValue>=1?1:0);
#endif
