if (Mode>1.5)
{
    // Integer Grid2D GetPrevious* is a texture Load, including zero outside.
    int2 index=int2(UV/CellSize);
    float2 r=Field.Load(int3(index+int2(1,0),0)).rg;
    float2 l=Field.Load(int3(index-int2(1,0),0)).rg;
    float2 u=Field.Load(int3(index+int2(0,1),0)).rg;
    float2 d=Field.Load(int3(index-int2(0,1),0)).rg;
    return float3(r.x-l.x+u.y-d.y,0,0);
}
// Selected Composite gradient uses bilinear samples and the half factor.
// The original `if(Clamp=false){frac(UV1);...}` has no coordinate effect.
float2 stepUV=CellSize*SimSpeed;
float2 r=Texture2DSampleLevel(Field,FieldSampler,UV+float2(stepUV.x,0),0).rg;
float2 l=Texture2DSampleLevel(Field,FieldSampler,UV-float2(stepUV.x,0),0).rg;
float2 u=Texture2DSampleLevel(Field,FieldSampler,UV+float2(0,stepUV.y),0).rg;
float2 d=Texture2DSampleLevel(Field,FieldSampler,UV-float2(0,stepUV.y),0).rg;
if(Mode<0.5) return float3(r.x-l.x+u.y-d.y,0,0);
return float3((r.x-l.x)*0.5,(u.x-d.x)*0.5,0);
