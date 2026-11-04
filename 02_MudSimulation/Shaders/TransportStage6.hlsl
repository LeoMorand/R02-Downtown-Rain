// Selected Advection 2.4; the scalar feedback multiplies XYZ, not only XY.
float3 velocity=Texture2DSampleLevel(Field,FieldSampler,UV,0).rgb;
float2 back=UV-velocity.xy*CellSize*SimSpeed;
if(AreaClamp<0.5) back=frac(back);
return Texture2DSampleLevel(Field,FieldSampler,back,0).rgb*Feedback;
