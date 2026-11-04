#pragma once
#include "CoreMinimal.h"
#include "RHIResources.h"
class FRDGBuilder;
class FRHITexture;
struct FMudNormalTiming
{
    FRenderQueryRHIRef Start, End;
    uint32 Frame = 0;
};

/** Adds to the caller's graph, preserving dependencies on prior simulation writes.
 * Returns false when strict mode cannot find the producer texture in this graph. */
MUDSHADERLAB_API bool AddMudHeightNormalPass(FRDGBuilder& GraphBuilder,
    FRHITexture* Source, FRHITexture* Destination, FIntPoint Extent,
    float HeightScale, FVector2f TexelWorldSize, bool RequireProducerInGraph = false,
    TSharedPtr<FMudNormalTiming, ESPMode::ThreadSafe> Timing = nullptr);
