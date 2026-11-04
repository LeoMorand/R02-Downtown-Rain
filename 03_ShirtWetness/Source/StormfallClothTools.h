#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "StormfallClothTools.generated.h"
class USkeletalMesh;
UCLASS()
class STORMFALL_API UStormfallClothTools : public UBlueprintFunctionLibrary
{
 GENERATED_BODY()
public:
 UFUNCTION(BlueprintCallable,Category="Stormfall") static FString BuildHemCloth(USkeletalMesh* Mesh);
 UFUNCTION(BlueprintCallable,Category="Stormfall|Shirt") static FString BuildWetShirtHem(USkeletalMesh* Mesh);
 UFUNCTION(BlueprintCallable,Category="Stormfall|Shirt") static FString FinalizeWetShirtHem(USkeletalMesh* Mesh);
};
