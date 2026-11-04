#include "HissPass.h"
#include "GlobalShader.h"
#include "ShaderParameterStruct.h"
#include "RenderGraphBuilder.h"
#include "RenderGraphUtils.h"
#include "SceneView.h"
#include "PostProcess/PostProcessMaterialInputs.h"
#include "SceneTexturesConfig.h"
#include "ProfilingDebugging/RealtimeGPUProfiler.h"
DECLARE_GPU_STAT_NAMED(StormfallHiss, TEXT("Stormfall.Hiss"));


class FStormfallHissPS : public FGlobalShader {
 DECLARE_GLOBAL_SHADER(FStormfallHissPS);
 SHADER_USE_PARAMETER_STRUCT(FStormfallHissPS,FGlobalShader);
 BEGIN_SHADER_PARAMETER_STRUCT(FParameters,)
  SHADER_PARAMETER_RDG_TEXTURE(Texture2D,SceneColor)
  SHADER_PARAMETER_RDG_TEXTURE(Texture2D,SceneDepth)
  SHADER_PARAMETER_SAMPLER(SamplerState,SceneSampler)
  SHADER_PARAMETER(FVector4f,InputRect)
  SHADER_PARAMETER(FVector2f,InputExtentInverse)
  SHADER_PARAMETER(FVector4f,OutputRect)
  SHADER_PARAMETER_STRUCT_REF(FViewUniformShaderParameters,View)
  SHADER_PARAMETER(FVector2f,DepthExtentInverse)
  SHADER_PARAMETER(FVector4f,DepthTransform)
  SHADER_PARAMETER(FVector4f,EdgeColor)
  SHADER_PARAMETER(FVector4f,ErosionColor)
  SHADER_PARAMETER(FVector4f,Controls)
  SHADER_PARAMETER(FVector4f,Erosion)
  RENDER_TARGET_BINDING_SLOTS()
 END_SHADER_PARAMETER_STRUCT()
 static bool ShouldCompilePermutation(const FGlobalShaderPermutationParameters& P) { return IsFeatureLevelSupported(P.Platform,ERHIFeatureLevel::SM5); }
};
IMPLEMENT_GLOBAL_SHADER(FStormfallHissPS,"/Plugin/StormfallHiss/Private/Hiss.usf","MainPS",SF_Pixel);
FScreenPassTexture AddHissPass(FRDGBuilder& Graph,const FSceneView& View,const FPostProcessMaterialInputs& Inputs,const FHissSnapshot& S) {
 if(!S.bEnabled || S.Intensity<=0.f || !Inputs.SceneTextures.SceneTextures) return Inputs.ReturnUntouchedSceneColorForPostProcessing(Graph);
 RDG_EVENT_SCOPE_STAT(Graph, StormfallHiss, "Stormfall.Hiss");
 const FScreenPassTexture Input=FScreenPassTexture::CopyFromSlice(Graph,Inputs.GetInput(EPostProcessMaterialInput::SceneColor));
 FRDGTextureRef Depth=Inputs.SceneTextures.SceneTextures->GetParameters()->SceneDepthTexture;
 if(!Depth) return Inputs.ReturnUntouchedSceneColorForPostProcessing(Graph);
 FScreenPassRenderTarget Output=Inputs.OverrideOutput;
 if(!Output.IsValid()) Output=FScreenPassRenderTarget::CreateFromInput(Graph,Input,ERenderTargetLoadAction::ENoAction,TEXT("Stormfall.Hiss.Output"));
 auto* P=Graph.AllocParameters<FStormfallHissPS::FParameters>();
 P->SceneColor=Input.Texture; P->SceneDepth=Depth;
 P->SceneSampler=TStaticSamplerState<SF_Bilinear,AM_Clamp,AM_Clamp,AM_Clamp>::GetRHI();
 P->InputRect=FVector4f(Input.ViewRect.Min.X,Input.ViewRect.Min.Y,Input.ViewRect.Width(),Input.ViewRect.Height());
 P->InputExtentInverse=FVector2f(1.f/Input.Texture->Desc.Extent.X,1.f/Input.Texture->Desc.Extent.Y);
 P->OutputRect=FVector4f(Output.ViewRect.Min.X,Output.ViewRect.Min.Y,Output.ViewRect.Width(),Output.ViewRect.Height());

 P->View=View.ViewUniformBuffer;
 P->DepthExtentInverse=FVector2f(1.f/Depth->Desc.Extent.X,1.f/Depth->Desc.Extent.Y);
 P->DepthTransform=View.InvDeviceZToWorldZTransform;
 P->EdgeColor=FVector4f(S.EdgeColor.R,S.EdgeColor.G,S.EdgeColor.B,1.f);
 P->ErosionColor=FVector4f(S.ErosionColor.R,S.ErosionColor.G,S.ErosionColor.B,1.f);
 P->Controls=FVector4f(S.Intensity,S.EdgeThreshold,S.ChromaticAberration,S.Time);
 P->Erosion=FVector4f(S.ErosionNear,S.ErosionFar,S.ScanlineDensity,S.bDebugRed?1.f:0.f);
 P->RenderTargets[0]=FRenderTargetBinding(Output.Texture,Output.LoadAction);
 TShaderMapRef<FStormfallHissPS> Shader(GetGlobalShaderMap(View.GetFeatureLevel()));
 AddDrawScreenPass(Graph,RDG_EVENT_NAME("Stormfall.Hiss %dx%d",Output.ViewRect.Width(),Output.ViewRect.Height()),View,FScreenPassTextureViewport(Output),FScreenPassTextureViewport(Input),Shader,P);
 return Output;
}
