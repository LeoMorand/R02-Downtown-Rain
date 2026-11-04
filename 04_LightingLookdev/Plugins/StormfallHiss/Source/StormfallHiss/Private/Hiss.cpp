#include "Modules/ModuleManager.h"
#include "SceneViewExtension.h"
#include "SceneView.h"
#include "SceneInterface.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "Misc/CoreDelegates.h"
#include "Misc/ScopeLock.h"
#include "HAL/IConsoleManager.h"
#include "PostProcess/PostProcessMaterialInputs.h"
#include "HissPass.h"
#include "StormfallHissVolume.h"
static TAutoConsoleVariable<int32> HissEnabled(TEXT("r.Stormfall.Hiss"),1,TEXT("Master switch; actor still defaults disabled"),ECVF_RenderThreadSafe);
static TAutoConsoleVariable<float> HissIntensity(TEXT("r.Stormfall.Hiss.Intensity"),1.f,TEXT("Multiplier on actor intensity; zero bypasses shader exactly"),ECVF_RenderThreadSafe);
static TAutoConsoleVariable<float> HissTime(TEXT("r.Stormfall.Hiss.Time"),-1.f,TEXT("Negative: live time; otherwise fixed shader seconds for QA"),ECVF_RenderThreadSafe);
static TAutoConsoleVariable<int32> HissDebug(TEXT("r.Stormfall.Hiss.DebugRed"),0,TEXT("L1 red tint diagnostic, still requires enabled actor"),ECVF_RenderThreadSafe);
struct FHissFamilyKey {
 const FSceneInterface* Scene;
 const FRenderTarget* Target;
 uint32 Frame;
 explicit FHissFamilyKey(const FSceneViewFamily& F):Scene(F.Scene),Target(F.RenderTarget),Frame(F.FrameNumber) {}
 bool operator==(const FHissFamilyKey& B) const {return Scene==B.Scene && Target==B.Target && Frame==B.Frame;}
 friend uint32 GetTypeHash(const FHissFamilyKey& K) {return HashCombine(HashCombine(PointerHash(K.Scene),PointerHash(K.Target)),::GetTypeHash(K.Frame));}
};
struct FHissEntry {FHissSnapshot Values;uint64 CreatedAt;};
class FStormfallHissExtension : public FSceneViewExtensionBase {
 FCriticalSection Mutex;
 TMap<FHissFamilyKey,FHissEntry> Families;
public:
 FStormfallHissExtension(const FAutoRegister& R):FSceneViewExtensionBase(R) {}
 void SetupViewFamily(FSceneViewFamily&) override {}
 void BeginRenderViewFamily(FSceneViewFamily& Family) override {
  check(IsInGameThread());
  FHissSnapshot S;
  UWorld* World=Family.Scene?Family.Scene->GetWorld():nullptr;
  AStormfallHissVolume* Selected=nullptr;
  if(World) for(TActorIterator<AStormfallHissVolume> It(World);It;++It) {
   // One enabled volume per world is the intended workflow. Stable tie-break.
   if(It->bEnabled && (!Selected || It->GetPathName()<Selected->GetPathName())) Selected=*It;
  }
  if(Selected) {
   S.bEnabled=true;
   auto Safe=[](float V,float Fallback){return FMath::IsFinite(V)?V:Fallback;};
   S.Intensity=FMath::Clamp(Safe(Selected->Intensity,0.f),0.f,1.f)*FMath::Clamp(Safe(HissIntensity.GetValueOnGameThread(),0.f),0.f,1.f);
   S.EdgeThreshold=FMath::Clamp(Safe(Selected->EdgeThreshold,0.035f),0.0001f,1.f);
   S.EdgeColor=Selected->EdgeColor;
   S.ChromaticAberration=FMath::Clamp(Safe(Selected->ChromaticAberration,0.f),0.f,10.f);
   S.ErosionNear=FMath::Max(0.f,Safe(Selected->ErosionNear,400.f));
   S.ErosionFar=FMath::Max(S.ErosionNear+1.f,Safe(Selected->ErosionFar,2500.f));
   S.ErosionColor=Selected->ErosionColor;
   S.ScanlineDensity=FMath::Clamp(Safe(Selected->ScanlineDensity,110.f),1.f,1080.f);
  }
  S.bDebugRed=HissDebug.GetValueOnGameThread()!=0;
  S.Time=HissTime.GetValueOnGameThread()>=0.f?HissTime.GetValueOnGameThread():float(Family.Time.GetWorldTimeSeconds());
  FScopeLock Lock(&Mutex);
    // Renderer copies FSceneViewFamily; its address is not a cross-thread identity.
  // FrameNumber is assigned before BeginRenderViewFamily and copied unchanged.
  for(auto It=Families.CreateIterator();It;++It) if(It.Value().CreatedAt+64<Family.FrameCounter) It.RemoveCurrent();
  Families.Add(FHissFamilyKey(Family),FHissEntry{S,Family.FrameCounter});
 }
 void SetupView(FSceneViewFamily&,FSceneView&) override {}

 bool IsActiveThisFrame_Internal(const FSceneViewExtensionContext&) const override { return HissEnabled.GetValueOnGameThread()!=0; }
 void SubscribeToPostProcessingPass(EPostProcessingPass Pass,const FSceneView& View,FPostProcessingPassDelegateArray& Callbacks,bool bPassEnabled) override {
  if(Pass!=EPostProcessingPass::Tonemap || !bPassEnabled || View.GetFeatureLevel()<ERHIFeatureLevel::SM5) return;
  FHissSnapshot Snapshot;
  { FScopeLock Lock(&Mutex); if(const FHissEntry* Found=Families.Find(FHissFamilyKey(*View.Family))) Snapshot=Found->Values; }
  if(!Snapshot.bEnabled || Snapshot.Intensity<=0.f) return;
  Callbacks.Add(FPostProcessingPassDelegate::CreateLambda([Snapshot](FRDGBuilder& Graph,const FSceneView& V,const FPostProcessMaterialInputs& Inputs){ return AddHissPass(Graph,V,Inputs,Snapshot); }));
 }

};
class FHissModule : public IModuleInterface {
 TSharedPtr<FStormfallHissExtension,ESPMode::ThreadSafe> Extension;
 FDelegateHandle InitHandle;
 void Create() { if(!Extension) Extension=FSceneViewExtensions::NewExtension<FStormfallHissExtension>(); }
 void StartupModule() override { if(GEngine) Create(); else InitHandle=FCoreDelegates::GetOnPostEngineInit().AddRaw(this,&FHissModule::Create); }
 void ShutdownModule() override { FCoreDelegates::GetOnPostEngineInit().Remove(InitHandle); Extension.Reset(); }
};
IMPLEMENT_MODULE(FHissModule,StormfallHiss)
