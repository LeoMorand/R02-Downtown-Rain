using UnrealBuildTool;
public class MudAuthoring : ModuleRules
{
    public MudAuthoring(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage=PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[]{"Core","CoreUObject","Engine"});
        PrivateDependencyModuleNames.AddRange(new[]{"UnrealEd","AssetTools","Json","Niagara","NiagaraCore","NiagaraEditor"});
    }
}
