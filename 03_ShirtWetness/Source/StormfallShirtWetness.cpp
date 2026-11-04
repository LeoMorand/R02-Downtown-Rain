#include "StormfallShirtWetness.h"
#include "Components/BoxComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "DrawDebugHelpers.h"
#include "ClothingSimulationInteractor.h"
#include "ClothingAssetBase.h"
#include "ChaosCloth/ChaosClothingSimulationInteractor.h"
#include "Camera/CameraActor.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"

namespace
{
    float Unit(float V) { return FMath::IsFinite(V) ? FMath::Clamp(V,0.f,1.f) : 0.f; }
    float Positive(float V) { return FMath::IsFinite(V) ? FMath::Max(V,0.f) : 0.f; }
}

float StormfallWetness::Integrate(float W, float Input, float Evaporation, float Seconds)
{
    const float A=Positive(Input), B=Positive(Evaporation), Dt=Positive(Seconds), Sum=A+B;
    if(Sum<=SMALL_NUMBER || Dt<=0) return Unit(W);
    const float Target=A/Sum;
    return Unit(Target+(Unit(W)-Target)*FMath::Exp(-Sum*Dt));
}

void StormfallWetness::Diffuse(TArray<float>& Values, const TArray<FVector>& P, float Rate, float Seconds, float Radius)
{
    if(Values.Num()!=P.Num() || Values.Num()<2 || Positive(Rate)*Positive(Seconds)<=0) return;
    // Symmetric graph Laplacian, explicit substeps bounded by maximum degree.
    // Symmetry conserves the sum; h*max(degree)<=1 makes each step a convex combination.
    const float R=FMath::Max(1.f,Positive(Radius));
    const int32 N=Values.Num();
    TArray<float> Weights; Weights.Init(0,N*N);
    float MaxDegree=0;
    for(int32 I=0;I<N;++I)
    {
        float Degree=0;
        for(int32 J=0;J<N;++J) if(I!=J)
        {
            const float K=FMath::Square(FMath::Max(0.f,1.f-float(FVector::Distance(P[I],P[J]))/R));
            Weights[I*N+J]=K; Degree+=K;
        }
        MaxDegree=FMath::Max(MaxDegree,Degree);
    }
    const float Duration=Positive(Rate)*Positive(Seconds);
    const int32 Steps=FMath::Max(1,FMath::CeilToInt(Duration*MaxDegree));
    const float H=Duration/Steps;
    for(int32 S=0;S<Steps;++S)
    {
        const TArray<float> Before=Values;
        for(int32 I=0;I<N;++I)
        {
            float Change=0;
            for(int32 J=0;J<N;++J) Change+=Weights[I*N+J]*(Before[J]-Before[I]);
            Values[I]=Unit(Before[I]+H*Change);
        }
    }
}

AStormfallShirtWaterZone::AStormfallShirtWaterZone()
{
    PrimaryActorTick.bCanEverTick=false;
    WaterBounds=CreateDefaultSubobject<UBoxComponent>(TEXT("WaterBounds"));
    RootComponent=WaterBounds;
    WaterBounds->SetBoxExtent(FVector(150,150,75));
    WaterBounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    WaterBounds->SetCanEverAffectNavigation(false);
}

float AStormfallShirtWaterZone::SampleWater(FVector P, float FeatherCm) const
{
    const FTransform T=WaterBounds->GetComponentTransform();
    const FVector Q=T.InverseTransformPosition(P), E=WaterBounds->GetUnscaledBoxExtent();
    if(FMath::Abs(Q.X)>E.X || FMath::Abs(Q.Y)>E.Y || Q.Z < -E.Z || Q.Z>E.Z) return 0;
    const float Depth=(E.Z-Q.Z)*T.GetScale3D().GetAbs().Z;
    return Unit(Absorption)*FMath::SmoothStep(0.f,FMath::Max(.01f,FeatherCm),Depth);
}

