#include "MudAuthoringLibrary.h"
#include "Modules/ModuleManager.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraph/EdGraphSchema.h"
#include "UObject/UnrealType.h"
#include "UObject/SavePackage.h"
#include "Misc/PackageName.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "NiagaraSystem.h"
#include "NiagaraDataInterface.h"
#include "NiagaraTypes.h"
#include "NiagaraComponent.h"
#include "NiagaraSystemInstanceController.h"
#include "NiagaraSystemInstance.h"
#include "NiagaraEmitterInstance.h"
#include "NiagaraComputeExecutionContext.h"
#include "NiagaraDataInterfaceGrid2DCollection.h"

IMPLEMENT_MODULE(FDefaultModuleImpl,MudAuthoring)

FString UMudAuthoringLibrary::InspectGpuInputs(UNiagaraComponent* Component,const FString& NameFilter)
{
    auto Root=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Rows;
    if(!IsValid(Component))return TEXT("{\"success\":false,\"error\":\"Component missing\"}");
    auto Controller=Component->GetSystemInstanceController();
    if(!Controller.IsValid())return TEXT("{\"success\":false,\"error\":\"No live instance\"}");
    Controller->WaitForConcurrentTickAndFinalize();
    const auto Instance=Controller->GetSystemInstance_Unsafe();
    if(!Instance)return TEXT("{\"success\":false,\"error\":\"No live instance\"}");
    for(const auto& Emitter:Instance->GetEmitters())
    {
        auto Context=Emitter->GetGPUContext();if(!Context)continue;
        // Stage counts/enabled bindings are CPU-side renderer-bound parameters,
        // not entries in the GPU shader's CombinedParamStore (see GPUSystemTick).
        const auto& StageStore=Emitter->GetRendererBoundVariables();
        for(const auto& V:StageStore.ReadParameterVariables())
        {
            const FString Name=V.GetName().ToString();
            if(!NameFilter.IsEmpty()&&!Name.Contains(NameFilter))continue;
            if(V.IsDataInterface()||V.IsUObject()||!V.GetType().GetScriptStruct())continue;
            auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("name"),Name);
            Row->SetStringField(TEXT("type"),V.GetType().GetName());
            Row->SetStringField(TEXT("source"),TEXT("RendererBoundVariables"));
            FString Value;V.GetType().GetScriptStruct()->ExportText(Value,StageStore.GetParameterData(V),nullptr,nullptr,PPF_None,nullptr);
            Row->SetStringField(TEXT("value"),Value);Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
        const auto& Store=Context->CombinedParamStore;
        for(const auto& V:Store.ReadParameterVariables())
        {
            const FString Name=V.GetName().ToString();
            if(!NameFilter.IsEmpty()&&!Name.Contains(NameFilter))continue;
            auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("name"),Name);
            Row->SetStringField(TEXT("type"),V.GetType().GetName());
            if(V.IsDataInterface())
            {
                auto DI=Store.GetDataInterface(V.Offset);Row->SetStringField(TEXT("object"),GetPathNameSafe(DI));
                if(auto Grid=Cast<UNiagaraDataInterfaceGrid2DCollection>(DI))
                {
                    int32 X=0,Y=0;Grid->GetTextureSize(Component,X,Y);
                    Row->SetNumberField(TEXT("cellsX"),X);Row->SetNumberField(TEXT("cellsY"),Y);
                    Row->SetNumberField(TEXT("manualAttributes"),Grid->NumAttributes);
                    Row->SetStringField(TEXT("format"),StaticEnum<ENiagaraGpuBufferFormat>()->GetNameStringByValue((int64)Grid->OverrideBufferFormat));
                }
            }
            else if(!V.IsUObject()&&V.GetType().GetScriptStruct())
            {
                FString Value;V.GetType().GetScriptStruct()->ExportText(Value,Store.GetParameterData(V),nullptr,nullptr,PPF_None,nullptr);
                Row->SetStringField(TEXT("value"),Value);
                if(V.GetSizeInBytes()==64||Name.Contains(TEXT("SimPos")))
                {
                    TArray<TSharedPtr<FJsonValue>> Numbers;
                    const uint8* Data=Store.GetParameterData(V);
                    for(int32 I=0;I<V.GetSizeInBytes()/4;++I)
                    {
                        float Number=0;FMemory::Memcpy(&Number,Data+I*4,4);
                        Numbers.Add(MakeShared<FJsonValueNumber>(Number));
                    }
                    Row->SetArrayField(TEXT("float32"),Numbers);
                }
            }
            Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
    }
    Root->SetBoolField(TEXT("success"),true);Root->SetArrayField(TEXT("values"),Rows);
    FString Result;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Result));return Result;
}

