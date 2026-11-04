#include "MudNormalComponent.h"
#include "MudRebuildActor.h"
#include "MudShaderLibrary.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "TextureResource.h"
#include "MudNormalPass.h"
#include "NiagaraGpuComputeDispatchInterface.h"
#include "RenderingThread.h"
#include "RenderGraphBuilder.h"
#include "RHICommandList.h"

struct FMudNormalRenderState
{
    FNiagaraGpuComputeDispatchInterface* Dispatcher = nullptr;
    FDelegateHandle Handle;
    FTextureRHIRef Source, Destination;
    FIntPoint Extent = FIntPoint::ZeroValue;
    FVector2f Spacing = FVector2f(1, 1);
    float Height = 10;
    bool Enabled = true;
    bool Profile = false;
    TArray<TSharedPtr<FMudNormalTiming, ESPMode::ThreadSafe>> Pending;
    TAtomic<float> LastMs{-1};
    TAtomic<int64> TimingSamples{0};
    TAtomic<int64> DispatchCount{0};
};

UMudNormalComponent::UMudNormalComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
}

void UMudNormalComponent::BeginPlay()
{
    Super::BeginPlay();
    if (!InputActor) InputActor = Cast<AMudRebuildActor>(GetOwner());
    if (InputActor) AddTickPrerequisiteActor(InputActor);
    RenderState = MakeShared<FMudNormalRenderState, ESPMode::ThreadSafe>();
    const auto State = RenderState;
    FSceneInterface* Scene = GetWorld()->Scene;
    ENQUEUE_RENDER_COMMAND(MudRegisterAfterNiagara)([State, Scene](FRHICommandListImmediate&)
    {
        State->Dispatcher = FNiagaraGpuComputeDispatchInterface::Get(Scene);
        if (!State->Dispatcher) return;
        TWeakPtr<FMudNormalRenderState, ESPMode::ThreadSafe> Weak = State;
        State->Handle = State->Dispatcher->GetOnPostRenderEvent().AddLambda([Weak](FRDGBuilder& Graph)
        {
            const auto Pinned = Weak.Pin();
            if (!Pinned || !Pinned->Enabled || !Pinned->Source || !Pinned->Destination) return;
            for (int32 I = Pinned->Pending.Num() - 1; I >= 0; --I)
            {
                uint64 Start = 0, End = 0;
                const auto& Query = Pinned->Pending[I];
                if (GFrameNumberRenderThread - Query->Frame < 4) continue;
                if (RHIGetRenderQueryResult(Query->Start, Start, false) && RHIGetRenderQueryResult(Query->End, End, false))
                {
                    if (End >= Start)
                    {
                        // RQT_AbsoluteTime returns microseconds (D3D12 RHI).
                        Pinned->LastMs.Store(float(End - Start) / 1000.0f);
                        ++Pinned->TimingSamples;
                    }
                    Pinned->Pending.RemoveAtSwap(I);
                }
            }
            TSharedPtr<FMudNormalTiming, ESPMode::ThreadSafe> Timing;
            if (Pinned->Profile && GSupportsTimestampRenderQueries && Pinned->Pending.Num() < 8)
            {
                Timing = MakeShared<FMudNormalTiming, ESPMode::ThreadSafe>();
                Timing->Start = RHICreateRenderQuery(RQT_AbsoluteTime);
                Timing->End = RHICreateRenderQuery(RQT_AbsoluteTime);
                Timing->Frame = GFrameNumberRenderThread;
            }
            if (AddMudHeightNormalPass(Graph, Pinned->Source, Pinned->Destination,
                Pinned->Extent, Pinned->Height, Pinned->Spacing, true, Timing))
            {
                ++Pinned->DispatchCount;
                if (Timing) Pinned->Pending.Add(Timing);
            }
        });
    });
}

void UMudNormalComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    const auto State = RenderState;
    if (State)
    {
        ENQUEUE_RENDER_COMMAND(MudRemoveAfterNiagara)([State](FRHICommandListImmediate&)
        {
            if (State->Dispatcher) State->Dispatcher->GetOnPostRenderEvent().Remove(State->Handle);
            State->Source.SafeRelease();
            State->Destination.SafeRelease();
        });
    }
    RenderState.Reset();
    Super::EndPlay(Reason);
}

void UMudNormalComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    LastDispatchAccepted = false;
    if (!IsValid(InputActor) || !IsValid(InputActor->Output)) return;
    UTextureRenderTarget2D* Source = InputActor->Output;
    if (!NormalOutput || NormalOutput->SizeX != Source->SizeX || NormalOutput->SizeY != Source->SizeY)
    {
        NormalOutput = NewObject<UTextureRenderTarget2D>(this);
        NormalOutput->bCanCreateUAV = true;
        NormalOutput->AddressX = TA_Clamp;
        NormalOutput->AddressY = TA_Clamp;
        NormalOutput->ClearColor = FLinearColor(0.5f, 0.5f, 1, 0);
        NormalOutput->InitCustomFormat(Source->SizeX, Source->SizeY, PF_FloatRGBA, true);
        NormalOutput->UpdateResourceImmediate(true);
    }
    if (!RenderState || !FMath::IsFinite(HeightScale) || !FMath::IsFinite(WorldSize.X) ||
        !FMath::IsFinite(WorldSize.Y) || WorldSize.X <= 0 || WorldSize.Y <= 0) return;
    ProducerGraphDispatches = RenderState->DispatchCount.Load();
    LastGPUTimeMs = RenderState->LastMs.Load();
    GPUTimingSamples = RenderState->TimingSamples.Load();
    const auto State = RenderState;
    auto* InputResource = Source->GameThread_GetRenderTargetResource();
    auto* OutputResource = NormalOutput->GameThread_GetRenderTargetResource();
    const FIntPoint Extent(Source->SizeX, Source->SizeY);
    const FVector2f Spacing(WorldSize.X / Extent.X, WorldSize.Y / Extent.Y);
    const float Height = HeightScale;
    const bool Enabled = EnableNormalPass;
    const bool Profile = ProfileGPU;
    ENQUEUE_RENDER_COMMAND(MudUpdateNormalResources)([State, InputResource, OutputResource, Extent, Spacing, Height, Enabled, Profile](FRHICommandListImmediate&)
    {
        State->Source = InputResource->GetRenderTargetTexture();
        State->Destination = OutputResource->GetRenderTargetTexture();
        State->Extent = Extent;
        State->Spacing = Spacing;
        State->Height = Height;
        State->Enabled = Enabled;
        State->Profile = Profile;
    });
    LastDispatchAccepted = true;
}
