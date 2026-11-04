#include "StormfallHissVolume.h"
#include "Components/SceneComponent.h"
AStormfallHissVolume::AStormfallHissVolume() {
 RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
 PrimaryActorTick.bCanEverTick=false;
}
