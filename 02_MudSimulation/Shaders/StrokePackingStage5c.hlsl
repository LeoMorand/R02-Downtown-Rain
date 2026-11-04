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
float velocityWeight=pow(max(mask-feedback*0.1,0),1-min(feedback*2,0.9));
float2 velocity=(shapedVelocity+outward)*velocityWeight*(min(pow(max(strength,0),0.25),1)+1-DensityEnable);
float density=strength*mask;
float3 result=clamp(float3(velocity,density),float3(-VelocityClamp,-VelocityClamp,-1),float3(VelocityClamp,VelocityClamp,1))*float3(VelocityXYMultiplier,VelocityXYMultiplier,1);
float opacity=saturate(density+pow(max(1-InputFeedback,0),3));
return OutputAlpha>0.5 ? float3(opacity,opacity,opacity) : result;
