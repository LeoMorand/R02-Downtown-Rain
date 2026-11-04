#include "MudShaderPreviewActor.h"
#include "MudNormalComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TextureResource.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/PlatformMisc.h"
#include "Engine/World.h"

AMudShaderPreviewActor::AMudShaderPreviewActor()
{
    NormalPass = CreateDefaultSubobject<UMudNormalComponent>(TEXT("GlobalShaderNormal"));
    NormalPreview = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("NormalPreview"));
    NormalPreview->SetupAttachment(RootComponent);
    NormalPreview->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane")));
    NormalPreview->SetRelativeScale3D(FVector(20, 20, 1));
    NormalPreview->SetRelativeLocation(FVector(2400, 0, 0));
    NormalPreview->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void AMudShaderPreviewActor::BeginPlay()
{
    Super::BeginPlay();
    if (NormalPreviewMaterial)
    {
        PreviewMID = UMaterialInstanceDynamic::Create(NormalPreviewMaterial, this);
        NormalPreview->SetMaterial(0, PreviewMID);
    }
}

void AMudShaderPreviewActor::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (PreviewMID && NormalPass->NormalOutput)
        PreviewMID->SetTextureParameterValue(TEXT("MudNormalBuffer"), NormalPass->NormalOutput);
    if (SurfaceMID && NormalPass->NormalOutput)
    {
        SurfaceMID->SetTextureParameterValue(TEXT("MudNormalBuffer"), NormalPass->NormalOutput);
        SurfaceMID->SetVectorParameterValue(TEXT("MudSimCenter"), FLinearColor(GetActorLocation()));
        SurfaceMID->SetVectorParameterValue(TEXT("MudWorldSize"), FLinearColor(NormalPass->WorldSize.X, NormalPass->WorldSize.Y, 0));
        SurfaceMID->SetScalarParameterValue(TEXT("UseGlobalNormal"), UseComputedNormal ? 1.0f : 0.0f);
    }
    // Opt-in packaged smoke test only. Readbacks never run in normal gameplay.
    if (!SmokeFinished && FParse::Param(FCommandLine::Get(), TEXT("MudShaderSmokeTest")))
    {
        if (GetWorld()->GetTimeSeconds() > 60)
        {
            SmokeFinished = true;
            FPlatformMisc::RequestExitWithStatus(false, 2);
        }
        else if (GetWorld()->GetTimeSeconds() > 5 && NormalPass->ProducerGraphDispatches > 10 && Output && NormalPass->NormalOutput)
        {
            SmokeFinished = true;
            TArray<FFloat16Color> SourcePixels, NormalPixels;
            const bool Read = Output->GameThread_GetRenderTargetResource()->ReadFloat16Pixels(SourcePixels) &&
                NormalPass->NormalOutput->GameThread_GetRenderTargetResource()->ReadFloat16Pixels(NormalPixels);
            float MaxError = 0;
            bool Passed = Read && SourcePixels.Num() == NormalPixels.Num() && !SourcePixels.IsEmpty();
            if (Passed)
            {
                for (int32 I = 0; I < SourcePixels.Num(); ++I)
                    MaxError = FMath::Max(MaxError, FMath::Abs(SourcePixels[I].B.GetFloat() - NormalPixels[I].A.GetFloat()));
                Passed = MaxError == 0 && SurfaceMID && SurfaceMID->K2_GetTextureParameterValue(TEXT("MudNormalBuffer")) == NormalPass->NormalOutput;
            }
            FString Report = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("MudShaderSmoke.json"));
            FParse::Value(FCommandLine::Get(), TEXT("MudShaderReport="), Report);
            const FString Json = FString::Printf(TEXT("{\"pass\":%s,\"producer_graph_dispatches\":%lld,\"max_height_error\":%.9g,\"pixels\":%d,\"gpu_samples\":%lld}"),
                Passed ? TEXT("true") : TEXT("false"), NormalPass->ProducerGraphDispatches, MaxError, SourcePixels.Num(), NormalPass->GPUTimingSamples);
            FFileHelper::SaveStringToFile(Json, *Report);
            UE_LOG(LogTemp, Display, TEXT("MUD_SHADER_SMOKE %s"), *Json);
            FPlatformMisc::RequestExitWithStatus(false, Passed ? 0 : 1);
        }
    }
}
