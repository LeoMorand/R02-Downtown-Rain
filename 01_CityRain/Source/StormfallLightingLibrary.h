#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "StormfallLightingLibrary.generated.h"

// Day/night switch for R02: shows one of the Downtown_West lighting sublevels and hides the other.
// Works in both worlds: in the editor it changes editor visibility without dirtying the level, in a
// game world it changes streaming visibility (both sublevels must use dynamic streaming for that).
UCLASS()
class STORMFALL_API UStormfallLightingLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    // Does nothing when the requested look is already showing, so it is safe to call every tick.
    UFUNCTION(BlueprintCallable, Category="Stormfall|Lighting", meta=(WorldContext="WorldContextObject"))
    static void SetNightLighting(const UObject* WorldContextObject, bool bNight);
};