UStormfallShirtWetnessComponent::UStormfallShirtWetnessComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostPhysics;
    for(const TCHAR* B : {TEXT("spine_03"),TEXT("spine_03"),TEXT("spine_01"),TEXT("spine_01"),TEXT("pelvis"),TEXT("pelvis"),TEXT("upperarm_l"),TEXT("lowerarm_l"),TEXT("hand_l"),TEXT("upperarm_r"),TEXT("lowerarm_r"),TEXT("hand_r")})
    {
        FStormfallWetnessAnchor A; A.Bone=FName(B); Anchors.Add(A);
    }
}

bool UStormfallShirtWetnessComponent::InitializeGarment()
{
    if(bInitialized) return Garment && MaterialCount>0;
    if(!Garment && GetOwner())
    {
        TArray<USkeletalMeshComponent*> Meshes; GetOwner()->GetComponents(Meshes);
        for(auto* M:Meshes)
        {
            bool bFound=false;
            for(int32 I=0;I<M->GetNumMaterials();++I)
            {
                float V=0;
                if(M->GetMaterial(I) && M->GetMaterial(I)->GetScalarParameterValue(FMaterialParameterInfo(TEXT("SpatialWetnessEnable")),V)) { bFound=true; break; }
            }
            if(bFound) { Garment=M; break; }
        }
    }
    if(!Garment || Anchors.Num()!=12) { BindingStatus=TEXT("Requires a garment and exactly twelve bone anchors"); return false; }
    for(const auto& A:Anchors) if(Garment->GetBoneIndex(A.Bone)==INDEX_NONE)
    { BindingStatus=FString::Printf(TEXT("Missing bone: %s"),*A.Bone.ToString()); return false; }
    for(int32 I=0;I<Garment->GetNumMaterials();++I)
    {
        auto* Original=Garment->GetMaterial(I); float V=0;
        if(!Original || !Original->GetScalarParameterValue(FMaterialParameterInfo(TEXT("SpatialWetnessEnable")),V)) continue;
        auto* MID=Garment->CreateDynamicMaterialInstance(I);
        if(MID) { Materials.Add(MID); MaterialSlots.Add(I); OriginalMaterials.Add(Original); }
    }
    MaterialCount=Materials.Num();
    if(MaterialCount==0) { BindingStatus=TEXT("No compatible SpatialWetnessEnable garment materials"); return false; }
    WetnessValues.Init(Unit(InitialWetness),12); ExposureValues.Init(1,12); ImmersionValues.Init(0,12);
    const auto Positions=GetAnchorPositions();
    for(const FVector& P:Positions) RestPositions.Add(Garment->GetComponentTransform().InverseTransformPosition(P));
    AddTickPrerequisiteComponent(Garment);
    bInitialized=true;
    BindingStatus=FString::Printf(TEXT("Ready: %d garment slots / 12 persistent bone anchors"),MaterialCount);
    ApplyToMaterials(); return true;
}

TArray<FVector> UStormfallShirtWetnessComponent::GetAnchorPositions() const
{
    TArray<FVector> Result;
    if(!Garment) return Result;
    for(const auto& A:Anchors) Result.Add(Garment->GetSocketTransform(A.Bone,RTS_World).TransformPosition(A.BoneOffset));
    return Result;
}

void UStormfallShirtWetnessComponent::BeginPlay()
{
    Super::BeginPlay();
    if(InitializeGarment())
    {
        if(Garment->IsVisible() && Garment->CanSimulateClothing() &&
           !Garment->bDisableClothSimulation && !Garment->IsClothingSimulationSuspended())
        {
            // UE 5.8 can render an offscreen shadow before the first parallel cloth buffer exists.
            // Keep the render proxy hidden until the first completed, finite simulation dataset.
            bOriginalClothWait=Garment->bWaitForParallelClothTask;
            Garment->bWaitForParallelClothTask=true;
            Garment->SetVisibility(false);
            bWaitingForCloth=true;
        }
        RefreshEnvironment();
    }
}

void UStormfallShirtWetnessComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if(Garment)
    {
        if(bWaitingForCloth) Garment->SetVisibility(true);
        if(bWaitingForCloth) Garment->bWaitForParallelClothTask=bOriginalClothWait;
        for(int32 I=0;I<MaterialSlots.Num();++I)
            if(Garment->GetMaterial(MaterialSlots[I])==Materials[I]) Garment->SetMaterial(MaterialSlots[I],OriginalMaterials[I]);
        RemoveTickPrerequisiteComponent(Garment);
    }
    Materials.Reset(); OriginalMaterials.Reset(); MaterialSlots.Reset(); RestPositions.Reset();
    bInitialized=false; MaterialCount=0;
    Super::EndPlay(Reason);
}

void UStormfallShirtWetnessComponent::RefreshEnvironment()
{
    if(!bInitialized || !GetWorld()) return;
    if(bReadWeatherCollection && WeatherCollection)
    {
        if(auto* Collection=GetWorld()->GetParameterCollectionInstance(WeatherCollection))
        {
            float Value;
            if(Collection->GetScalarParameterValue(RainParameter,Value)) RainAmount=Unit(Value);
            if(Collection->GetScalarParameterValue(HumidityParameter,Value)) AirHumidity=Unit(Value);
            // Same artist manual-mode contract as MF_WeatherArtistState.
            float Manual=0, ManualRain=0;
            if(Collection->GetScalarParameterValue(TEXT("ManualMode"),Manual) && Collection->GetScalarParameterValue(TEXT("ManualRain"),ManualRain))
                RainAmount=FMath::Lerp(Unit(RainAmount),Unit(ManualRain),Unit(Manual));
        }
    }
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ShirtRainShelter),false,GetOwner());
    // Attached clothing/body components must not shelter themselves.
    if(GetOwner()) { TArray<AActor*> Attached; GetOwner()->GetAttachedActors(Attached,true,true); Query.AddIgnoredActors(Attached); }
    FVector Up=-RainDirection.GetSafeNormal(); if(Up.IsNearlyZero()) Up=FVector::UpVector;
    const auto Positions=GetAnchorPositions(); RainExposure=0;
    TArray<AStormfallShirtWaterZone*> Zones;
    for(TActorIterator<AStormfallShirtWaterZone> It(GetWorld());It;++It) Zones.Add(*It);
    for(int32 I=0;I<Positions.Num();++I)
    {
        FHitResult Hit;
        ExposureValues[I]=bTraceShelter && GetWorld()->LineTraceSingleByChannel(Hit,Positions[I],Positions[I]+Up*FMath::Max(10.f,ShelterTraceLength),ShelterChannel,Query) ? 0.f : 1.f;
        float Water=0;
        for(auto* Zone:Zones) Water=FMath::Max(Water,Zone->SampleWater(Positions[I]));
        if(bUseExternalWaterPlane) Water=FMath::Max(Water,Unit(WaterContact)*FMath::SmoothStep(0.f,3.f,WaterSurfaceZ-float(Positions[I].Z)));
        ImmersionValues[I]=Water; RainExposure+=ExposureValues[I]/Positions.Num();
    }
    DrivenClothCount=0;
    if(bDriveClothResponse && Garment->GetSkeletalMeshAsset())
    {
        // Runtime commands affect only this component's solver, never shared asset configuration.
        for(const auto& AssetPointer:Garment->GetSkeletalMeshAsset()->GetMeshClothingAssets())
        {
            auto* Asset=AssetPointer.Get();
            if(!Asset) continue;
            auto* Solver=Garment->GetClothingSimulationInteractor(Asset->GetFName());
            if(!Solver) continue;
            auto* Cloth=Cast<UChaosClothingInteractor>(Solver->GetClothingInteractor(Asset->GetFName()));
            if(!Cloth) continue;
            Cloth->SetDamping(FMath::Lerp(Unit(DryClothDamping),Unit(WetClothDamping),AverageWetness));
            const float Stiffness=FMath::Lerp(Unit(DryAnimDrive),Unit(WetAnimDrive),AverageWetness);
            Cloth->SetAnimDrive(FVector2D(Stiffness,Stiffness),FVector2D(.2,.2));
            ++DrivenClothCount;
        }
    }
}

