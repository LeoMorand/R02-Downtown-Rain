using UnrealBuildTool;
public class MudRuntime : ModuleRules
{
    public MudRuntime(ReadOnlyTargetRules Target):base(Target)
    {
        PCHUsage=PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[]{"Core","CoreUObject","Engine","Niagara"});
    }
}
