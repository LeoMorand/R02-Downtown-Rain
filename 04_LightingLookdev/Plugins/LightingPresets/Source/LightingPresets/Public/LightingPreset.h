#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "LightingPreset.generated.h"

/** One actor a preset drives: a light, sky light, height fog or post process volume. */
USTRUCT(BlueprintType)
struct LIGHTINGPRESETS_API FLightingPresetEntry
{
	GENERATED_BODY()

	/** The actor's "LP:<Key>" tag, or its label when it has no such tag. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Entry")
	FName Key;

	/** Actor class name at capture time (PointLight, RectLight, ...). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Entry", meta = (EditCondition = "false"))  // shown greyed out; scripts still write it
	FString ActorClass;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Entry")
	bool bVisible = true;

	/** When false the actor is left where it is. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Entry")
	bool bApplyTransform = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Entry", meta = (EditCondition = "bApplyTransform"))
	FVector Location = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Entry", meta = (EditCondition = "bApplyTransform"))
	FRotator Rotation = FRotator::ZeroRotator;

	/** Component (or post process setting) property -> value as JSON text, e.g. "8e7", "[1,0.9,0.8,1]", "\"Lumens\"". */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Entry")
	TMap<FName, FString> Properties;

	/** Actor-level properties (post process volume: Enabled, Unbound, Priority ...), same encoding. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Entry")
	TMap<FName, FString> ActorProperties;
};

/**
 * A level's lighting as data: every light, sky light, height fog and post
 * process volume it drives, keyed so it can be applied to any level whose
 * actors carry the same keys. Captured and applied by the plugin's Python
 * (lighting_presets.core); this asset is its storage.
 */
UCLASS(BlueprintType)
class LIGHTINGPRESETS_API ULightingPreset : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	/** Data format version the entries were written with. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Preset", meta = (EditCondition = "false"))  // shown greyed out; scripts still write it
	int32 Version = 1;

	/** Level the preset was captured in (informational; it applies to any level). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Preset", meta = (AllowedClasses = "/Script/Engine.World"))
	FSoftObjectPath SourceLevel;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Preset", meta = (MultiLine = true))
	FString Notes;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Preset")
	TObjectPtr<UTexture2D> Thumbnail;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Preset", meta = (TitleProperty = "Key"))
	TArray<FLightingPresetEntry> Entries;

	virtual FPrimaryAssetId GetPrimaryAssetId() const override
	{
		return FPrimaryAssetId(TEXT("LightingPreset"), GetFName());
	}
};
