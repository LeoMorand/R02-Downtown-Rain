#pragma once
#include "CoreMinimal.h"
// Plain values only. Owned per view family; copied into the render callback.
struct FHissSnapshot {
 bool bEnabled=false;
 bool bDebugRed=false;
 float Intensity=0.65f;
 float EdgeThreshold=0.035f;
 FLinearColor EdgeColor=FLinearColor(1.f,0.025f,0.04f,1.f);
 float ChromaticAberration=2.f; // pixels at the image edge, at 1080p
 float ErosionNear=400.f; // cm
 float ErosionFar=2500.f;
 FLinearColor ErosionColor=FLinearColor(0.85f,0.05f,0.08f,1.f);
 float ScanlineDensity=110.f; // cycles per image height
 float Time=0.f;
};
