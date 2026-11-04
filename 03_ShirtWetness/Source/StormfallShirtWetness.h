#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameFramework/Actor.h"
#include "StormfallShirtWetness.generated.h"

class USkeletalMeshComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UMaterialParameterCollection;
class UBoxComponent;

namespace StormfallWetness
{
    // Exact solution of dW/dt = input*(1-W) - evaporation*W.
    STORMFALL_API float Integrate(float Wetness, float InputRate, float EvaporationRate, float Seconds);
    STORMFALL_API void Diffuse(TArray<float>& Values, const TArray<FVector>& RestPositions, float Rate, float Seconds, float Radius);
}

USTRUCT(BlueprintType)
struct FStormfallWetnessAnchor
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wetness") FName Bone;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wetness", meta=(Units="cm")) FVector BoneOffset = FVector::ZeroVector;
};

USTRUCT(BlueprintType)
struct FStormfallWetnessSnapshot
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category="Wetness") int32 Version = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category="Wetness") TArray<float> Values;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category="Wetness") TArray<FName> Bones;
};

/** A bounded water region. The box top is its water surface, including actor rotation/scale. */
UCLASS()
class STORMFALL_API AStormfallShirtWaterZone : public AActor
{
    GENERATED_BODY()
public:
    AStormfallShirtWaterZone();
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Water") TObjectPtr<UBoxComponent> WaterBounds;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Water", meta=(ClampMin="0",ClampMax="1")) float Absorption = 1;
    UFUNCTION(BlueprintPure, Category="Water") float SampleWater(FVector WorldPosition, float FeatherCm = 3) const;
};

/** Twelve bone-bound wetness cells: persistent absorption, shelter, water, diffusion and impact history.
 * Owns only garment MIDs. Does not change the shared mesh, material assets or global weather. */
UCLASS(ClassGroup=(Stormfall), meta=(BlueprintSpawnableComponent))
class STORMFALL_API UStormfallShirtWetnessComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UStormfallShirtWetnessComponent();
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Binding") TObjectPtr<USkeletalMeshComponent> Garment;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Binding") TArray<FStormfallWetnessAnchor> Anchors;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Weather") TObjectPtr<UMaterialParameterCollection> WeatherCollection;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Weather") FName RainParameter = TEXT("RainAmount");
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Weather") FName HumidityParameter = TEXT("Humidity");
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Weather") bool bReadWeatherCollection = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Weather", meta=(ClampMin="0",ClampMax="1")) float RainAmount = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Weather", meta=(ClampMin="0",ClampMax="1")) float AirHumidity = .4f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Weather") FVector RainDirection = FVector(0,0,-1);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Shelter") bool bTraceShelter = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Shelter") TEnumAsByte<ECollisionChannel> ShelterChannel = ECC_Visibility;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Shelter", meta=(ClampMin="10",Units="cm")) float ShelterTraceLength = 2000;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Shelter", meta=(ClampMin="0.02",ClampMax="2",Units="s")) float EnvironmentInterval = .2f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Response", meta=(ClampMin="0",ClampMax="1")) float InitialWetness = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Response", meta=(ClampMin="0.1",Units="s")) float RainAbsorptionSeconds = 18;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Response", meta=(ClampMin="0.1",Units="s")) float WaterAbsorptionSeconds = 1.5f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Response", meta=(ClampMin="0.1",Units="s")) float DryingSeconds = 90;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Response", meta=(ClampMin="0",ClampMax="10",ToolTip="Diffusion rate per second on the bone-anchor graph.")) float DiffusionRate = .08f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Response", meta=(ClampMin="1",Units="cm")) float DiffusionRadius = 28;
    // External Water plugin/gameplay adapters can call SetWaterContact; water zones also work automatically.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Water") bool bUseExternalWaterPlane = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Water", meta=(Units="cm")) float WaterSurfaceZ = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Water", meta=(ClampMin="0",ClampMax="1")) float WaterContact = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Preview") bool bManualPreview = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Preview", meta=(ClampMin="0",ClampMax="1")) float PreviewWetness = .5f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Debug") bool bDrawDebug = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Cloth", meta=(ToolTip="Controls existing Chaos cloth only. Requires authored cloth assets; does not create geometry or change mass.")) bool bDriveClothResponse = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Cloth", meta=(ClampMin="0",ClampMax="1")) float DryClothDamping = .08f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Cloth", meta=(ClampMin="0",ClampMax="1")) float WetClothDamping = .3f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Cloth", meta=(ClampMin="0",ClampMax="1")) float DryAnimDrive = .15f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Shirt Wetness|Cloth", meta=(ClampMin="0",ClampMax="1")) float WetAnimDrive = .45f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="Shirt Wetness|State") float AverageWetness = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="Shirt Wetness|State") float RainExposure = 1;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="Shirt Wetness|State") int32 MaterialCount = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="Shirt Wetness|State") FString BindingStatus;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="Shirt Wetness|State") int32 DrivenClothCount = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="Shirt Wetness|State") TArray<float> WetnessValues;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="Shirt Wetness|State") TArray<float> ExposureValues;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="Shirt Wetness|State") TArray<float> ImmersionValues;
    UFUNCTION(BlueprintCallable, Category="Shirt Wetness") bool InitializeGarment();
    UFUNCTION(BlueprintCallable, Category="Shirt Wetness") void SetUniformWetness(float Value);
    UFUNCTION(BlueprintCallable, Category="Shirt Wetness") void AddWetImpact(FVector WorldPosition, float RadiusCm = 12, float Amount = .25f);
    UFUNCTION(BlueprintCallable, Category="Shirt Wetness") void SetWaterContact(bool bActive, float SurfaceZ, float Contact = 1);
    UFUNCTION(BlueprintPure, Category="Shirt Wetness") FStormfallWetnessSnapshot CaptureWetness() const;
    UFUNCTION(BlueprintCallable, Category="Shirt Wetness") bool RestoreWetness(const FStormfallWetnessSnapshot& Snapshot);
    UFUNCTION(BlueprintCallable, Category="Shirt Wetness") void RefreshEnvironment();
    UFUNCTION(BlueprintCallable, Category="Shirt Wetness") void AdvanceWetness(float Seconds);
    UFUNCTION(BlueprintCallable, Category="Shirt Wetness") void ApplyToMaterials();
    UFUNCTION(BlueprintPure, Category="Shirt Wetness") TArray<FVector> GetAnchorPositions() const;
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
private:
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInterface>> OriginalMaterials;
    TArray<int32> MaterialSlots;
    TArray<FVector> RestPositions;
    float EnvironmentElapsed = 0;
    bool bInitialized = false;
    bool bWaitingForCloth = false;
    bool bOriginalClothWait = false;
};

UENUM(BlueprintType)
enum class EStormfallShirtDemo : uint8 { Rain, Shelter, Water, Impacts };

/** Runtime demonstration actors alongside the original static comparison row. */
UCLASS()
class STORMFALL_API AStormfallShirtWeatherDemo : public AActor
{
    GENERATED_BODY()
public:
    AStormfallShirtWeatherDemo();
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Demo") TObjectPtr<USkeletalMeshComponent> Shirt;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Demo") TObjectPtr<UStormfallShirtWetnessComponent> Wetness;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Demo") EStormfallShirtDemo Scenario = EStormfallShirtDemo::Rain;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Demo") bool bRunScenario = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Demo", meta=(ClampMin="1",Units="s")) float ScenarioSeconds = 48;
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
private:
    double Elapsed = 0;
    int32 ImpactEvent = -1;
};
