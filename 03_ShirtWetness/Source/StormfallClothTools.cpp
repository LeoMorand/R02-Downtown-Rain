#include "StormfallClothTools.h"
#include "Engine/SkeletalMesh.h"
#if WITH_EDITOR
#include "ClothingAssetFactory.h"
#include "ClothingAsset.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "ChaosCloth/ChaosClothConfig.h"
#endif
FString UStormfallClothTools::BuildHemCloth(USkeletalMesh* Mesh){
#if WITH_EDITOR
 if(!Mesh || !Mesh->GetImportedModel() || Mesh->GetImportedModel()->LODModels.Num()==0)return TEXT("ERROR: missing mesh");
 if(Mesh->GetMeshClothingAssets().Num())return TEXT("EXISTS: preserve existing clothing");
 auto& LOD=Mesh->GetImportedModel()->LODModels[0];
 int32 Section=INDEX_NONE;float Highest=-FLT_MAX;
 for(int32 I=0;I<LOD.Sections.Num();++I){
  float Top=-FLT_MAX;for(const auto& V:LOD.Sections[I].SoftVertices)Top=FMath::Max(Top,V.Position.Z);
  if(Top>Highest){Highest=Top;Section=I;}
 }
 if(Section==INDEX_NONE)return TEXT("ERROR: no shirt section");
 FSkeletalMeshClothBuildParams Params;Params.AssetName=TEXT("SF_ShirtHem");Params.LodIndex=0;
 Params.SourceSection=Section;Params.bRemoveFromMesh=false;
 Params.PhysicsAsset=LoadObject<UPhysicsAsset>(nullptr,TEXT("/Game/MetaHumans/MC_Stormfall/Body/PHYS_MC_Stormfall"));
 auto* Asset=Cast<UClothingAssetCommon>(NewObject<UClothingAssetFactory>()->CreateFromSkeletalMesh(Mesh,Params));
 if(!Asset || Asset->LodData.IsEmpty())return TEXT("ERROR: cloth extraction failed");
 auto& Data=Asset->LodData[0];const auto& Vertices=Data.PhysicalMeshData.Vertices;
 float Bottom=FLT_MAX,Top=-FLT_MAX;for(auto V:Vertices){Bottom=FMath::Min(Bottom,V.Z);Top=FMath::Max(Top,V.Z);}
 Data.PointWeightMaps.Reset();FPointWeightMap Mask(Vertices.Num());Mask.Name=TEXT("Hem_MaxDistance_cm");
 Mask.CurrentTarget=(uint8)EWeightMapTargetCommon::MaxDistance;Mask.bEnabled=true;
 int32 Movable=0;for(int32 I=0;I<Vertices.Num();++I){
  // Pin the torso and sleeves. Fade to 2.5 cm of travel across the lower 22% of the shirt.
  Mask.Values[I]=2.5f*(1-FMath::SmoothStep(Bottom,Bottom+(Top-Bottom)*.22f,Vertices[I].Z));
  if(Mask.Values[I]>.01f)++Movable;
 }
 Data.PointWeightMaps.Add(MoveTemp(Mask));Asset->ApplyParameterMasks(true);
 Mesh->AddClothingAsset(Asset);
 if(!Asset->BindToSkeletalMesh(Mesh,0,Section,0))return TEXT("ERROR: cloth binding failed");
 Mesh->PostEditChange();Mesh->MarkPackageDirty();
 return FString::Printf(TEXT("OK: section=%d vertices=%d movable=%d max_distance_cm=2.5 collision=%s"),Section,Vertices.Num(),Movable,Asset->PhysicsAsset?TEXT("yes"):TEXT("no"));
#else
 return TEXT("ERROR: editor-only operation");
#endif
}

