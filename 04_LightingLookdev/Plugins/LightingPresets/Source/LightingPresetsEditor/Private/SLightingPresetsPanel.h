#pragma once

#include "CoreMinimal.h"
#include "Styling/SlateBrush.h"
#include "UObject/StrongObjectPtr.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/Views/SListView.h"

class SEditableTextBox;
class SMultiLineEditableTextBox;
class UTexture2D;
template <typename OptionType> class SComboBox;

/**
 * Window > Lighting Presets. A view over the plugin's Python
 * (lighting_presets.ui): every action runs one ui function, shows what it
 * printed, and reads "@"-prefixed lines as data (parameter rows, cameras,
 * render status, thumbnails). Preset logic and its tests live in Python only.
 */
class SLightingPresetsPanel : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SLightingPresetsPanel) {}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);
	bool ConfigureRender(const TArray<FString>& PresetNames, const TArray<FString>& CameraNames,
		int32 Width, int32 Height);
	FString RenderConfigurationJson() const;
	bool SelectForReview(const FString& Name, const FString& Filter);

	/** One editable value of the selected preset. */
	struct FParamRow
	{
		FString Key, Property, Value;
	};

private:
	using FItem = TSharedPtr<FString>;
	using FRow = TSharedPtr<FParamRow>;

	/** Runs `lighting_presets.ui.<Call>`. Plain lines go to the output box
	 * (unless bQuiet), "@" lines to OutData. Returns success. */
	bool RunUi(const FString& Call, TArray<FString>* OutData = nullptr, bool bQuiet = false);
	void Refresh();
	void LoadSelected();
	void RefreshFilteredRows();
	FString Selected() const;
	static FString Quote(const FString& S);
	static FString Py(bool b) { return b ? TEXT("True") : TEXT("False"); }
	const FSlateBrush* ThumbFor(const FString& Preset) const;
	void SetThumb(const FString& Preset, const FString& TexturePath);
	EActiveTimerReturnType PollRender(double, float);

	FReply OnApply(bool bDryRun);
	FReply OnCapture(bool bOverwriteSelected);
	FReply OnDerive();
	FReply OnDiff();
	FReply OnValidate();
	FReply OnAB();
	FReply OnDelete();
	FReply OnExport();
	FReply OnIgnore(bool bIgnore);
	FReply OnRender();
	FReply OnOpenPage();
	void OnValueCommitted(const FText& Text, ETextCommit::Type, FRow Row);

	TSharedRef<SWidget> MakeLibrary();
	TSharedRef<SWidget> MakeSelected();
	TSharedRef<SWidget> MakeTools();
	TSharedRef<SWidget> MakeRender();

	// presets
	TArray<FItem> Presets;
	TArray<FItem> CompareOptions;          // "@world" + presets
	TSharedPtr<SListView<FItem>> List;
	TMap<FString, TSharedPtr<FSlateBrush>> Thumbs;
	TArray<TStrongObjectPtr<UTexture2D>> ThumbTextures;

	// selected preset
	TArray<FRow> Rows;
	TArray<FRow> FilteredRows;
	TSharedPtr<SListView<FRow>> RowList;
	TSharedPtr<SEditableTextBox> RowFilter;
	bool bApplyEdits = true;
	bool bTransforms = true;

	// new / derive / compare / exclude
	TSharedPtr<SEditableTextBox> NameBox, NotesBox, IgnoreBox;
	TSharedPtr<SComboBox<FItem>> CompareA, CompareB;
	FItem SelA, SelB;

	// render
	TArray<FItem> Cameras;
	TSet<FString> RenderPresets, RenderCameras;
	TSharedPtr<SListView<FItem>> RenderPresetList, CameraList;
	int32 RenderWidth = 1600, RenderHeight = 900;
	FString RenderState, RenderFolder;
	bool bRendering = false;
	TWeakPtr<FActiveTimerHandle> RenderPollTimer;

	TSharedPtr<SMultiLineEditableTextBox> Output;
};
