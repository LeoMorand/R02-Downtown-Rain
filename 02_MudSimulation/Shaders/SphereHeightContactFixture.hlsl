// 4 radii x 9 cases; analytic field substitutes texture reads only.
int2 cell = int2(floor(UV * float2(4,9)));
float radii[4] = {5,10,20,40};
float RadiusCm = radii[min(cell.x,3)];
int Case = min(cell.y,8);
float3 SimCenter = Case == 8 ? float3(100,-80,7) : float3(0,0,0);
float3 ObjectCenter = SimCenter + float3(Case == 5 ? 1200 : 0,0,RadiusCm);
float2 WorldSize = float2(2000,2000);
float HeightCm = Case == 7 ? 0 : 20;
float Enabled = Case == 6 ? 0 : 1;
struct AnalyticField {
 float4 Sample(float2 uv, int kind, float2 size, float heightScale) {
  float2 p = (uv-0.5)*size;
  float h = -10; float2 g = float2(0,0);
  if(kind == 0) h = 0;
  if(kind == 2) { h = -10 + 0.2*p.x - 0.1*p.y; g = float2(0.2,-0.1); }
  if(kind == 3) {
   float2 q=p-float2(12,0); float b=8*exp(-dot(q,q)/18);
   h=-10+b; g=-q*b/9;
  }
  if(kind == 4) {
   float b=-12*exp(-dot(p,p)/18); h=-2+b; g=-p*b/9;
  }
  return float4(normalize(float3(-g,1))*0.5+0.5,heightScale>0 ? 1+h/heightScale : 1);
 }
};
AnalyticField Field;
// Rigid visual sphere placement against the same height stored in normal RT A.
// Axis-aligned height field. The simulation/collision root is not moved.
float radius = max(RadiusCm, 0.0);
float2 centerUV = (ObjectCenter.xy - SimCenter.xy) / max(WorldSize.xy, float2(0.001,0.001)) + 0.5;
if (Enabled <= 0.0 || radius <= 0.0 || HeightCm < 0.0 ||
    any(WorldSize.xy <= 0.0) || any(centerUV < 0.0) || any(centerUV > 1.0))
    return float3(0.5,0.5,0.5);

float4 centerData = Field.Sample(centerUV, Case, WorldSize, HeightCm);
float support = SimCenter.z + (centerData.a - 1.0) * HeightCm + radius;

// This candidate is exact on a plane: contact XY = -R*N.xy.
float3 n = centerData.rgb * 2.0 - 1.0;
if (dot(n,n) > 0.000001) {
    n = normalize(n);
    float2 probeUV = centerUV - radius * n.xy / WorldSize.xy;
    if (n.z > 0.0 && all(probeUV >= 0.0) && all(probeUV <= 1.0)) {
        float h = Field.Sample(probeUV, Case, WorldSize, HeightCm).a;
        support = max(support, SimCenter.z + (h - 1.0) * HeightCm + radius * n.z);
    }
}

// Sample the footprint, including the rim; not a certified continuous solver.
[unroll] for (int ring = 1; ring <= 4; ++ring) {
    float r = radius * (ring * 0.25);
    float cap = sqrt(max(radius * radius - r * r, 0.0));
    [unroll] for (int direction = 0; direction < 16; ++direction) {
        float angle = direction * 0.392699081698724;
        float2 sampleUV = centerUV + r * float2(cos(angle),sin(angle)) / WorldSize.xy;
        if (all(sampleUV >= 0.0) && all(sampleUV <= 1.0)) {
            float h = Field.Sample(sampleUV, Case, WorldSize, HeightCm).a;
            support = max(support, SimCenter.z + (h - 1.0) * HeightCm + cap);
        }
    }
}
return float3(0.5 + (support - ObjectCenter.z) * saturate(Enabled) / 64.0,0,1);
