#include "MudRebuildActor.h"
#include "Modules/ModuleManager.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "NiagaraDataInterfaceArrayFunctionLibrary.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "Components/SkeletalMeshComponent.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"

IMPLEMENT_MODULE(FDefaultModuleImpl,MudRuntime)

AMudRebuildActor::AMudRebuildActor()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickGroup=TG_PostPhysics;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Simulation=CreateDefaultSubobject<UNiagaraComponent>(TEXT("Simulation"));
    Simulation->SetupAttachment(RootComponent);Simulation->SetAutoActivate(false);
    Simulation->AddTickPrerequisiteActor(this);
    Surface=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Surface"));
    Surface->SetupAttachment(RootComponent);Surface->SetCollisionProfileName(TEXT("BlockAll"));
    Surface->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Plane.Plane")));
    Surface->SetRelativeScale3D(FVector(20,20,1));
    Solver=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/MudStudy/Rebuild/Niagara/NS_Mud_FromScratch.NS_Mud_FromScratch"));
    SurfaceMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/MudStudy/Rebuild/Materials/MI_Surface_Rebuilt.MI_Surface_Rebuilt"));
}

void AMudRebuildActor::BeginPlay(){Super::BeginPlay();RebuildSimulation();}

void AMudRebuildActor::RebuildSimulation()
{
    History.Reset();PreviousInputCount=0;InputRandom.Initialize(InputRandomSeed);
    if(!Solver||!SurfaceMaterial)return;
    Output=NewObject<UTextureRenderTarget2D>(this);
    Output->bCanCreateUAV=true;Output->RenderTargetFormat=RTF_RGBA16f;
    Output->ClearColor=FLinearColor(0,0,1,1);Output->AddressX=TA_Clamp;Output->AddressY=TA_Clamp;
    Output->InitAutoFormat(OutputResolution,OutputResolution);Output->UpdateResourceImmediate(true);
    Simulation->SetAsset(Solver);Simulation->ReinitializeSystem();
    Simulation->SetVariableTextureRenderTarget(TEXT("User.OutputTexture"),Output);
    Simulation->SetVariablePosition(TEXT("User.SimCenter"),GetActorLocation());
    Simulation->SetVariableFloat(TEXT("User.BrushRandom"),BrushPositionRandom);
    Simulation->SetVariableFloat(TEXT("User.MotionOffset"),OffsetInMotionDirection);
    Simulation->SetVariableInt(TEXT("User.TrackingRandomSeed"),InputRandomSeed);
    SurfaceMID=UMaterialInstanceDynamic::Create(SurfaceMaterial,this);
    SurfaceMID->SetTextureParameterValue(TEXT("VelocityDensityBuffer"),Output);
    Surface->SetMaterial(0,SurfaceMID);
    Simulation->Activate(true);
}

