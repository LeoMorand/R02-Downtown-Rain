#include "StormfallFollowViewComponent.h"

#include "Camera/PlayerCameraManager.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "GameFramework/PlayerController.h"

#if WITH_EDITOR
#include "Editor.h"
#include "LevelEditorViewport.h"
#endif

UStormfallFollowViewComponent::UStormfallFollowViewComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickGroup = TG_PrePhysics;
    bTickInEditor = true;
}

void UStormfallFollowViewComponent::OnRegister()
{
    Super::OnRegister();
    if (USceneComponent* Target = FindTarget())
    {
        AuthoredZ = Target->GetComponentLocation().Z;
        bHasAuthoredZ = true;
    }
}

USceneComponent* UStormfallFollowViewComponent::FindTarget() const
{
    const AActor* Owner = GetOwner();
    if (!Owner)
    {
        return nullptr;
    }
    TInlineComponentArray<USceneComponent*> Components(Owner);
    for (USceneComponent* Component : Components)
    {
        if (Component && Component->GetFName() == TargetComponentName)
        {
            return Component;
        }
    }
    return nullptr;
}

bool UStormfallFollowViewComponent::GetViewLocation(FVector& OutLocation) const
{
    UWorld* World = GetWorld();
    if (!World)
    {
        return false;
    }
    if (World->IsGameWorld())
    {
        const APlayerController* Controller = World->GetFirstPlayerController();
        if (Controller && Controller->PlayerCameraManager)
        {
            OutLocation = Controller->PlayerCameraManager->GetCameraLocation();
            return true;
        }
        return false;
    }
#if WITH_EDITOR
    if (bFollowInEditor && GEditor)
    {
        // Prefer the viewport the user is looking through; fall back to any perspective viewport.
        const FLevelEditorViewportClient* Current = GCurrentLevelEditingViewportClient;
        if (Current && Current->IsPerspective() && Current->GetWorld() == World)
        {
            OutLocation = Current->GetViewLocation();
            return true;
        }
        for (const FLevelEditorViewportClient* Client : GEditor->GetLevelViewportClients())
        {
            if (Client && Client->IsPerspective() && Client->GetWorld() == World)
            {
                OutLocation = Client->GetViewLocation();
                return true;
            }
        }
    }
#endif
    return false;
}

void UStormfallFollowViewComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    USceneComponent* Target = FindTarget();
    FVector View;
    if (!Target || !bHasAuthoredZ || !GetViewLocation(View))
    {
        return;
    }
    const FVector Location(View.X, View.Y, FMath::Max(AuthoredZ, View.Z + MinHeightAboveView));
    // Teleport: the emitter simulates in world space, so live particles stay where they fell.
    Target->SetWorldLocation(Location, false, nullptr, ETeleportType::TeleportPhysics);
}
