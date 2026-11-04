#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/Paths.h"
#include "ShaderCore.h"
class FHissShadersModule : public IModuleInterface {
 void StartupModule() override { AddShaderSourceDirectoryMapping(TEXT("/Plugin/StormfallHiss"), FPaths::Combine(IPluginManager::Get().FindPlugin(TEXT("StormfallHiss"))->GetBaseDir(), TEXT("Shaders"))); }
};
IMPLEMENT_MODULE(FHissShadersModule, StormfallHissShaders)