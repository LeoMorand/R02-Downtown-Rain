using UnrealBuildTool;

public class MudShaderIntegration : ModuleRules
{
    public MudShaderIntegration(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "MudRuntime" });
        PrivateDependencyModuleNames.AddRange(new[] { "MudShaderLab", "Niagara", "RenderCore", "RHI" });
    }
}