FString UStormfallClothTools::BuildWetShirtHem(USkeletalMesh* Mesh)
{
#if WITH_EDITOR
 // Operate only on the dedicated production copy; never rebuild original garment assets.
 if(!Mesh || !Mesh->GetPathName().StartsWith(TEXT("/Game/Stormfall/ShirtTrial/Wetness/Physics/"))) return TEXT("ERROR: requires dedicated Wetness/Physics mesh copy");
 if(!Mesh->GetImportedModel() || Mesh->GetImportedModel()->LODModels.IsEmpty()) return TEXT("ERROR: no imported LOD");
 if(!Mesh->GetMeshClothingAssets().IsEmpty()) return FinalizeWetShirtHem(Mesh);
 if(!Mesh->GetPhysicsAsset()) return TEXT("ERROR: compatible body collision PhysicsAsset required");
 auto& LOD=Mesh->GetImportedModel()->LODModels[0];
 const int32 ProxyLOD=Mesh->GetImportedModel()->LODModels.Num()>1?1:0;
 const auto& Proxy=Mesh->GetImportedModel()->LODModels[ProxyLOD];
 TArray<int32> Sections;
 for(int32 I=0;I<LOD.Sections.Num();++I)
 {
  const int32 M=LOD.Sections[I].MaterialIndex;
  if(!Mesh->GetMaterials().IsValidIndex(M)) continue;
  const FString Slot=Mesh->GetMaterials()[M].MaterialSlotName.ToString();
  if(Slot==TEXT("MS_Shirt_Front") || Slot==TEXT("MS_Shirt_Back")) Sections.Add(I);
 }
 if(Sections.Num()!=2) return TEXT("ERROR: expected exactly Front and Back garment sections");
 FScopedSkeletalMeshPostEditChange Scope(Mesh);
 FString Report;
 for(int32 Section:Sections)
 {
  int32 ProxySection=INDEX_NONE;
  for(int32 I=0;I<Proxy.Sections.Num();++I)
   if(Proxy.Sections[I].MaterialIndex==LOD.Sections[Section].MaterialIndex) {ProxySection=I;break;}
  if(ProxySection==INDEX_NONE) return TEXT("ERROR: garment section missing in simulation proxy");
  FSkeletalMeshClothBuildParams Params; Params.AssetName=FString::Printf(TEXT("SF_WetShirtHem_%d"),Section);
  Params.LodIndex=ProxyLOD; Params.SourceSection=ProxySection; Params.bRemoveFromMesh=false; Params.PhysicsAsset=Mesh->GetPhysicsAsset();
  auto* Asset=Cast<UClothingAssetCommon>(NewObject<UClothingAssetFactory>()->CreateFromSkeletalMesh(Mesh,Params));
  if(!Asset || Asset->LodData.IsEmpty()) return TEXT("ERROR: cloth extraction failed; inspect dedicated copy");
  auto& Data=Asset->LodData[0]; const auto& V=Data.PhysicalMeshData.Vertices;
  float Bottom=FLT_MAX,Top=-FLT_MAX; for(auto P:V) {Bottom=FMath::Min(Bottom,P.Z);Top=FMath::Max(Top,P.Z);}
  Data.PointWeightMaps.Reset(); FPointWeightMap Mask(V.Num()); Mask.Name=TEXT("ShirtHemMaxDistance");
  Mask.CurrentTarget=(uint8)EWeightMapTargetCommon::MaxDistance; Mask.bEnabled=true;
  int32 Movable=0;
  for(int32 I=0;I<V.Num();++I)
  {
   Mask.Values[I]=.25f*(1-FMath::SmoothStep(Bottom,Bottom+(Top-Bottom)*.2f,V[I].Z));
   if(Mask.Values[I]>.01f) ++Movable;
  }
  Data.PointWeightMaps.Add(MoveTemp(Mask)); Asset->ApplyParameterMasks(true);
  if(auto* Config=Asset->GetClothConfig<UChaosClothConfig>())
  {
   Config->DampingCoefficient=.08f; Config->CollisionThickness=.2f; Config->bUseCCD=true;
   Config->AnimDriveStiffness.Low=.15f; Config->AnimDriveStiffness.High=.15f;
   Config->AnimDriveDamping.Low=.2f; Config->AnimDriveDamping.High=.2f;
  }
  Mesh->AddClothingAsset(Asset);
  if(!Asset->BindToSkeletalMesh(Mesh,0,Section,0)) return TEXT("ERROR: cloth binding failed; inspect dedicated copy");
  auto& User=LOD.UserSectionsData.FindOrAdd(LOD.Sections[Section].OriginalDataSectionIndex);
  User.CorrespondClothAssetIndex=static_cast<int16>(Mesh->GetMeshClothingAssets().Num()-1);
  User.ClothingData.AssetGuid=Asset->GetAssetGuid(); User.ClothingData.AssetLodIndex=0;
  Report+=FString::Printf(TEXT("section=%d proxyLOD=%d vertices=%d movable=%d max=0.25cm; "),Section,ProxyLOD,V.Num(),Movable);
 }
 Mesh->MarkPackageDirty(); return TEXT("OK: ")+Report;
#else
 return TEXT("ERROR: editor-only authoring");
#endif
}

