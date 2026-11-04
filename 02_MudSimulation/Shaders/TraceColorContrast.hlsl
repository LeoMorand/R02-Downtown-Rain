float trace=saturate(Texture2DSampleLevel(TraceBuffer,TraceBufferSampler,ParallaxUV,0).a);
return OriginalColor*(1-trace*saturate(ColorContrast));
