#include "LightingPresetRenderLibrary.h"

#include "LevelEditor.h"
#include "Modules/ModuleManager.h"
#include "SLevelViewport.h"
#include "UnrealClient.h"
#include "Framework/Docking/TabManager.h"
#include "SLightingPresetsPanel.h"
#include "Widgets/Docking/SDockTab.h"
#include "Slate/SceneViewport.h"

namespace
{
	TWeakPtr<SLevelViewport> RenderViewport;
	const FText RenderOverrideName = NSLOCTEXT("LightingPresets", "RenderRealtime", "Lighting Presets Render");
}

bool ULightingPresetRenderLibrary::SetRenderRealtime(bool bEnabled)
{
	if (TSharedPtr<SLevelViewport> Previous = RenderViewport.Pin())
	{
		Previous->GetLevelViewportClient().RemoveRealtimeOverride(RenderOverrideName, false);
	}
	RenderViewport.Reset();
	if (!bEnabled) return true;

	FLevelEditorModule* Module = FModuleManager::GetModulePtr<FLevelEditorModule>("LevelEditor");
	TSharedPtr<SLevelViewport> Viewport = Module ? Module->GetFirstActiveLevelViewport() : nullptr;
	if (!Viewport.IsValid()) return false;
	Viewport->GetLevelViewportClient().AddRealtimeOverride(true, RenderOverrideName);
	Viewport->GetLevelViewportClient().Invalidate();
	RenderViewport = Viewport;
	return true;
}

bool ULightingPresetRenderLibrary::IsViewportRealtime()
{
	FLevelEditorModule* Module = FModuleManager::GetModulePtr<FLevelEditorModule>("LevelEditor");
	TSharedPtr<SLevelViewport> Viewport = Module ? Module->GetFirstActiveLevelViewport() : nullptr;
	return Viewport.IsValid() && Viewport->GetLevelViewportClient().IsRealtime();
}

void ULightingPresetRenderLibrary::DrawRenderViewport()
{
	if (TSharedPtr<SLevelViewport> Viewport = RenderViewport.Pin())
	{
		if (FViewport* SceneViewport = Viewport->GetActiveViewport())
		{
			SceneViewport->Draw(false);
		}
	}
}

bool ULightingPresetRenderLibrary::ConfigurePanelRender(const TArray<FString>& PresetNames,
	const TArray<FString>& CameraNames, int32 Width, int32 Height)
{
	TSharedPtr<SDockTab> Tab = FGlobalTabmanager::Get()->TryInvokeTab(FName("LightingPresets"));
	return Tab.IsValid() && StaticCastSharedRef<SLightingPresetsPanel>(Tab->GetContent())->ConfigureRender(
		PresetNames, CameraNames, Width, Height);
}

FString ULightingPresetRenderLibrary::GetPanelRenderConfiguration()
{
	TSharedPtr<SDockTab> Tab = FGlobalTabmanager::Get()->TryInvokeTab(FName("LightingPresets"));
	return Tab.IsValid() ? StaticCastSharedRef<SLightingPresetsPanel>(Tab->GetContent())->RenderConfigurationJson()
		: TEXT("{}");
}

bool ULightingPresetRenderLibrary::SetFixedRenderViewportSize(int32 Width, int32 Height)
{
	if (!((Width == 0 && Height == 0) || (Width > 0 && Height > 0 && Width <= 8192 && Height <= 8192))) return false;
	FLevelEditorModule* Module = FModuleManager::GetModulePtr<FLevelEditorModule>("LevelEditor");
	TSharedPtr<SLevelViewport> Viewport = Module ? Module->GetFirstActiveLevelViewport() : nullptr;
	if (!Viewport.IsValid() || !Viewport->GetActiveViewport()) return false;
	static_cast<FSceneViewport*>(Viewport->GetActiveViewport())->SetFixedViewportSize(Width, Height);
	Viewport->GetLevelViewportClient().Invalidate();
	return true;
}

FIntPoint ULightingPresetRenderLibrary::GetRenderViewportSize()
{
	FLevelEditorModule* Module = FModuleManager::GetModulePtr<FLevelEditorModule>("LevelEditor");
	TSharedPtr<SLevelViewport> Viewport = Module ? Module->GetFirstActiveLevelViewport() : nullptr;
	return Viewport.IsValid() && Viewport->GetActiveViewport() ? Viewport->GetActiveViewport()->GetSizeXY() : FIntPoint::ZeroValue;
}

bool ULightingPresetRenderLibrary::SelectPanelPresetForReview(const FString& PresetName, const FString& Filter)
{
	TSharedPtr<SDockTab> Tab = FGlobalTabmanager::Get()->TryInvokeTab(FName("LightingPresets"));
	return Tab.IsValid() && StaticCastSharedRef<SLightingPresetsPanel>(Tab->GetContent())->SelectForReview(PresetName, Filter);
}
