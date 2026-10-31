#include "StormfallWetFootprints.h"

#include "Components/DecalComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"

AStormfallWetFootprints::AStormfallWetFootprints()
{
    PrimaryActorTick.bCanEverTick = true;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
}

void AStormfallWetFootprints::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    ACharacter* Character = UGameplayStatics::GetPlayerCharacter(this, 0);
    if (!DecalMaterial || !Character)
    {
        return;
    }
    USkeletalMeshComponent* Mesh = Character->GetMesh();
    if (!Mesh)
    {
        return;
    }
    Feet.SetNum(FootBones.Num());

    FCollisionQueryParams Query(SCENE_QUERY_STAT(WetFootprints), false, Character);
    for (int32 Index = 0; Index < FootBones.Num(); ++Index)
    {
        if (Mesh->GetBoneIndex(FootBones[Index]) == INDEX_NONE)
        {
            continue;
        }
        const FVector Foot = Mesh->GetBoneLocation(FootBones[Index]);
        FHitResult Hit;
        if (!GetWorld()->LineTraceSingleByChannel(Hit, Foot, Foot - FVector(0, 0, 200), ECC_Visibility, Query))
        {
            continue;
        }
        const float Height = Foot.Z - Hit.ImpactPoint.Z;
        if (bLogFootHeights)
        {
            UE_LOG(LogTemp, Display, TEXT("[WetFootprints] %s height %.1f"), *FootBones[Index].ToString(), Height);
        }
        FFootState& State = Feet[Index];
        if (!State.bPlanted && Height < PlantHeight)
        {
            State.bPlanted = true;
            Stamp(Hit.ImpactPoint, Hit.ImpactNormal, Character->GetActorRotation().Yaw,
                  FootBones[Index].ToString().EndsWith(TEXT("_r")));
        }
        else if (State.bPlanted && Height > LiftHeight)
        {
            State.bPlanted = false;
        }
    }
}

void AStormfallWetFootprints::Stamp(const FVector& Ground, const FVector& Normal, float Yaw, bool bRightFoot)
{
    // Decals project along their local X: point X down into the surface, Z along the heading.
    const FVector Forward = FRotator(0, Yaw, 0).Vector();
    const FRotator Rotation = FRotationMatrix::MakeFromXZ(-Normal, Forward).Rotator();
    const FVector Size(8.f, PrintSize.Y * 0.5f, PrintSize.X * 0.5f);   // depth, half width, half length
    // The trace starts at the ankle, which sits over the heel: move the print forward to the sole's
    // centre, about a third of the print length on the GASP skeleton.
    const FVector Centre = Ground + Forward * (PrintSize.X * 0.3f);
    // The lifespan removes the decal itself. SpawnDecalAtLocation parents decals to the WorldSettings
    // actor, so the fade must never be told to destroy its owner.
    UDecalComponent* Decal = UGameplayStatics::SpawnDecalAtLocation(this, DecalMaterial, Size, Centre, Rotation, WetSeconds + DrySeconds);
    if (!Decal)
    {
        return;
    }
    if (bRightFoot)
    {
        // The material draws a left sole; mirror it across the foot (decal local Y is U).
        Decal->SetRelativeScale3D(FVector(1.f, -1.f, 1.f));
    }
    // DecalLifetimeOpacity in the material goes 1 -> 0 over the fade; the material turns it into drying.
    Decal->SetFadeOut(WetSeconds, DrySeconds, false);
    Decal->SetFadeScreenSize(0.f);
    Prints.Add(Decal);

    if (RippleMaterial)
    {
        // Short-lived: the material reads DecalLifetimeOpacity as the ring's age.
        const FVector RippleSize(8.f, RippleRadius, RippleRadius);
        if (UDecalComponent* Ripple = UGameplayStatics::SpawnDecalAtLocation(this, RippleMaterial, RippleSize, Ground, Rotation, RippleSeconds))
        {
            Ripple->SetFadeOut(0.f, RippleSeconds, false);
            Ripple->SetFadeScreenSize(0.f);
        }
    }

    Prints.RemoveAll([](const TWeakObjectPtr<UDecalComponent>& Print) { return !Print.IsValid(); });
    while (Prints.Num() > MaxPrints)
    {
        if (UDecalComponent* Oldest = Prints[0].Get())
        {
            Oldest->DestroyComponent();
        }
        Prints.RemoveAt(0);
    }
}