FString UStormfallClothTools::FinalizeWetShirtHem(USkeletalMesh* Mesh)
{
#if WITH_EDITOR
 if(!Mesh || !Mesh->GetPathName().StartsWith(TEXT("/Game/Stormfall/ShirtTrial/Wetness/Physics/")) || !Mesh->GetImportedModel()) return TEXT("ERROR: requires dedicated shirt physics copy");
 FScopedSkeletalMeshPostEditChange Scope(Mesh); Mesh->Modify();
 auto& LOD=Mesh->GetImportedModel()->LODModels[0]; int32 Count=0;
 for(int32 Index=0;Index<Mesh->GetMeshClothingAssets().Num();++Index)
 {
  auto* Asset=Cast<UClothingAssetCommon>(Mesh->GetMeshClothingAssets()[Index]);
  if(!Asset || !Asset->GetName().StartsWith(TEXT("SF_WetShirtHem_"))) continue;
  const int32 Section=FCString::Atoi(*Asset->GetName().RightChop(15));
  if(!LOD.Sections.IsValidIndex(Section)) return TEXT("ERROR: missing shirt section");
  Asset->Modify();
  for(auto& Data:Asset->LodData)
   for(auto& Map:Data.PointWeightMaps)
    if(Map.CurrentTarget==(uint8)EWeightMapTargetCommon::MaxDistance)
    {
     float Maximum=0; for(float V:Map.Values) Maximum=FMath::Max(Maximum,V);
     if(Maximum>.25001f) for(float& V:Map.Values) V*=.25f/Maximum;
    }
  Asset->ApplyParameterMasks(true);
  if(!LOD.Sections[Section].ClothingData.IsValid())
  {
   Asset->LodMap.Reset();
   if(!Asset->BindToSkeletalMesh(Mesh,0,Section,0)) return TEXT("ERROR: persistent clothing binding failed");
  }
  // Match FSkeletalMeshClothingSystemUtilities::AssignClothingToSection in UE 5.8.
  auto& User=LOD.UserSectionsData.FindOrAdd(LOD.Sections[Section].OriginalDataSectionIndex);
  User.CorrespondClothAssetIndex=static_cast<int16>(Index);
  User.ClothingData.AssetGuid=Asset->GetAssetGuid(); User.ClothingData.AssetLodIndex=0;
  if(auto* Config=Asset->GetClothConfig<UChaosClothConfig>())
  {
   Config->DampingCoefficient=.08f; Config->CollisionThickness=.2f; Config->bUseCCD=true;
   Config->AnimDriveStiffness.Low=Config->AnimDriveStiffness.High=.15f;
   Config->AnimDriveDamping.Low=Config->AnimDriveDamping.High=.2f;
  }
  ++Count;
 }
 Mesh->MarkPackageDirty();
 return Count==2?TEXT("EXISTS: two persistent front/back cloth bindings finalized"):TEXT("ERROR: expected two shirt cloth assets");
#else
 return TEXT("ERROR: editor-only authoring");
#endif
}
