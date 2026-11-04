using UnrealBuildTool;
using System.IO;
public class StormfallHiss : ModuleRules { public StormfallHiss(ReadOnlyTargetRules Target) : base(Target) { PCHUsage=PCHUsageMode.UseExplicitOrSharedPCHs; PublicDependencyModuleNames.AddRange(new[]{"Core","CoreUObject","Engine"}); PrivateDependencyModuleNames.AddRange(new[]{"StormfallHissShaders","RenderCore","Renderer","RHI","Projects"});  } }