namespace
{
bool Owned(const FString& P){return P.StartsWith(TEXT("/Game/MudStudy/"));}
FString MudError(const FString& S){return FString::Printf(TEXT("{\"success\":false,\"error\":\"%s\"}"),*S.ReplaceCharWithEscapedChar());}
FString Okay(){return TEXT("{\"success\":true}");}
FString Field(const TSharedPtr<FJsonObject>& O,const TCHAR* K,const FString& D=TEXT("")){FString V;return O->TryGetStringField(K,V)?V:D;}
bool Assign(UObject* O,const FString& Name,const FString& Text)
{
    FProperty* P=O->GetClass()->FindPropertyByName(*Name);
    return P && P->ImportText_Direct(*Text,P->ContainerPtrToValuePtr<void>(O),O,PPF_None)!=nullptr;
}
UEdGraphPin* Pin(UEdGraphNode* N,const FString& Name,EEdGraphPinDirection Dir)
{
    if(!N)return nullptr;
    for(UEdGraphPin* P:N->Pins)if(P->Direction==Dir&&P->PinName.ToString()==Name)return P;
    return nullptr;
}
UEdGraphNode* Node(UEdGraph* G,const FString& Name)
{
    for(UEdGraphNode* N:G->Nodes)if(N&&N->GetName()==Name)return N;
    return nullptr;
}
FNiagaraTypeDefinition TypeDef(const FString& T)
{
    if(T==TEXT("float"))return FNiagaraTypeDefinition::GetFloatDef();
    if(T==TEXT("int"))return FNiagaraTypeDefinition::GetIntDef();
    if(T==TEXT("bool"))return FNiagaraTypeDefinition::GetBoolDef();
    if(T==TEXT("float2"))return FNiagaraTypeDefinition::GetVec2Def();
    if(T==TEXT("float3"))return FNiagaraTypeDefinition::GetVec3Def();
    if(T==TEXT("float4"))return FNiagaraTypeDefinition::GetVec4Def();
    if(T==TEXT("position"))return FNiagaraTypeDefinition::GetPositionDef();
    if(T==TEXT("map"))return FNiagaraTypeDefinition::GetParameterMapDef();
    if(UClass* C=LoadObject<UClass>(nullptr,*T))return FNiagaraTypeDefinition(C);
    if(UScriptStruct* S=LoadObject<UScriptStruct>(nullptr,*T))return FNiagaraTypeDefinition(S);
    return FNiagaraTypeDefinition();
}
FEdGraphPinType PinType(const FNiagaraTypeDefinition& T)
{
    FEdGraphPinType P;
    if(T.GetClass()){P.PinCategory=TEXT("Class");P.PinSubCategoryObject=T.GetClass();}
    else{P.PinCategory=TEXT("Type");P.PinSubCategoryObject=T.GetScriptStruct();}
    return P;
}
}

