#if WITH_DEV_AUTOMATION_TESTS
#include "StormfallShirtWetness.h"
#include "Misc/AutomationTest.h"
#include "Components/BoxComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/SkeletalMesh.h"
#include <limits>
#if WITH_EDITOR
#include "Editor.h"
#endif

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FShirtRates,"Stormfall.ShirtWetness.AbsorptionDrying",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FShirtRates::RunTest(const FString&)
{
    TestTrue(TEXT("Rain absorbs into dry cloth"),StormfallWetness::Integrate(0,1.f/18,0,18)>.63f);
    TestTrue(TEXT("Evaporation dries cloth"),StormfallWetness::Integrate(1,0,1.f/90,90)<.37f);
    TestTrue(TEXT("Zero rates preserve history"),FMath::IsNearlyEqual(StormfallWetness::Integrate(.73f,0,0,100),.73f));
    TestEqual(TEXT("Negative time does not reverse absorption"),StormfallWetness::Integrate(.5f,1,0,-1),.5f);
    TestTrue(TEXT("Huge time stays bounded"),FMath::IsNearlyEqual(StormfallWetness::Integrate(.5f,1,0,10000),1.f));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FShirtTime,"Stormfall.ShirtWetness.FrameRateIndependence",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FShirtTime::RunTest(const FString&)
{
    const float Exact=StormfallWetness::Integrate(.12f,.05f,.01f,20);
    for(int32 FPS:{15,30,60,120})
    {
        float W=.12f; for(int32 I=0;I<20*FPS;++I) W=StormfallWetness::Integrate(W,.05f,.01f,1.f/FPS);
        TestTrue(FString::Printf(TEXT("%d FPS matches analytic solution"),FPS),FMath::IsNearlyEqual(W,Exact,2e-5f));
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FShirtDiffusion,"Stormfall.ShirtWetness.DiffusionConservation",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FShirtDiffusion::RunTest(const FString&)
{
    TArray<float> W={1,0,0,0}; const TArray<FVector> P={{0,0,0},{10,0,0},{20,0,0},{200,0,0}};
    StormfallWetness::Diffuse(W,P,3,10,30);
    float Sum=0; for(float V:W) { Sum+=V; TestTrue(TEXT("Diffusion remains bounded"),V>=0 && V<=1); }
    TestTrue(TEXT("Diffusion conserves total moisture"),FMath::IsNearlyEqual(Sum,1.f,1e-5f));
    TestTrue(TEXT("Wet patch spreads to neighbours"),W[1]>.1f && W[2]>.1f);
    TestEqual(TEXT("Disconnected cloth cell remains dry"),W[3],0.f);
    TArray<float> Uniform={.4f,.4f,.4f,.4f}; StormfallWetness::Diffuse(Uniform,P,10,60,300);
    for(float V:Uniform) TestTrue(TEXT("Uniform field remains uniform"),FMath::IsNearlyEqual(V,.4f));
    return true;
}

#if WITH_EDITOR
namespace
{
    AStormfallShirtWeatherDemo* SpawnShirt()
    {
        UWorld* World=GEditor?GEditor->GetEditorWorldContext().World():nullptr;
        if(!World) return nullptr;
        FActorSpawnParameters Params; Params.ObjectFlags|=RF_Transient; Params.bTemporaryEditorActor=true;
        auto* Actor=World->SpawnActor<AStormfallShirtWeatherDemo>(FVector(5000000,5000000,10000),FRotator::ZeroRotator,Params);
        Actor->bRunScenario=false;
        Actor->Shirt->SetSkeletalMesh(LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Stormfall/ShirtTrial/SK_Manny_MotionStudio_Shirt")));
        Actor->Shirt->RefreshBoneTransforms();
        Actor->Wetness->bReadWeatherCollection=false; Actor->Wetness->bTraceShelter=false;
        Actor->Wetness->DiffusionRate=0;
        return Actor;
    }
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FShirtBinding,"Stormfall.ShirtWetness.MaterialOwnership",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FShirtBinding::RunTest(const FString&)
{
    auto* Actor=SpawnShirt(); if(!TestNotNull(TEXT("Test actor"),Actor)) return false;
    auto* C=Actor->Wetness.Get();
    TestTrue(TEXT("Compatible garment initializes"),C->InitializeGarment());
    TestEqual(TEXT("Six garment slots, no body/buttons"),C->MaterialCount,6);
    auto* Before=Actor->Shirt->GetMaterial(2);
    C->SetUniformWetness(.5f); C->ApplyToMaterials();
    TestTrue(TEXT("Repeated updates reuse the same MID"),Before==Actor->Shirt->GetMaterial(2));
    TestTrue(TEXT("Initialization is idempotent"),C->InitializeGarment());
    TestEqual(TEXT("No duplicate MID registrations"),C->MaterialCount,6);
    Actor->GetWorld()->DestroyActor(Actor); return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FShirtSnapshot,"Stormfall.ShirtWetness.HistoryRestore",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FShirtSnapshot::RunTest(const FString&)
{
    auto* Actor=SpawnShirt(); if(!Actor) return false;
    auto* C=Actor->Wetness.Get();
    if(!C->InitializeGarment()) { AddError(TEXT("Garment initialization failed")); Actor->Destroy(); return false; }
    C->SetUniformWetness(.63f); auto Snapshot=C->CaptureWetness(); C->SetUniformWetness(0);
    TestTrue(TEXT("Captured history restores"),C->RestoreWetness(Snapshot));
    TestTrue(TEXT("Restored average matches"),FMath::IsNearlyEqual(C->AverageWetness,.63f,1e-5f));
    Snapshot.Version=99; TestFalse(TEXT("Unknown schema rejected"),C->RestoreWetness(Snapshot));
    Snapshot.Version=1; Snapshot.Bones[0]=TEXT("wrong_bone"); TestFalse(TEXT("Different anchor layout rejected"),C->RestoreWetness(Snapshot));
    Snapshot=C->CaptureWetness(); Snapshot.Values[0]=std::numeric_limits<float>::quiet_NaN();
    TestFalse(TEXT("Nonfinite history rejected atomically"),C->RestoreWetness(Snapshot));
    TestTrue(TEXT("Rejected restore preserves state"),FMath::IsNearlyEqual(C->AverageWetness,.63f,1e-5f));
    Actor->Destroy(); return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FShirtImpact,"Stormfall.ShirtWetness.LocalImpact",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FShirtImpact::RunTest(const FString&)
{
    auto* Actor=SpawnShirt(); if(!Actor) return false;
    auto* C=Actor->Wetness.Get(); if(!C->InitializeGarment()) { AddError(TEXT("Garment initialization failed")); Actor->Destroy(); return false; }
    const auto P=C->GetAnchorPositions(); C->SetUniformWetness(0);
    C->AddWetImpact(P[8],5,.6f);
    TestTrue(TEXT("Impacted wrist retains moisture"),C->WetnessValues[8]>.59f);
    TestEqual(TEXT("Opposite wrist remains dry"),C->WetnessValues[11],0.f);
    const auto S=C->CaptureWetness(); C->AddWetImpact(P[8],-5,1);
    TestEqual(TEXT("Invalid radius cannot change history"),C->WetnessValues[8],S.Values[8]);
    C->RainAmount=0; C->AirHumidity=0; C->RefreshEnvironment(); C->AdvanceWetness(1); C->ApplyToMaterials();
    TestTrue(TEXT("Impact moisture persists after event and dries gradually"),C->WetnessValues[8]>.5f && C->WetnessValues[8]<.6f);
    Actor->Destroy(); return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FShirtWater,"Stormfall.ShirtWetness.PartialImmersion",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FShirtWater::RunTest(const FString&)
{
    auto* Actor=SpawnShirt(); if(!Actor) return false;
    auto* C=Actor->Wetness.Get(); if(!C->InitializeGarment()) { AddError(TEXT("Garment initialization failed")); Actor->Destroy(); return false; }
    const auto P=C->GetAnchorPositions();
    double Min=P[0].Z, Max=Min; for(auto V:P) {Min=FMath::Min(Min,V.Z);Max=FMath::Max(Max,V.Z);}
    C->SetWaterContact(true,(Min+Max)*.5); C->AdvanceWetness(3);
    int32 Wet=0,Dry=0; for(float W:C->WetnessValues) {Wet+=W>.5f;Dry+=W<.01f;}
    TestTrue(TEXT("Waterline wets only submerged cells"),Wet>0 && Dry>0);
    C->SetWaterContact(false,0); C->ApplyToMaterials(); const float Before=C->AverageWetness;
    C->AdvanceWetness(1); C->ApplyToMaterials();
    TestTrue(TEXT("Leaving water retains gradually drying history"),C->AverageWetness>0 && C->AverageWetness<Before);
    Actor->Destroy(); return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FShirtZone,"Stormfall.ShirtWetness.BoundedWaterZone",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FShirtZone::RunTest(const FString&)
{
    auto* World=GEditor->GetEditorWorldContext().World(); FActorSpawnParameters Params; Params.ObjectFlags|=RF_Transient;
    auto* Z=World->SpawnActor<AStormfallShirtWaterZone>(FVector(0,0,10000),FRotator(0,45,0),Params);
    Z->WaterBounds->SetBoxExtent({100,50,40});
    TestEqual(TEXT("Submerged centre is wet"),Z->SampleWater({0,0,10000}),1.f);
    TestEqual(TEXT("Outside footprint is dry"),Z->SampleWater({200,200,10000}),0.f);
    TestEqual(TEXT("Above surface is dry"),Z->SampleWater({0,0,10041}),0.f);
    TestEqual(TEXT("Below bounded water volume is dry"),Z->SampleWater({0,0,9950}),0.f);
    Z->Destroy(); return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FShirtShelter,"Stormfall.ShirtWetness.ShelterTrace",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FShirtShelter::RunTest(const FString&)
{
    auto* Actor=SpawnShirt(); if(!Actor) return false;
    auto* C=Actor->Wetness.Get();
    if(!C->InitializeGarment()) { AddError(TEXT("Garment initialization failed")); Actor->Destroy(); return false; }
    C->bTraceShelter=true; C->RainAmount=1; C->RefreshEnvironment();
    TestEqual(TEXT("Open sky is exposed"),C->RainExposure,1.f);
    FActorSpawnParameters Params; Params.ObjectFlags|=RF_Transient;
    const FVector CanopyPosition=Actor->GetActorLocation()+FVector(0,0,400);
    auto* Canopy=Actor->GetWorld()->SpawnActor<AActor>(CanopyPosition,FRotator::ZeroRotator,Params);
    auto* Box=NewObject<UBoxComponent>(Canopy); Canopy->SetRootComponent(Box);
    Box->SetBoxExtent(FVector(300,300,10)); Box->SetCollisionProfileName(TEXT("BlockAll"));
    Box->RegisterComponent(); Box->SetWorldLocation(CanopyPosition);
    C->RefreshEnvironment();
    TestEqual(TEXT("Real blocking canopy shelters every cell"),C->RainExposure,0.f);
    C->SetUniformWetness(0); C->AdvanceWetness(10);
    for(float W:C->WetnessValues) TestEqual(TEXT("Sheltered dry cloth does not absorb rain"),W,0.f);
    C->SetUniformWetness(.8f); C->AdvanceWetness(1); C->ApplyToMaterials();
    TestTrue(TEXT("Shelter does not reset existing moisture"),C->AverageWetness>.7f);
    Canopy->Destroy(); C->RefreshEnvironment(); C->AdvanceWetness(10); C->ApplyToMaterials();
    TestTrue(TEXT("Removing canopy allows rain absorption"),C->AverageWetness>.8f);
    Actor->Destroy(); return true;
}
#endif
#endif
