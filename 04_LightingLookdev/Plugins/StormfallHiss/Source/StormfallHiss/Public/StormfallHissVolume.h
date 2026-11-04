#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "StormfallHissVolume.generated.h"
UCLASS(BlueprintType)
class STORMFALLHISS_API AStormfallHissVolume : public AActor {
 GENERATED_BODY()
public:
 AStormfallHissVolume();
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Hiss") bool bEnabled=false;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Hiss",meta=(ClampMin="0",ClampMax="1")) float Intensity=0.65f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Hiss",meta=(ClampMin="0.0001",ClampMax="1")) float EdgeThreshold=0.035f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Hiss") FLinearColor EdgeColor=FLinearColor(1.f,0.025f,0.04f,1.f);
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Hiss",meta=(ClampMin="0",ClampMax="10")) float ChromaticAberration=2.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Hiss",meta=(ClampMin="0",Units="cm")) float ErosionNear=400.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Hiss",meta=(ClampMin="1",Units="cm")) float ErosionFar=2500.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Hiss") FLinearColor ErosionColor=FLinearColor(0.85f,0.05f,0.08f,1.f);
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Hiss",meta=(ClampMin="1",ClampMax="1080")) float ScanlineDensity=110.f;
};
