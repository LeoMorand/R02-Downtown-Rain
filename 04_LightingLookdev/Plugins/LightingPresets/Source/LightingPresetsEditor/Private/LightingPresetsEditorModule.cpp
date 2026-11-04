#include "Framework/Docking/TabManager.h"
#include "Modules/ModuleManager.h"
#include "SLightingPresetsPanel.h"
#include "Widgets/Docking/SDockTab.h"
#include "WorkspaceMenuStructure.h"
#include "WorkspaceMenuStructureModule.h"

#define LOCTEXT_NAMESPACE "LightingPresetsEditor"

static const FName LightingPresetsTab(TEXT("LightingPresets"));

class FLightingPresetsEditorModule : public IModuleInterface
{
public:
	virtual void StartupModule() override
	{
		FGlobalTabmanager::Get()->RegisterNomadTabSpawner(LightingPresetsTab,
			FOnSpawnTab::CreateLambda([](const FSpawnTabArgs&)
			{
				return SNew(SDockTab).TabRole(ETabRole::NomadTab)[SNew(SLightingPresetsPanel)];
			}))
			.SetDisplayName(LOCTEXT("TabTitle", "Lighting Presets"))
			.SetTooltipText(LOCTEXT("TabTip", "Capture, apply and compare the level's lighting as presets"))
			.SetGroup(WorkspaceMenu::GetMenuStructure().GetLevelEditorCategory())
			.SetIcon(FSlateIcon(FAppStyle::GetAppStyleSetName(), "ClassIcon.DirectionalLight"));
	}

	virtual void ShutdownModule() override
	{
		if (FSlateApplication::IsInitialized())
		{
			FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(LightingPresetsTab);
		}
	}
};

IMPLEMENT_MODULE(FLightingPresetsEditorModule, LightingPresetsEditor)

#undef LOCTEXT_NAMESPACE