void UStormfallShirtWetnessComponent::AdvanceWetness(float Seconds)
{
    if(!bInitialized || !FMath::IsFinite(Seconds) || Seconds<=0) return;
    // Bound pathological Blueprint inputs without dropping normal frame time.
    const float Dt=FMath::Min(Seconds,60.f);
    for(int32 I=0;I<WetnessValues.Num();++I)
    {
        const float Rain=Unit(RainAmount)*ExposureValues[I];
        const float Water=ImmersionValues[I];
        const float Absorb=Rain/FMath::Max(.1f,Positive(RainAbsorptionSeconds))+Water/FMath::Max(.1f,Positive(WaterAbsorptionSeconds));
        const float Evaporate=(1-Water)*(1-Rain)*(1-.85f*Unit(AirHumidity))/FMath::Max(.1f,Positive(DryingSeconds));
        WetnessValues[I]=StormfallWetness::Integrate(WetnessValues[I],Absorb,Evaporate,Dt);
    }
    StormfallWetness::Diffuse(WetnessValues,RestPositions,FMath::Clamp(Positive(DiffusionRate),0.f,10.f),Dt,DiffusionRadius);
}

void UStormfallShirtWetnessComponent::SetUniformWetness(float Value)
{
    if(!bInitialized && !InitializeGarment()) return;
    WetnessValues.Init(Unit(Value),12); ApplyToMaterials();
}

void UStormfallShirtWetnessComponent::AddWetImpact(FVector Position, float Radius, float Amount)
{
    if(!bInitialized || Position.ContainsNaN() || !FMath::IsFinite(Radius) || Radius<=0) return;
    const auto P=GetAnchorPositions();
    for(int32 I=0;I<P.Num();++I)
    {
        const float Falloff=FMath::Square(FMath::Max(0.f,1.f-float(FVector::Distance(P[I],Position))/Radius));
        WetnessValues[I]=Unit(WetnessValues[I]+Unit(Amount)*Falloff);
    }
    ApplyToMaterials();
}

void UStormfallShirtWetnessComponent::SetWaterContact(bool bActive, float SurfaceZ, float Contact)
{
    bUseExternalWaterPlane=bActive && FMath::IsFinite(SurfaceZ);
    WaterSurfaceZ=FMath::IsFinite(SurfaceZ)?SurfaceZ:0; WaterContact=Unit(Contact);
    RefreshEnvironment();
}

FStormfallWetnessSnapshot UStormfallShirtWetnessComponent::CaptureWetness() const
{
    FStormfallWetnessSnapshot S; S.Values=WetnessValues;
    for(const auto& A:Anchors) S.Bones.Add(A.Bone);
    return S;
}

bool UStormfallShirtWetnessComponent::RestoreWetness(const FStormfallWetnessSnapshot& S)
{
    if(!bInitialized || S.Version!=1 || S.Values.Num()!=12 || S.Bones.Num()!=12) return false;
    for(int32 I=0;I<12;++I) if(S.Bones[I]!=Anchors[I].Bone || !FMath::IsFinite(S.Values[I])) return false;
    for(int32 I=0;I<12;++I) WetnessValues[I]=Unit(S.Values[I]);
    ApplyToMaterials(); return true;
}

void UStormfallShirtWetnessComponent::ApplyToMaterials()
{
    if(!bInitialized || !Garment) return;
    const auto P=GetAnchorPositions(); AverageWetness=0;
    for(float W:WetnessValues) AverageWetness+=W/12;
    for(const auto& Material:Materials)
    {
        auto* M=Material.Get();
        M->SetScalarParameterValue(TEXT("SpatialWetnessEnable"),1);
        for(int32 I=0;I<12;++I)
        {
            const FVector Local=Garment->GetComponentTransform().InverseTransformPosition(P[I]);
            const float W=bManualPreview?Unit(PreviewWetness):WetnessValues[I];
            M->SetVectorParameterValue(FName(*FString::Printf(TEXT("WetAnchor%d"),I)),FLinearColor(Local.X,Local.Y,Local.Z,W));
        }
    }
}

