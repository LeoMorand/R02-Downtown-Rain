#pragma once
#include "CoreMinimal.h"
#include "MudRebuildActor.h"
#include "MudShaderPreviewActor.generated.h"

class UMudNormalComponent;

/** Existing mud pipeline plus an optional separate RDG normal diagnostic. */
UCLASS(Blueprintable)
class MUDSHADERINTEGRATION_API AMudShaderPreviewActor : public AMudRebuildActor
{
    GENERATED_BODY()
public:
    AMudShaderPreviewActor();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Mud|Shader") TObjectPtr<UMudNormalComponent> NormalPass;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Mud|Shader") TObjectPtr<UStaticMeshComponent> NormalPreview;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mud|Shader") TObjectPtr<UMaterialInterface> NormalPreviewMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mud|Shader") bool UseComputedNormal = true;
private:
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> PreviewMID;
    bool SmokeFinished = false;
};

