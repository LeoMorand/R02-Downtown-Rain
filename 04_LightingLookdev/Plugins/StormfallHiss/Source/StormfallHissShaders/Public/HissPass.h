#pragma once
#include "CoreMinimal.h"
#include "ScreenPass.h"
#include "HissSnapshot.h"
struct FPostProcessMaterialInputs;
class FSceneView;
STORMFALLHISSSHADERS_API FScreenPassTexture AddHissPass(FRDGBuilder& Graph,const FSceneView& View,const FPostProcessMaterialInputs& Inputs,const FHissSnapshot& Snapshot);
