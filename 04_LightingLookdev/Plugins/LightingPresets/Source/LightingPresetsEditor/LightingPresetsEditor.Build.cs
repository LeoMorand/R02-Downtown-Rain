using UnrealBuildTool;

public class LightingPresetsEditor : ModuleRules
{
	public LightingPresetsEditor(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PrivateDependencyModuleNames.AddRange(new[]
		{
			"Core", "CoreUObject", "Engine", "Slate", "SlateCore", "InputCore",
			"UnrealEd", "LevelEditor", "WorkspaceMenuStructure", "PythonScriptPlugin", "LightingPresets", "Json"
		});
	}
}
