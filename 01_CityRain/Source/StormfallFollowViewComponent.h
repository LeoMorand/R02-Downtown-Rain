#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "StormfallFollowViewComponent.generated.h"

// Keeps one scene component of its owner centred under the active view (player camera in game,
// the perspective level viewport in the editor). Used to make a fixed-size rain emitter follow the
// camera instead of enlarging it to cover the whole map. Only X/Y follow the view; Z keeps the
// authored height unless the view rises above it.
UCLASS(ClassGroup=(Stormfall), meta=(BlueprintSpawnableComponent))
class STORMFALL_API UStormfallFollowViewComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UStormfallFollowViewComponent();

    // Name of the owner's scene component to move (for example the rain Niagara component).
    UPROPERTY(EditAnywhere, Category="Follow View")
    FName TargetComponentName = TEXT("Rain");

    // Minimum height of the target above the view, cm. Keeps rain spawning above a high camera.
    UPROPERTY(EditAnywhere, Category="Follow View", meta=(ClampMin="0"))
    float MinHeightAboveView = 300.f;

    // Also follow the editor viewport camera when not playing.
    UPROPERTY(EditAnywhere, Category="Follow View")
    bool bFollowInEditor = true;

    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

protected:
    virtual void OnRegister() override;

private:
    bool GetViewLocation(FVector& OutLocation) const;
    USceneComponent* FindTarget() const;

    // Authored world Z of the target, captured when the component registers.
    float AuthoredZ = 0.f;
    bool bHasAuthoredZ = false;
};
