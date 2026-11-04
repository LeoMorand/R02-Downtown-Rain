#include "MudShaderLibrary.h"
#include "Engine/TextureRenderTarget2D.h"
#include "TextureResource.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "GlobalShader.h"
#include "ShaderParameterStruct.h"
#include "RenderGraphBuilder.h"
#include "RenderGraphUtils.h"
#include "RenderTargetPool.h"
#include "RenderingThread.h"
#include "MudNormalPass.h"

class FMudHeightNormalCS : public FGlobalShader
{
    DECLARE_GLOBAL_SHADER(FMudHeightNormalCS);
    SHADER_USE_PARAMETER_STRUCT(FMudHeightNormalCS, FGlobalShader);
    BEGIN_SHADER_PARAMETER_STRUCT(FParameters, )
        SHADER_PARAMETER(FIntPoint, Extent)
        SHADER_PARAMETER(float, HeightScale)
        SHADER_PARAMETER(FVector2f, TexelWorldSize)
        SHADER_PARAMETER_RDG_TEXTURE(Texture2D, StateTexture)
        SHADER_PARAMETER_RDG_TEXTURE_UAV(RWTexture2D<float4>, NormalOutput)
    END_SHADER_PARAMETER_STRUCT()

    static bool ShouldCompilePermutation(const FGlobalShaderPermutationParameters& Parameters)
    {
        return IsFeatureLevelSupported(Parameters.Platform, ERHIFeatureLevel::SM5);
    }
};

IMPLEMENT_GLOBAL_SHADER(FMudHeightNormalCS, "/Plugin/MudShaderLab/Private/MudHeightNormal.usf", "MainCS", SF_Compute);

class FMudShaderLabModule : public IModuleInterface
{
public:
    virtual void StartupModule() override
    {
        const TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("MudShaderLab"));
        check(Plugin.IsValid());
        AddShaderSourceDirectoryMapping(TEXT("/Plugin/MudShaderLab"), FPaths::Combine(Plugin->GetBaseDir(), TEXT("Shaders")));
    }
};
IMPLEMENT_MODULE(FMudShaderLabModule, MudShaderLab)

bool AddMudHeightNormalPass(FRDGBuilder& GraphBuilder, FRHITexture* Source,
    FRHITexture* Destination, FIntPoint Extent, float HeightScale,
    FVector2f TexelWorldSize, bool RequireProducerInGraph,
    TSharedPtr<FMudNormalTiming, ESPMode::ThreadSafe> Timing)
{
    FRDGTextureRef Input = GraphBuilder.FindExternalTexture(Source);
    if (RequireProducerInGraph && !Input) return false;
    if (!Input) Input = GraphBuilder.RegisterExternalTexture(CreateRenderTarget(Source, TEXT("Mud.State")));
    FRDGTextureRef Output = GraphBuilder.RegisterExternalTexture(CreateRenderTarget(Destination, TEXT("Mud.Normal")));
    GraphBuilder.UseInternalAccessMode(Input);
    GraphBuilder.UseInternalAccessMode(Output);
    auto* Parameters = GraphBuilder.AllocParameters<FMudHeightNormalCS::FParameters>();
    Parameters->Extent = Extent;
    Parameters->HeightScale = HeightScale;
    Parameters->TexelWorldSize = TexelWorldSize;
    Parameters->StateTexture = Input;
    Parameters->NormalOutput = GraphBuilder.CreateUAV(Output);
    TShaderMapRef<FMudHeightNormalCS> Shader(GetGlobalShaderMap(GMaxRHIFeatureLevel));
    const FIntVector Groups = FComputeShaderUtils::GetGroupCount(Extent, FIntPoint(8, 8));
    GraphBuilder.AddPass(RDG_EVENT_NAME("Mud.HeightNormal %dx%d", Extent.X, Extent.Y),
        Parameters, ERDGPassFlags::Compute, [Shader, Parameters, Groups, Timing](FRHICommandList& RHICmdList)
        {
            if (Timing) RHICmdList.EndRenderQuery(Timing->Start);
            FComputeShaderUtils::Dispatch(RHICmdList, Shader, *Parameters, Groups);
            if (Timing) RHICmdList.EndRenderQuery(Timing->End);
        });
    // Base pass texture parameters are external to this pass's parameter struct.
    GraphBuilder.UseExternalAccessMode(Input, ERHIAccess::SRVMask);
    GraphBuilder.UseExternalAccessMode(Output, ERHIAccess::SRVMask);
    return true;
}

bool UMudShaderLibrary::DispatchHeightNormal(UTextureRenderTarget2D* Source,
    UTextureRenderTarget2D* Destination, float HeightScale, FVector2D WorldSize)
{
    if (!IsInGameThread() || !IsValid(Source) || !IsValid(Destination) || Source == Destination ||
        Source->SizeX < 1 || Source->SizeY < 1 || Source->SizeX != Destination->SizeX ||
        Source->SizeY != Destination->SizeY || !Destination->bCanCreateUAV ||
        Destination->GetFormat() != PF_FloatRGBA || !FMath::IsFinite(HeightScale) ||
        !FMath::IsFinite(WorldSize.X) || !FMath::IsFinite(WorldSize.Y) || WorldSize.X <= 0 || WorldSize.Y <= 0 ||
        GMaxRHIFeatureLevel < ERHIFeatureLevel::SM5)
    {
        return false;
    }
    FTextureRenderTargetResource* InputResource = Source->GameThread_GetRenderTargetResource();
    FTextureRenderTargetResource* OutputResource = Destination->GameThread_GetRenderTargetResource();
    if (!InputResource || !OutputResource) return false;
    const FIntPoint Extent(Source->SizeX, Source->SizeY);
    const FVector2f TexelWorldSize(WorldSize.X / Extent.X, WorldSize.Y / Extent.Y);
    // Resource release commands are ordered after this command on the render
    // thread. No UObject is dereferenced on the render thread.
    ENQUEUE_RENDER_COMMAND(MudHeightNormal)(
        [InputResource, OutputResource, Extent, HeightScale, TexelWorldSize](FRHICommandListImmediate& RHICmdList)
        {
            FTextureRHIRef InputRHI = InputResource->GetRenderTargetTexture();
            FTextureRHIRef OutputRHI = OutputResource->GetRenderTargetTexture();
            if (!InputRHI || !OutputRHI) return;
            FRDGBuilder GraphBuilder(RHICmdList);
            AddMudHeightNormalPass(GraphBuilder, InputRHI, OutputRHI, Extent, HeightScale, TexelWorldSize);
            GraphBuilder.Execute();
        });
    return true;
}
