Position=0;Previous=0;Velocity=0;World=0;RawVelocity=0;
#if GPU_SIMULATION
int index,iy;Grid.ExecutionIndexToGridIndex(index,iy);
int count;Inputs.Length(count);
World.w=count;
float4 ageHistory;Grid.GetPreviousVector4Value<Attribute=TrackedRawVelocity>(index,0,ageHistory);
float emitterAge=ageHistory.w+DeltaTime;
RawVelocity.w=emitterAge;
if(index<count){
float4 input;Inputs.Get(index,input);
float4 oldWorld,oldRaw,oldPosition,oldVelocity;
Grid.GetPreviousVector4Value<Attribute=TrackedWorld>(index,0,oldWorld);
Grid.GetPreviousVector4Value<Attribute=TrackedRawVelocity>(index,0,oldRaw);
Grid.GetPreviousVector4Value<Attribute=TrackedPosition>(index,0,oldPosition);
Grid.GetPreviousVector4Value<Attribute=TrackedVelocity>(index,0,oldVelocity);
bool changed=(int)oldWorld.w!=count;
bool newIndex=index>=(int)oldWorld.w;
float age=emitterAge;
float3 raw=(input.xyz-oldWorld.xyz)*(0.0005/max(DeltaTime,0.000001));
if(changed||age<0.25)raw=0;
// The source CPU VM builds InvScale using reciprocal-estimate(2000).
// Preserve its rounded translation separately from the GPU matrix multiply.
const float inverseScale=0.0004999637603759765625;
precise float3 unitTranslation=-SimCenter*inverseScale+0.5;
float3 unit=input.xyz*inverseScale+unitTranslation;
float3 modified=unit;
if(length(raw)<1)modified.xy+=raw.xy*(60*MotionOffset/2000);
// Two independent uniform samples; seed is explicit for reproducible own runs.
uint seed=(uint)index*747796405u+asuint(age)+RandomSeed;
seed=((seed>>((seed>>28u)+4u))^seed)*277803737u;seed=(seed>>22u)^seed;
float rx=(float)(seed&0x00ffffffu)/16777216.0;
seed=seed*747796405u+2891336453u;seed=((seed>>((seed>>28u)+4u))^seed)*277803737u;seed=(seed>>22u)^seed;
float ry=(float)(seed&0x00ffffffu)/16777216.0;
float width=BrushRandom*20/2000;
modified.xy+=(float2(rx,ry)-0.5)*width*saturate(length(raw.xy*5));
Position=float4(modified,input.w);
// WorldToUnit refreshes Previous.UnitPosition from previous *raw* world position
// for non-camera-facing inputs; it does not retain the previous random offset.
float3 previousUnit=oldWorld.xyz*inverseScale+unitTranslation;
Previous=float4(changed?unit:previousUnit,input.w);
float3 guarded=length(raw-oldRaw.xyz)<1?raw:float3(0,0,0);
Velocity=float4(guarded,age);
World=float4(input.xyz,count);RawVelocity=float4(raw,emitterAge);
}
#endif
