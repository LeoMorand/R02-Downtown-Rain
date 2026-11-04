#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "LightingPresetRenderLibrary.generated.h"

/** Temporary viewport state needed by asynchronous preset screenshots. */
UCLASS()
class LIGHTINGPRESETSEDITOR_API ULightingPresetRenderLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** Keep the screenshot viewport ticking; false removes only our override. */
	UFUNCTION(BlueprintCallable, Category = "Lighting Presets")
	static bool SetRenderRealtime(bool bEnabled);

	UFUNCTION(BlueprintPure, Category = "Lighting Presets")
	static bool IsViewportRealtime();

	/** Process a pending screenshot even when the editor window is in the background. */
	UFUNCTION(BlueprintCallable, Category = "Lighting Presets")
	static void DrawRenderViewport();

	/** Configure the real panel's checkboxes and resolution; does not start a render. */
	UFUNCTION(BlueprintCallable, Category = "Lighting Presets")
	static bool ConfigurePanelRender(const TArray<FString>& PresetNames, const TArray<FString>& CameraNames,
		int32 Width, int32 Height);

	/** Read back the real panel's render selection, resolution and progress as JSON. */
	UFUNCTION(BlueprintCallable, Category = "Lighting Presets")
	static FString GetPanelRenderConfiguration();

	/** Fix the active viewport's actual render size for GPU measurements; 0,0 restores automatic sizing. */
	UFUNCTION(BlueprintCallable, Category = "Lighting Presets")
	static bool SetFixedRenderViewportSize(int32 Width, int32 Height);

	UFUNCTION(BlueprintPure, Category = "Lighting Presets")
	static FIntPoint GetRenderViewportSize();

	/** Select a preset and filter visible parameter rows for panel review. */
	UFUNCTION(BlueprintCallable, Category = "Lighting Presets")
	static bool SelectPanelPresetForReview(const FString& PresetName, const FString& Filter);
};
