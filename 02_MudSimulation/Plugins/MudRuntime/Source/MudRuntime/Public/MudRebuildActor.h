#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MudRebuildActor.generated.h"

class UNiagaraComponent;
class UNiagaraSystem;
class UStaticMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UTextureRenderTarget2D;

/** Own runtime inputs and output display; all fluid calculations remain in Niagara. */
UCLASS(Blueprintable)
class MUDRUNTIME_API AMudRebuildActor : public AActor
{
    GENERATED_BODY()
public:
    AMudRebuildActor();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Mud") TObjectPtr<UNiagaraComponent> Simulation;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Mud") TObjectPtr<UStaticMeshComponent> Surface;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Mud") TObjectPtr<UNiagaraSystem> Solver;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Mud") TObjectPtr<UMaterialInterface> SurfaceMaterial;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Mud",meta=(ClampMin="32",ClampMax="2048")) int32 OutputResolution=512;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Mud|Input") TArray<TObjectPtr<AActor>> BrushActors;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Mud|Input") bool TrackPlayer=true;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Mud|Input") bool TrackPhysicsBones=true;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Mud|Input") bool UseObjectBounds=true;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Mud|Input") float BrushPositionRandom=1.0f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Mud|Input") float OffsetInMotionDirection=0.5f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Mud|Input") int32 InputRandomSeed=12345;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Mud|Input",meta=(ClampMin="0.001")) float PlayerBrushSize=0.15f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Mud|Input",meta=(ClampMin="0.001")) float ObjectBrushSize=0.15f;
    UPROPERTY(Transient,BlueprintReadOnly,Category="Mud") TObjectPtr<UTextureRenderTarget2D> Output;
    UPROPERTY(Transient,BlueprintReadOnly,Category="Mud") TObjectPtr<UMaterialInstanceDynamic> SurfaceMID;
    UFUNCTION(BlueprintCallable,Category="Mud") void RebuildSimulation();
private:
    struct FBrushHistory {FVector World=FVector::ZeroVector;FVector Velocity=FVector::ZeroVector;FVector ModifiedUnit=FVector::ZeroVector;float Age=0;};
    TMap<FName,FBrushHistory> History;
    int32 PreviousInputCount=0;
    FRandomStream InputRandom;
};