void AMudRebuildActor::Tick(float Dt)
{
    Super::Tick(Dt);if(!Output||Dt<=SMALL_NUMBER)return;
    TArray<AActor*> Actors;for(AActor* A:BrushActors)if(IsValid(A))Actors.AddUnique(A);
    AActor* Player=TrackPlayer?UGameplayStatics::GetPlayerPawn(this,0):nullptr;
    if(Player)Actors.AddUnique(Player);
    TArray<FVector4> Positions,Previous,Velocities,WorldInputs;
    TSet<FName> Current;
    // Original runtime sets IgnoreSystemRotation: match its world-aligned transform.
    const FTransform Transform(FQuat::Identity,GetActorLocation());
    auto AddPoint=[&](FName Key,const FVector& World,float Size)
    {
        const FVector Local=Transform.InverseTransformPositionNoScale(World);
        const FVector Unit(Local.X/2000+0.5,Local.Y/2000+0.5,Local.Z/2000+0.5);
        if(FMath::Abs(Unit.X-0.5)>0.6||FMath::Abs(Unit.Y-0.5)>0.6||FMath::Abs(Local.Z)>100)return;
        Current.Add(Key);
        WorldInputs.Add(FVector4(World,Size));
        FBrushHistory* Old=History.Find(Key);FBrushHistory New;
        New.World=World;New.Age=Old?Old->Age+Dt:0;
        FVector V=Old?Transform.InverseTransformVectorNoScale((World-Old->World)/Dt)*0.0005:FVector::ZeroVector;
        if(New.Age<0.25)V=FVector::ZeroVector;
        New.Velocity=V; // Previous.UnitVelocity stores the unguarded source velocity.
        FVector ModifiedUnit=Unit;
        if(V.Length()<1)ModifiedUnit+=FVector(V.X,V.Y,0)*(60.0*OffsetInMotionDirection/2000.0);
        const float RandomWidth=BrushPositionRandom*(20.0f/2000.0f);
        const float RandomScale=FMath::Clamp(FVector2D(V.X*5,V.Y*5).Length(),0.0,1.0);
        ModifiedUnit.X+=(InputRandom.FRand()-0.5f)*RandomWidth*RandomScale;
        ModifiedUnit.Y+=(InputRandom.FRand()-0.5f)*RandomWidth*RandomScale;
        New.ModifiedUnit=ModifiedUnit;
        if(Old&&(V-Old->Velocity).Length()>=1)V=FVector::ZeroVector;
        const FVector PrevUnit=Old?Old->ModifiedUnit:ModifiedUnit;
        Positions.Add(FVector4(ModifiedUnit,Size));Previous.Add(FVector4(PrevUnit,Size));Velocities.Add(FVector4(V,New.Age));
        History.Add(Key,New);
    };
    for(AActor* A:Actors)
    {
        bool UsedBones=false;
        if(TrackPhysicsBones)
        {
            TInlineComponentArray<USkeletalMeshComponent*> Meshes(A);
            for(USkeletalMeshComponent* Mesh:Meshes)
            {
                UPhysicsAsset* Physics=Mesh->GetPhysicsAsset();if(!Physics)continue;
                for(const USkeletalBodySetup* Body:Physics->SkeletalBodySetups)
                {
                    if(!Body)continue;const FName Bone=Body->BoneName;
                    const FVector World=Mesh->GetSocketLocation(Bone);
                    const FVector Parent=Mesh->GetSocketLocation(Mesh->GetParentBone(Bone));
                    // Selected Blueprint: parent-bone distance * .05 * SkeletalMeshBrushSize(.5).
                    const float Size=FVector::Distance(World,Parent)*0.025f;
                    if(Size>SMALL_NUMBER)AddPoint(FName(Mesh->GetPathName()+TEXT(":")+Bone.ToString()),World,Size);
                    UsedBones=true;
                }
            }
        }
        if(!UsedBones)
        {
            TInlineComponentArray<UPrimitiveComponent*> Components(A);
            for(UPrimitiveComponent* Component:Components)
            {
                if(!Component||!Component->IsCollisionEnabled())continue;
                const float Radius=Component->Bounds.SphereRadius;
                const float Size=UseObjectBounds?Radius*0.07f:(A==Player?PlayerBrushSize:ObjectBrushSize);
                // Selected Blueprint: primitive pivot shifted by radius * -.6 * .5.
                const FVector World=Component->GetComponentLocation()-FVector(0,0,Radius*0.3f);
                AddPoint(FName(Component->GetPathName()),World,Size);
            }
        }
    }
    for(auto It=History.CreateIterator();It;++It)if(!Current.Contains(It.Key()))It.RemoveCurrent();
    if(Positions.Num()!=PreviousInputCount)
    {
        Previous=Positions;for(FVector4& V:Velocities){V.X=0;V.Y=0;V.Z=0;}
    }
    PreviousInputCount=Positions.Num();
    UNiagaraDataInterfaceArrayFunctionLibrary::SetNiagaraArrayVector4(Simulation,TEXT("User.BrushWorldPositions"),WorldInputs);
    UNiagaraDataInterfaceArrayFunctionLibrary::SetNiagaraArrayVector4(Simulation,TEXT("User.BrushPositions"),Positions);
    UNiagaraDataInterfaceArrayFunctionLibrary::SetNiagaraArrayVector4(Simulation,TEXT("User.BrushPrevious"),Previous);
    UNiagaraDataInterfaceArrayFunctionLibrary::SetNiagaraArrayVector4(Simulation,TEXT("User.BrushVelocities"),Velocities);
}
