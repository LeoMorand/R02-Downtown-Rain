#if GPU_SIMULATION
int x,y;Target.ExecToIndex(x,y);float2 uv;Target.ExecToUnit(uv);
float4 value,paint;
Grid.SamplePreviousGridVector4Value<Attribute=State>(uv,value);
Painter.SamplePreviousGridVector4Value<Attribute=State>(uv,paint);
float edge=saturate(10-0.01-max(abs(uv.x*20-10),abs(uv.y*20-10)));
// Only display reconstruction changes; fluid density and momentum stay untouched.
float imprint=saturate(paint.w)*clamp(TrailStrength,0,1);
float displayDensity=lerp(value.z,1.0,imprint);
// Phase18 output: RG=velocity, B=height, A=retained imprint for colour.
value=float4(value.xy*edge,1-displayDensity,imprint);
Target.SetRenderTargetValue(true,x,y,value);
#endif