void UStormfallShirtWetnessComponent::TickComponent(float Dt, ELevelTick Type, FActorComponentTickFunction* Fn)
{
    Super::TickComponent(Dt,Type,Fn);
    if(!bInitialized) return;
    if(bWaitingForCloth)
    {
        const auto& Data=Garment->GetCurrentClothingData_GameThread();
        bool bReady=!Data.IsEmpty();
        for(const auto& Entry:Data)
        {
            bReady&=!Entry.Value.Positions.IsEmpty();
            for(const auto& P:Entry.Value.Positions) if(P.ContainsNaN()) { bReady=false; break; }
        }
        if(bReady)
        {
            Garment->SetVisibility(true);
            Garment->bWaitForParallelClothTask=bOriginalClothWait;
            bWaitingForCloth=false;
        }
    }
    EnvironmentElapsed+=Dt;
    if(EnvironmentElapsed>=FMath::Clamp(EnvironmentInterval,.02f,2.f)) { EnvironmentElapsed=0; RefreshEnvironment(); }
    if(!bManualPreview) AdvanceWetness(Dt);
    // Positions update after skeletal pose each frame; expensive traces remain throttled.
    ApplyToMaterials();
    if(bDrawDebug)
    {
        const auto P=GetAnchorPositions();
        for(int32 I=0;I<P.Num();++I) DrawDebugSphere(GetWorld(),P[I],3,8,FLinearColor::LerpUsingHSV(FLinearColor::Yellow,FLinearColor::Blue,WetnessValues[I]).ToFColor(true),false,0);
    }
}

AStormfallShirtWeatherDemo::AStormfallShirtWeatherDemo()
{
    PrimaryActorTick.bCanEverTick=true;
    Shirt=CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Shirt")); RootComponent=Shirt;
    Shirt->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Wetness=CreateDefaultSubobject<UStormfallShirtWetnessComponent>(TEXT("ShirtWetness"));
    Wetness->Garment=Shirt; Wetness->bReadWeatherCollection=false;
    Wetness->RainAbsorptionSeconds=6; Wetness->DryingSeconds=12;
}

void AStormfallShirtWeatherDemo::BeginPlay()
{
    Super::BeginPlay(); Wetness->AddTickPrerequisiteActor(this);
}

void AStormfallShirtWeatherDemo::Tick(float Dt)
{
    Super::Tick(Dt);
    if(Scenario==EStormfallShirtDemo::Rain)
    {
        if(auto* PC=GetWorld()->GetFirstPlayerController())
        {
            const bool Compare=PC->WasInputKeyJustPressed(EKeys::One);
            const bool Runtime=PC->WasInputKeyJustPressed(EKeys::Two);
            if(Compare || Runtime)
                for(TActorIterator<ACameraActor> It(GetWorld());It;++It)
                    if(It->ActorHasTag(Compare?TEXT("ShirtComparisonCamera"):TEXT("ShirtRuntimeCamera"))) PC->SetViewTargetWithBlend(*It,.35f);
        }
    }
    if(!bRunScenario) return;
    Elapsed+=Dt;
    const float Phase=FMath::Fmod(Elapsed,FMath::Max(1.f,ScenarioSeconds))/FMath::Max(1.f,ScenarioSeconds);
    Wetness->RainAmount=(Scenario==EStormfallShirtDemo::Rain || Scenario==EStormfallShirtDemo::Shelter) && Phase<.5f ? 1 : 0;
    if(Scenario==EStormfallShirtDemo::Water)
    {
        const auto P=Wetness->GetAnchorPositions();
        if(P.Num())
        {
            double Min=P[0].Z, Max=Min; for(const auto& V:P) { Min=FMath::Min(Min,V.Z); Max=FMath::Max(Max,V.Z); }
            const float Rise=FMath::Clamp(Phase*4.f,0.f,1.f);
            Wetness->SetWaterContact(Phase<.5f,FMath::Lerp(Min-5,Max+5,Rise));
        }
    }
    if(Scenario==EStormfallShirtDemo::Impacts)
    {
        const int32 Event=FMath::FloorToInt(Elapsed/2);
        if(Event!=ImpactEvent && Phase<.5f)
        {
            const auto P=Wetness->GetAnchorPositions();
            if(P.Num()==12) Wetness->AddWetImpact(P[(Event*7)%12],18,.6f);
        }
        ImpactEvent=Event;
    }
}
