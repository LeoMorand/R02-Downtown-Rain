int KernelIndex=(int)KIInput; int GaussKernelIndexOffset=(int)OffsetInput; int StepIndex=(int)StepInput; float Clamp=ClampInput; float2 TexelSize=CellSize*SimSpeed; float2 CenterUV=UV;
float2 WeightedAverage = 0.0;







static float GaussKernels[6][15] = { { 0.00117, 0.0045, 0.01394, 0.035, 0.07186, 0.12, 0.1631, 0.1807, 0.1631, 0.12, 0.07186, 0.035, 0.01394, 0.0045, 0.00117 },

			 { 0.0, 0.00222, 0.00876, 0.027, 0.0648, 0.121, 0.176, 0.199, 0.176, 0.121, 0.0648, 0.027, 0.00876, 0.00222, 0.0 },

			 { 0.0, 0.0, 0.00276, 0.01377, 0.0478, 0.1169, 0.19945, 0.23832, 0.19945, 0.1169, 0.0478, 0.01377, 0.00276, 0.0, 0.0 },

			 { 0.0, 0.0, 0.0, 0.0034, 0.0202, 0.09134, 0.22958, 0.31094, 0.22958, 0.09134, 0.0202, 0.0034, 0.0, 0.0, 0.0 },

			 { 0.0, 0.0, 0.0, 0.0, 0.0106, 0.075, 0.2387, 0.351, 0.2387, 0.075, 0.0106, 0.0, 0.0, 0.0, 0.0 },

			 { 0.0, 0.0, 0.0, 0.0, 0.0, 0.06136, 0.24477, 0.38774, 0.24477, 0.06136, 0.0, 0.0, 0.0, 0.0, 0.0 }};

			 

static float CustomKernels[6][15] = { { 0.0006, 0.003, 0.01, 0.028, 0.064, 0.1348, 0.30636, 0.65711, 0.30636, 0.1348, 0.064, 0.028, 0.01, 0.003, 0.0006 },

			 { 0.0, 0.00166, 0.00726, 0.02369, 0.06055, 0.1353, 0.3028, 0.64626, 0.3028, 0.1353, 0.06055, 0.02369, 0.00726, 0.00166, 0.0 },			 

			 { 0.0, 0.0, 0.00426, 0.017, 0.052, 0.13326, 0.324532, 0.63592, 0.324532, 0.13326, 0.052, 0.017, 0.00426, 0.0, 0.0 },			 

			 { 0.0, 0.0, 0.0, 0.00514, 0.022, 0.09, 0.2956, 0.60248, 0.2956, 0.09, 0.022, 0.00514, 0.0, 0.0, 0.0 },			 

			 { 0.0, 0.0, 0.0, 0.0, 0.0053, 0.0528, 0.2503, 0.57293, 0.2503, 0.0528, 0.0053, 0.0, 0.0, 0.0, 0.0 },			 

			 { 0.0, 0.0, 0.0, 0.0, 0.0, 0.04567, 0.18454, 0.51596, 0.18454, 0.04567, 0.0, 0.0, 0.0, 0.0, 0.0 }};



		 

static int SampleCounts[6] = { 15, 13, 11, 9, 7, 5 };

int KI = KernelIndex;

int KIoffset = GaussKernelIndexOffset;

int SampleCount = SampleCounts[KI];



float2   Direction  = lerp( float2( TexelSize.x, 0 ), float2( 0, TexelSize.y), StepIndex);

float2   OffsetCenterUV = lerp( float2(CenterUV.x - ((TexelSize.x * (SampleCount-1) )/2), CenterUV.y), float2(CenterUV.x, CenterUV.y - (TexelSize.y * (SampleCount-1) )/2), StepIndex);



for ( uint ix = 0; ix <= SampleCount; ix++ )

{

   float2 SampledColor;



// Sampler, without CLAMP feature

// Grid2D.SamplePreviousGridVector2DValue<Attribute=Pressure>(OffsetCenterUV + Direction * ( ix - Direction ), SampledColor);



// Sampler, with CLAMP feature

   SampledColor=Texture2DSampleLevel(Pressure,PressureSampler,frac(min(max(OffsetCenterUV + Direction * ( ix - Direction ),Clamp-1),2-Clamp)),0).rg;



	WeightedAverage += SampledColor * float2(GaussKernels[KI+KIoffset][ix+KI], CustomKernels[KI][ix+KI]);

}








if(StepIndex!=0) WeightedAverage.x-=WeightedAverage.y;
return float3(WeightedAverage*0.999*float2(PressureFeedback,DivergenceFeedback),0);
