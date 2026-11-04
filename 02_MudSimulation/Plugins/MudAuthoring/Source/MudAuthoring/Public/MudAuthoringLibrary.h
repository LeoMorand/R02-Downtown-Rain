#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "MudAuthoringLibrary.generated.h"

class UNiagaraComponent;

/** Source-only authoring bridge. Generated Niagara assets run without this editor module. */
UCLASS()
class MUDAUTHORING_API UMudAuthoringLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    /** Generic graph edits are restricted to assets owned by /Game/MudStudy/. */
    UFUNCTION(BlueprintCallable,Category="Mud Study|Authoring")
    static FString EditGraph(const FString& GraphPath,const FString& JsonSpec);
    /** Create typed user values / data interfaces in an owned NiagaraSystem. */
    UFUNCTION(BlueprintCallable,Category="Mud Study|Authoring")
    static FString AddUserParameter(const FString& SystemPath,const FString& Name,const FString& Type,const FString& DefaultText);
    UFUNCTION(BlueprintCallable,Category="Mud Study|Authoring")
    static FString SaveOwnedObject(const FString& ObjectPath);
    /** Read CPU-side GPU inputs after synchronizing the Niagara tick; no GPU readback or graph writes. */
    UFUNCTION(BlueprintCallable,Category="Mud Study|Inspection")
    static FString InspectGpuInputs(UNiagaraComponent* Component,const FString& NameFilter);
};
