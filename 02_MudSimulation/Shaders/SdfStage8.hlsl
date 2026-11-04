Value=0;
#if GPU_SIMULATION
float2 uv;Grid.ExecutionIndexToUnit(uv);
// Runtime inspection: IgnoreSystemRotation=true, so simulation axes are world XY.
// Match UnitToWorld's matrix multiplication and its rounded CPU translation.
float3 samplePosition=float3(uv,0.5)*2000+(SimCenter-1000);
float distance;float3 closest,meshVelocity;
Query.GetClosestPointMeshDistanceFieldNoNormal(samplePosition,DeltaTime,1.0,0.0,distance,closest,meshVelocity);
float normalDistance,maxEncoded;float3 normalPosition,normal,normalVelocity;bool normalValid;
Query.GetClosestPointMeshDistanceFieldAccurate(samplePosition,DeltaTime,1.0,0.0,normalDistance,normalPosition,normal,normalVelocity,normalValid,maxEncoded);
float2 gradient=abs(min(distance,0))*normal.xy;
// LimitDistanceFieldInsideMesh=true selects abs(min(distance,0)) everywhere.
float d=abs(min(distance,0));
float contours=saturate(d*0.1)-saturate(0.1*max(d-10,0));
// The source multiplies SDF velocity by CPU VM's approximate inverse matrix.
float2 unitVelocity=meshVelocity.xy*0.0004999637603759765625;
float speed=length(unitVelocity);
float density=saturate(contours+d)*speed;
float2 outward=meshVelocity.z*0.01*0.25*gradient*contours;
float2 velocity=outward+unitVelocity*0.05*d;
float edgeValue=saturate(100-0.01-max(abs(uv.x*200-100),abs(uv.y*200-100)));
Value=float4(velocity,density,d*speed)*(edgeValue>=1?1:0);
#endif
