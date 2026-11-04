Value=0;
#if GPU_SIMULATION
float2 uv;Destination.ExecutionIndexToUnit(uv);
int nx,ny;Destination.GetNumCells(nx,ny);
float2 cell=1.0/float2(nx,ny),aspect=float2(nx,ny)/max(nx,ny);
float2 moved=uv+WorldOffsetDelta;
float4 old,r,l,t,b,paint,paintTexture,history;
Advection.SamplePreviousGridVector4Value<Attribute=State>(moved,old);
float2 stepUV=cell*SimSpeed;
Pressure.SamplePreviousGridVector4Value<Attribute=State>(moved+float2(stepUV.x,0),r);
Pressure.SamplePreviousGridVector4Value<Attribute=State>(moved-float2(stepUV.x,0),l);
Pressure.SamplePreviousGridVector4Value<Attribute=State>(moved+float2(0,stepUV.y),t);
Pressure.SamplePreviousGridVector4Value<Attribute=State>(moved-float2(0,stepUV.y),b);
float2 velocity=old.xy-0.5*float2(r.x-l.x,t.x-b.x);
float4 amplitudeNoise;
AmplitudeNoiseTexture.SampleTexture2D((uv+WorldOffset)*4+SimTime*float2(0.25,0.1),0,amplitudeNoise);
// The original applies amplitude noise to its external velocity input, not
// Output117 (the transported velocity after pressure projection).
// This preset uses the neutral 1x1 velocity texture and zero offsets.
float2 externalVelocity=0;
if(AmplitudeNoiseEnabled)externalVelocity*=saturate(amplitudeNoise.r);
Painter.SamplePreviousGridVector4Value<Attribute=State>(uv,paint);
PainterTexture.SamplePreviousGridVector4Value<Attribute=State>(uv,paintTexture);
Destination.SamplePreviousGridVector4Value<Attribute=State>(moved,history);
float edgeValue=saturate(100-0.01-max(abs(uv.x*200-100),abs(uv.y*200-100)));
float edge=edgeValue;
float wetEdge=saturate(10-0.01-max(abs(uv.x*20-10),abs(uv.y*20-10)));
float4 noise;
DensityNoiseTexture.SampleTexture2D((uv*aspect+WorldOffset)*5,0,noise);
float densityNoise=1+1.5*(noise.r-0.5);
float density=saturate(old.z-min(EraserStrength,paint.z)+((1-EraserStrength)*paint.z+0.2*paintTexture.z)*densityNoise);
density=max(density*(0.5+0.5*DensityAccumulation*max(edge,0.7))*edge,0.000001);
float2 brush=paint.xy*(VeloFromBrushMotion*20);
float2 noisePosition=(uv+WorldOffset)*128*aspect*(0.5/0.2);
float3 noiseVector=MaterialExpressionVectorNoise(float3(noisePosition,0),1,1,true,300);
float2 directional=noiseVector.xy*0.005;
float2 directionalVelocity=directional*100*max(saturate(dot(velocity,velocity)*0.2),0);
if(!AreaClamp)directionalVelocity+=directional*(1-wetEdge)*20;
velocity=clamp(velocity+0.5*(old.z+0.1*EraserStrength*paint.z)*(brush+(1-saturate(dot(brush,brush)))*(externalVelocity+0.25*paintTexture.xy))+directionalVelocity,-VelocityClamp,VelocityClamp);
float wet=(history.w*0.982+density*(1-WetFeedback))*wetEdge;
Value=float4(velocity,density,wet);
#endif
