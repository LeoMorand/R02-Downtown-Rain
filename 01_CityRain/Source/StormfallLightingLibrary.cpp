#include "StormfallLightingLibrary.h"

#include "Engine/Engine.h"
#include "Engine/Level.h"
#include "Engine/LevelStreaming.h"
#include "Engine/World.h"

#if WITH_EDITOR
#include "EditorLevelUtils.h"
#endif

namespace
{
    const FName DayLevel(TEXT("/Game/Downtown_West/Maps/Sub-Levels/Daytime_Lighting"));
    const FName NightLevel(TEXT("/Game/Downtown_West/Maps/Sub-Levels/Nightime_Lighting"));
}

void UStormfallLightingLibrary::SetNightLighting(const UObject* WorldContextObject, bool bNight)
{
    UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::ReturnNull) : nullptr;
    if (!World)
    {
        return;
    }
    for (ULevelStreaming* Streaming : World->GetStreamingLevels())
    {
        if (!Streaming)
        {
            continue;
        }
        // In PIE the streaming package is renamed (.../UEDPIE_0_Daytime_Lighting): strip the prefix.
        const FName Package(*UWorld::RemovePIEPrefix(Streaming->GetWorldAssetPackageName()));
        const bool bIsDay = Package == DayLevel;
        if (!bIsDay && Package != NightLevel)
        {
            continue;
        }
        const bool bVisible = bIsDay ? !bNight : bNight;
        if (World->IsGameWorld())
        {
            if (Streaming->ShouldBeVisible() != bVisible)
            {
                Streaming->SetShouldBeLoaded(true);
                Streaming->SetShouldBeVisible(bVisible);
            }
            continue;
        }
#if WITH_EDITOR
        ULevel* Level = Streaming->GetLoadedLevel();
        if (Level && Level->bIsVisible != bVisible)
        {
            // Code-driven change: do not mark the map dirty or add an undo step.
            UEditorLevelUtils::SetLevelVisibility(Level, bVisible, false, ELevelVisibilityDirtyMode::DontModify);
        }
#endif
    }
}
