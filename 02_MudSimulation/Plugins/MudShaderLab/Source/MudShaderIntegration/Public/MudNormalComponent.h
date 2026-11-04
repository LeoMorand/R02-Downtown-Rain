#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "MudNormalComponent.generated.h"

class AMudRebuildActor;
class UTextureRenderTarget2D;
struct FMudNormalRenderState;

/** Optional normal derivation; does not replace or write the solver state. */
UCLASS(ClassGroup=(Rendering), meta=(BlueprintSpawnableComponent))
class MUDSHADERINTEGRATION_API UMudNormalComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UMudNormalComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

    /** Empty uses the owning MudRebuildActor. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mud|Shader")
    TObjectPtr<AMudRebuildActor> InputActor;

    /** Height in world units per unit of exported B. Negative flips slopes. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mud|Shader")
    float HeightScale = 10;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mud|Shader")
    FVector2D WorldSize = FVector2D(2000, 2000);

    /** RGB: encoded +Z world-space normal. A: source B. */
    UPROPERTY(Transient, BlueprintReadOnly, Category="Mud|Shader")
    TObjectPtr<UTextureRenderTarget2D> NormalOutput;

    UPROPERTY(Transient, BlueprintReadOnly, Category="Mud|Shader")
    bool LastDispatchAccepted = false;

    UPROPERTY(Transient, BlueprintReadOnly, Category="Mud|Shader")
    int64 ProducerGraphDispatches = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mud|Shader")
    bool EnableNormalPass = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mud|Profiling")
    bool ProfileGPU = false;
    UPROPERTY(Transient, BlueprintReadOnly, Category="Mud|Profiling")
    float LastGPUTimeMs = -1;
    UPROPERTY(Transient, BlueprintReadOnly, Category="Mud|Profiling")
    int64 GPUTimingSamples = 0;
private:
    TSharedPtr<FMudNormalRenderState, ESPMode::ThreadSafe> RenderState;
};

