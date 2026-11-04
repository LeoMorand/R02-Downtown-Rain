Value=0;
#if GPU_SIMULATION
float2 uv; Destination.ExecutionIndexToUnit(uv);
int nx,ny; Destination.GetNumCells(nx,ny);float2 cell=1.0/float2(nx,ny);
float4 center; Source.SamplePreviousGridVector4Value<Attribute=State>(uv,center);
float2 back=uv-center.xy*cell*SimSpeed;
if(!AreaClamp)back=frac(back);
float4 transported;Source.SamplePreviousGridVector4Value<Attribute=State>(back,transported);
// Momentum and relief retention must remain independent of the artist viscosity knob.
Value=float4(transported.xy*Feedback,transported.z*DensityFeedback,transported.w);
#endif
