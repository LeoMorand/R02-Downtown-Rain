#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "MudShaderLibrary.generated.h"

class UTextureRenderTarget2D;

UCLASS()
class MUDSHADERLAB_API UMudShaderLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    /** Queues an RDG compute pass. True means accepted, not GPU completion.
     * Source must already contain produced state. Output: encoded world normal
     * in RGB, source B in A. Source and destination must differ and match size. */
    UFUNCTION(BlueprintCallable, Category="Mud|Shader")
    static bool DispatchHeightNormal(UTextureRenderTarget2D* Source,
        UTextureRenderTarget2D* Destination, float HeightScale = 10.0f,
        FVector2D WorldSize = FVector2D(2000.0, 2000.0));
};
