#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "StormfallWetFootprints.generated.h"

class UMaterialInterface;

// Leaves drying wet footprints behind the player character. Each foot is tracked by bone; when it
// comes down onto the ground (with hysteresis so one step stamps once) a decal is spawned at the
// traced ground point, oriented along the character's heading. The decal fades over DryDuration,
// and the material uses that fade to shrink the print from its edges inwards, like real drying.
UCLASS(ClassGroup=(Stormfall))
class STORMFALL_API AStormfallWetFootprints : public AActor
{
    GENERATED_BODY()

public:
    AStormfallWetFootprints();

    // Decal material (deferred decal domain). See Tools/WetFootprints.
    UPROPERTY(EditAnywhere, Category="Wet Footprints")
    TObjectPtr<UMaterialInterface> DecalMaterial;

    UPROPERTY(EditAnywhere, Category="Wet Footprints")
    TArray<FName> FootBones = {TEXT("foot_l"), TEXT("foot_r")};

    // Footprint length and width, cm.
    UPROPERTY(EditAnywhere, Category="Wet Footprints", meta=(ClampMin="1"))
    FVector2D PrintSize = FVector2D(30.f, 12.f);

    // A foot counts as planted when its bone is this close to the ground, and lifted again above
    // LiftHeight; the gap stops one step from stamping repeatedly. Measured on the GASP character:
    // the ankle sits 9-12 cm up when planted and lifts 31-61 cm mid-stride, so 18/26 leaves margin
    // for frame-rate sampling.
    UPROPERTY(EditAnywhere, Category="Wet Footprints", meta=(ClampMin="0"))
    float PlantHeight = 18.f;

    UPROPERTY(EditAnywhere, Category="Wet Footprints", meta=(ClampMin="0"))
    float LiftHeight = 26.f;

    // Seconds a print stays fully wet, then seconds it takes to dry away.
    UPROPERTY(EditAnywhere, Category="Wet Footprints", meta=(ClampMin="0"))
    float WetSeconds = 4.f;

    UPROPERTY(EditAnywhere, Category="Wet Footprints", meta=(ClampMin="0.1"))
    float DrySeconds = 16.f;

    // Oldest prints are removed first once this many exist.
    UPROPERTY(EditAnywhere, Category="Wet Footprints", meta=(ClampMin="1"))
    int32 MaxPrints = 120;

    // Optional expanding ripple spawned with each step (normal-only decal). See Tools/WetFootprints.
    UPROPERTY(EditAnywhere, Category="Wet Footprints|Ripple")
    TObjectPtr<UMaterialInterface> RippleMaterial;

    // Ripple radius, cm, and how long it takes to spread and fade, seconds.
    UPROPERTY(EditAnywhere, Category="Wet Footprints|Ripple", meta=(ClampMin="1"))
    float RippleRadius = 45.f;

    UPROPERTY(EditAnywhere, Category="Wet Footprints|Ripple", meta=(ClampMin="0.05"))
    float RippleSeconds = 0.9f;

    // Logs each foot's height above the ground per frame (LogTemp) to tune Plant/LiftHeight.
    UPROPERTY(EditAnywhere, Category="Wet Footprints|Debug")
    bool bLogFootHeights = false;

    virtual void Tick(float DeltaSeconds) override;

private:
    struct FFootState
    {
        bool bPlanted = true;   // start planted so spawning in does not stamp
    };
    TArray<FFootState> Feet;
    TArray<TWeakObjectPtr<class UDecalComponent>> Prints;

    void Stamp(const FVector& Ground, const FVector& Normal, float Yaw, bool bRightFoot);
};