FString UMudAuthoringLibrary::EditGraph(const FString& GraphPath,const FString& JsonSpec)
{
    if(!Owned(GraphPath))return MudError(TEXT("Only /Game/MudStudy graphs are writable"));
    UEdGraph* G=LoadObject<UEdGraph>(nullptr,*GraphPath);
    if(!G)return MudError(TEXT("Graph not found"));
    TSharedPtr<FJsonObject> Spec;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(JsonSpec),Spec))return MudError(TEXT("Invalid JSON"));
    G->Modify();
    bool Clear=false;Spec->TryGetBoolField(TEXT("clear"),Clear);
    if(Clear){auto Existing=G->Nodes;for(auto N:Existing)if(N)G->RemoveNode(N);}
    const TArray<TSharedPtr<FJsonValue>>* Entries=nullptr;
    if(Spec->TryGetArrayField(TEXT("nodes"),Entries))for(const auto& Entry:*Entries)
    {
        auto O=Entry->AsObject();FString Name=Field(O,TEXT("name"));
        UEdGraphNode* N=Node(G,Name);
        if(!N)
        {
            UClass* C=LoadObject<UClass>(nullptr,*Field(O,TEXT("class")));
            if(!C||!C->IsChildOf(UEdGraphNode::StaticClass()))return MudError(TEXT("Invalid node class"));
            N=NewObject<UEdGraphNode>(G,C,*Name,RF_Transactional);G->AddNode(N,false,false);
            N->CreateNewGuid();N->PostPlacedNewNode();
        }
        N->Modify();
        const TSharedPtr<FJsonObject>* Variable=nullptr;
        if(O->TryGetObjectField(TEXT("variable"),Variable))
        {
            FNiagaraVariable V(TypeDef(Field(*Variable,TEXT("type"))),*Field(*Variable,TEXT("name")));
            auto P=FindFProperty<FStructProperty>(N->GetClass(),*Field(*Variable,TEXT("property"),TEXT("Input")));
            if(!P)return MudError(TEXT("Variable property missing"));
            P->Struct->CopyScriptStruct(P->ContainerPtrToValuePtr<void>(N),&V);
        }
        const TArray<TSharedPtr<FJsonValue>>* Vars=nullptr;
        if(O->TryGetArrayField(TEXT("outputVariables"),Vars))
        {
            auto P=FindFProperty<FArrayProperty>(N->GetClass(),TEXT("Outputs"));
            if(!P)return MudError(TEXT("Output variable array missing"));
            FScriptArrayHelper H(P,P->ContainerPtrToValuePtr<void>(N));H.EmptyValues();
            auto Inner=CastFieldChecked<FStructProperty>(P->Inner);
            for(const auto& Item:*Vars)
            {
                auto VObj=Item->AsObject();FNiagaraVariable V(TypeDef(Field(VObj,TEXT("type"))),*Field(VObj,TEXT("name")));
                const int32 I=H.AddValue();Inner->Struct->CopyScriptStruct(H.GetRawPtr(I),&V);
            }
        }
        const TSharedPtr<FJsonObject>* SigObj=nullptr;
        if(O->TryGetObjectField(TEXT("signature"),SigObj))
        {
            FNiagaraFunctionSignature Signature;Signature.Name=TEXT("MudKernel");
            for(const TCHAR* Side:{TEXT("inputs"),TEXT("outputs")})
            {
                const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
                if((*SigObj)->TryGetArrayField(Side,Values))for(const auto& Value:*Values)
                {
                    auto VObj=Value->AsObject();FNiagaraVariable V(TypeDef(Field(VObj,TEXT("type"))),*Field(VObj,TEXT("name")));
                    if(FCString::Strcmp(Side,TEXT("inputs"))==0)Signature.Inputs.Add(V);else Signature.Outputs.Add(V);
                }
            }
            auto P=FindFProperty<FStructProperty>(N->GetClass(),TEXT("Signature"));
            if(!P)return MudError(TEXT("Custom signature missing"));
            P->Struct->CopyScriptStruct(P->ContainerPtrToValuePtr<void>(N),&Signature);
        }
        const TSharedPtr<FJsonObject>* Props=nullptr;
        if(O->TryGetObjectField(TEXT("properties"),Props))for(const auto& KV:(*Props)->Values)
            if(!Assign(N,FString(*KV.Key),KV.Value->AsString()))return MudError(FString(TEXT("Failed property: "))+FString(*KV.Key));
        bool Allocate=true;O->TryGetBoolField(TEXT("allocate"),Allocate);
        if(Allocate&&N->Pins.Num()==0)N->AllocateDefaultPins();
        N->NodePosX=(int32)O->GetNumberField(TEXT("x"));N->NodePosY=(int32)O->GetNumberField(TEXT("y"));
    }
    if(Spec->TryGetArrayField(TEXT("pins"),Entries))for(const auto& Entry:*Entries)
    {
        auto O=Entry->AsObject();auto N=Node(G,Field(O,TEXT("node")));
        if(!N)return MudError(TEXT("Pin owner missing"));
        const bool Input=Field(O,TEXT("direction"))==TEXT("input");auto Dir=Input?EGPD_Input:EGPD_Output;
        FString Name=Field(O,TEXT("name"));auto P=Pin(N,Name,Dir);
        if(!P)P=N->CreatePin(Dir,PinType(TypeDef(Field(O,TEXT("type")))),*Name);
        P->DefaultValue=Field(O,TEXT("default"));P->PersistentGuid=FGuid::NewGuid();
        // Mirror the original MapGet default-pair bookkeeping without private editor APIs.
        if(!Input&&N->GetClass()->GetFName()==TEXT("NiagaraNodeParameterMapGet"))
        {
            auto D=N->CreatePin(EGPD_Input,P->PinType,NAME_None);D->PersistentGuid=FGuid::NewGuid();D->DefaultValue=P->DefaultValue;D->bHidden=true;
            if(FMapProperty* M=FindFProperty<FMapProperty>(N->GetClass(),TEXT("PinOutputToPinDefaultPersistentId")))
            {
                FScriptMapHelper H(M,M->ContainerPtrToValuePtr<void>(N));int32 I=H.AddDefaultValue_Invalid_NeedsRehash();
                M->KeyProp->CopyCompleteValue(H.GetKeyPtr(I),&P->PersistentGuid);M->ValueProp->CopyCompleteValue(H.GetValuePtr(I),&D->PersistentGuid);H.Rehash();
            }
        }
    }
    if(Spec->TryGetArrayField(TEXT("links"),Entries))for(const auto& Entry:*Entries)
    {
        auto O=Entry->AsObject();auto A=Pin(Node(G,Field(O,TEXT("from"))),Field(O,TEXT("out")),EGPD_Output);
        auto B=Pin(Node(G,Field(O,TEXT("to"))),Field(O,TEXT("in")),EGPD_Input);
        if(!A||!B)return MudError(TEXT("Connection pin missing: ")+Field(O,TEXT("from"))+TEXT(" -> ")+Field(O,TEXT("to")));
        B->BreakAllPinLinks();A->MakeLinkTo(B);
    }
    G->NotifyGraphChanged();G->MarkPackageDirty();
    for(UObject* Owner=G->GetOuter();Owner;Owner=Owner->GetOuter())
    {
        if(Owner->GetClass()->GetFName()!=TEXT("NiagaraScript"))continue;
        if(auto A=FindFProperty<FArrayProperty>(Owner->GetClass(),TEXT("VersionData")))
        {
            FScriptArrayHelper H(A,A->ContainerPtrToValuePtr<void>(Owner));
            auto S=CastFieldChecked<FStructProperty>(A->Inner);
            if(auto P=FindFProperty<FNumericProperty>(S->Struct,TEXT("ModuleUsageBitmask")))
                for(int32 I=0;I<H.Num();++I)P->SetIntPropertyValue(P->ContainerPtrToValuePtr<void>(H.GetRawPtr(I)),int64(2147483647));
        }
        Owner->MarkPackageDirty();break;
    }
    return Okay();
}

FString UMudAuthoringLibrary::AddUserParameter(const FString& SystemPath,const FString& Name,const FString& Type,const FString& DefaultText)
{
    if(!Owned(SystemPath)||!Name.StartsWith(TEXT("User.")))return MudError(TEXT("Owned system and User. name required"));
    auto System=LoadObject<UNiagaraSystem>(nullptr,*SystemPath);if(!System)return MudError(TEXT("System missing"));
    auto T=TypeDef(Type);if(!T.IsValid())return MudError(TEXT("Unknown type"));
    FNiagaraVariable V(T,*Name);auto& Store=System->GetExposedParameters();
    if(!Store.FindParameterOffset(V))Store.AddParameter(V);
    if(T.IsDataInterface())
    {
        UClass* C=T.GetClass();auto DI=NewObject<UNiagaraDataInterface>(System,C,NAME_None,RF_Transactional);
        TSharedPtr<FJsonObject> Settings;
        if(!DefaultText.IsEmpty()&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(DefaultText),Settings))
            for(const auto& KV:Settings->Values)if(!Assign(DI,FString(*KV.Key),KV.Value->AsString()))return MudError(FString(TEXT("Unknown DI property: "))+FString(*KV.Key));
        const int32 Index=Store.IndexOf(V);if(Index==INDEX_NONE)return MudError(TEXT("DI slot missing"));
        Store.SetDataInterface(DI,Index);
    }
    else if(!T.IsUObject()&&!DefaultText.IsEmpty())
    {
        V.AllocateData();T.GetScriptStruct()->ImportText(*DefaultText,V.GetData(),nullptr,PPF_None,nullptr,T.GetScriptStruct()->GetName());
        Store.SetParameterData(V.GetData(),V);
    }
    System->MarkPackageDirty();return Okay();
}

FString UMudAuthoringLibrary::SaveOwnedObject(const FString& ObjectPath)
{
    if(!Owned(ObjectPath))return MudError(TEXT("Only owned assets can be saved"));
    UObject* O=LoadObject<UObject>(nullptr,*ObjectPath);if(!O)return MudError(TEXT("Object not found"));
    UPackage* P=O->GetOutermost();FString File=FPackageName::LongPackageNameToFilename(P->GetName(),FPackageName::GetAssetPackageExtension());
    FSavePackageArgs Args;Args.TopLevelFlags=RF_Public|RF_Standalone;Args.SaveFlags=SAVE_NoError;
    return UPackage::SavePackage(P,nullptr,*File,Args)?Okay():MudError(TEXT("Save failed"));
}
