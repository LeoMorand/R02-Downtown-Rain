#include "SLightingPresetsPanel.h"

#include "Engine/Texture2D.h"
#include "HAL/PlatformProcess.h"
#include "IPythonScriptPlugin.h"
#include "Misc/MessageDialog.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Input/SComboBox.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"
#include "Widgets/Input/SSpinBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SExpandableArea.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSplitter.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Views/SHeaderRow.h"

#define LOCTEXT_NAMESPACE "LightingPresetsPanel"

namespace
{
	const FVector2D ThumbSmall(96, 54);
	const FVector2D ThumbLarge(320, 180);

	TSharedRef<SWidget> Button(const FText& Label, const FText& Tip, FOnClicked OnClicked)
	{
		return SNew(SButton).Text(Label).ToolTipText(Tip).OnClicked(OnClicked).HAlign(HAlign_Center);
	}

	TSharedRef<SWidget> Section(const FText& Title, TSharedRef<SWidget> Body, bool bOpen = true)
	{
		return SNew(SExpandableArea)
			.InitiallyCollapsed(!bOpen)
			.HeaderContent()[SNew(STextBlock).Text(Title).Font(FAppStyle::GetFontStyle("BoldFont"))]
			.BodyContent()[SNew(SBox).Padding(FMargin(4, 4, 4, 8))[Body]];
	}

	TSharedRef<SWidget> Row2(TSharedRef<SWidget> A, TSharedRef<SWidget> B)
	{
		return SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().FillWidth(1).Padding(0, 0, 2, 0)[A]
			+ SHorizontalBox::Slot().FillWidth(1).Padding(2, 0, 0, 0)[B];
	}

	TSharedRef<SWidget> Row3(TSharedRef<SWidget> A, TSharedRef<SWidget> B, TSharedRef<SWidget> C)
	{
		return SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().FillWidth(1).Padding(0, 0, 2, 0)[A]
			+ SHorizontalBox::Slot().FillWidth(1).Padding(2, 0)[B]
			+ SHorizontalBox::Slot().FillWidth(1).Padding(2, 0, 0, 0)[C];
	}
}

/** One row of the parameter table: key | property | editable value. */
class SParamRow : public SMultiColumnTableRow<TSharedPtr<SLightingPresetsPanel::FParamRow>>
{
public:
	DECLARE_DELEGATE_ThreeParams(FOnCommit, const FText&, ETextCommit::Type, TSharedPtr<SLightingPresetsPanel::FParamRow>);

	SLATE_BEGIN_ARGS(SParamRow) {}
		SLATE_ARGUMENT(TSharedPtr<SLightingPresetsPanel::FParamRow>, Row)
		SLATE_EVENT(FOnCommit, OnCommit)
	SLATE_END_ARGS()

	void Construct(const FArguments& Args, const TSharedRef<STableViewBase>& Owner)
	{
		Row = Args._Row;
		OnCommit = Args._OnCommit;
		SMultiColumnTableRow::Construct(FSuperRowType::FArguments().Padding(1), Owner);
	}

	virtual TSharedRef<SWidget> GenerateWidgetForColumn(const FName& Column) override
	{
		if (Column == "Value")
		{
			return SNew(SEditableTextBox)
				.Text(FText::FromString(Row->Value))
				.Font(FCoreStyle::GetDefaultFontStyle("Mono", 9))
				.ToolTipText(LOCTEXT("ValueTip", "Enter to save (numbers: 8e7, colors: [255,240,220,255], true/false)"))
				.OnTextCommitted_Lambda([this](const FText& T, ETextCommit::Type C)
				{
					if (C == ETextCommit::OnEnter && T.ToString() != Row->Value) OnCommit.ExecuteIfBound(T, C, Row);
				});
		}
		const FString& S = Column == "Key" ? Row->Key : Row->Property;
		return SNew(STextBlock).Text(FText::FromString(S)).Margin(FMargin(4, 2));
	}

private:
	TSharedPtr<SLightingPresetsPanel::FParamRow> Row;
	FOnCommit OnCommit;
};

void SLightingPresetsPanel::Construct(const FArguments&)
{
	ChildSlot
	[
		SNew(SSplitter).Orientation(Orient_Vertical)
		+ SSplitter::Slot().Value(0.78f)
		[
			SNew(SSplitter).Orientation(Orient_Horizontal)
			+ SSplitter::Slot().Value(0.22f)[MakeLibrary()]
			+ SSplitter::Slot().Value(0.48f)[MakeSelected()]
			+ SSplitter::Slot().Value(0.30f)
			[
				SNew(SScrollBox)
				+ SScrollBox::Slot()[MakeTools()]
				+ SScrollBox::Slot()[MakeRender()]
			]
		]
		+ SSplitter::Slot().Value(0.22f)
		[
			SAssignNew(Output, SMultiLineEditableTextBox).IsReadOnly(true).AlwaysShowScrollbars(true)
			.Font(FCoreStyle::GetDefaultFontStyle("Mono", 9))
		]
	];
	Refresh();
}

// --- layout -------------------------------------------------------------------

TSharedRef<SWidget> SLightingPresetsPanel::MakeLibrary()
{
	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight().Padding(4)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
			[SNew(STextBlock).Text(LOCTEXT("Presets", "Presets")).Font(FAppStyle::GetFontStyle("BoldFont"))]
			+ SHorizontalBox::Slot().AutoWidth()
			[Button(LOCTEXT("Refresh", "Refresh"), LOCTEXT("RefreshTip", "Reload presets and cameras"),
				FOnClicked::CreateLambda([this] { Refresh(); return FReply::Handled(); }))]
		]
		+ SVerticalBox::Slot().FillHeight(1).Padding(4, 0, 4, 4)
		[
			SNew(SBorder).BorderImage(FAppStyle::GetBrush("ToolPanel.GroupBorder"))
			[
				SAssignNew(List, SListView<FItem>)
				.ListItemsSource(&Presets)
				.SelectionMode(ESelectionMode::Single)
				.OnSelectionChanged_Lambda([this](FItem, ESelectInfo::Type) { LoadSelected(); })
				.OnMouseButtonDoubleClick_Lambda([this](FItem) { OnApply(true); })
				.OnGenerateRow_Lambda([this](FItem In, const TSharedRef<STableViewBase>& Owner)
				{
					return SNew(STableRow<FItem>, Owner).Padding(FMargin(2, 3))
					[
						SNew(SHorizontalBox)
						+ SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
						[
							SNew(SBox).WidthOverride(ThumbSmall.X).HeightOverride(ThumbSmall.Y)
							[SNew(SImage).Image_Lambda([this, In] { return ThumbFor(*In); })]
						]
						+ SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
						[SNew(STextBlock).Text(FText::FromString(*In))]
					];
				})
			]
		];
}

TSharedRef<SWidget> SLightingPresetsPanel::MakeSelected()
{
	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight().Padding(4)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 4)
			[
				SNew(STextBlock).Font(FAppStyle::GetFontStyle("HeadingExtraSmall"))
				.Text_Lambda([this] { const FString S = Selected(); return FText::FromString(S.IsEmpty() ? TEXT("Select a preset") : S); })
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 6).HAlign(HAlign_Left)
			[
				SNew(SBox).MaxDesiredHeight(ThumbLarge.Y).MaxDesiredWidth(ThumbLarge.X)
				.Visibility_Lambda([this] { return Thumbs.Contains(Selected()) ? EVisibility::Visible : EVisibility::Collapsed; })
				[
					SNew(SScaleBox).Stretch(EStretch::ScaleToFit)
					[SNew(SImage).Image_Lambda([this] { return ThumbFor(Selected()); })]
				]
			]
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 2)
				[Row3(
					Button(LOCTEXT("Preview", "Preview"), LOCTEXT("PreviewTip", "List the changes applying it would make; writes nothing (double-click does the same)"),
						FOnClicked::CreateLambda([this] { return OnApply(true); })),
					Button(LOCTEXT("Apply", "Apply"), LOCTEXT("ApplyTip", "Write it to the level as one undo step (Ctrl+Z). Does not save the level."),
						FOnClicked::CreateLambda([this] { return OnApply(false); })),
					Button(LOCTEXT("Validate", "Validate"), LOCTEXT("ValidateTip", "Missing actors, class changes, lights it does not drive"),
						FOnClicked::CreateSP(this, &SLightingPresetsPanel::OnValidate)))]
				+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 2)
				[Row3(
					Button(LOCTEXT("Overwrite", "Update from level"), LOCTEXT("OverwriteTip", "Re-capture the level into this preset"),
						FOnClicked::CreateLambda([this] { return OnCapture(true); })),
					Button(LOCTEXT("Export", "Export JSON"), LOCTEXT("ExportTip", "Write it to Saved/LightingPresets/<name>.json"),
						FOnClicked::CreateSP(this, &SLightingPresetsPanel::OnExport)),
					Button(LOCTEXT("Delete", "Delete"), LOCTEXT("DeleteTip", "Delete the preset and its thumbnail"),
						FOnClicked::CreateSP(this, &SLightingPresetsPanel::OnDelete)))]
				+ SVerticalBox::Slot().AutoHeight().Padding(0, 4, 0, 0)
				[
					SNew(SCheckBox)
					.IsChecked_Lambda([this] { return bTransforms ? ECheckBoxState::Checked : ECheckBoxState::Unchecked; })
					.OnCheckStateChanged_Lambda([this](ECheckBoxState S) { bTransforms = S == ECheckBoxState::Checked; })
					[SNew(STextBlock).Text(LOCTEXT("Transforms", "Include light positions"))]
				]
			]
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(4, 6, 4, 2)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 8, 0)
			[SNew(STextBlock).Text(LOCTEXT("Params", "Parameters")).Font(FAppStyle::GetFontStyle("BoldFont"))]
			+ SHorizontalBox::Slot().FillWidth(1).Padding(0, 0, 8, 0)
			[
				SAssignNew(RowFilter, SEditableTextBox).HintText(LOCTEXT("Filter", "Filter, e.g. TopLight or intensity"))
				.OnTextChanged_Lambda([this](const FText&) { RefreshFilteredRows(); })
			]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				SNew(SCheckBox)
				.IsChecked_Lambda([this] { return bApplyEdits ? ECheckBoxState::Checked : ECheckBoxState::Unchecked; })
				.OnCheckStateChanged_Lambda([this](ECheckBoxState S) { bApplyEdits = S == ECheckBoxState::Checked; })
				.ToolTipText(LOCTEXT("LiveTip", "Also apply each edited value to the level right away"))
				[SNew(STextBlock).Text(LOCTEXT("Live", "Apply edits live"))]
			]
		]
		+ SVerticalBox::Slot().FillHeight(1).Padding(4, 0, 4, 4)
		[
			SNew(SBorder).BorderImage(FAppStyle::GetBrush("ToolPanel.GroupBorder"))
			[
				SAssignNew(RowList, SListView<FRow>)
				.ListItemsSource(&FilteredRows)
				.SelectionMode(ESelectionMode::None)
				.OnGenerateRow_Lambda([this](FRow In, const TSharedRef<STableViewBase>& Owner) -> TSharedRef<ITableRow>
				{
					return SNew(SParamRow, Owner).Row(In)
						.OnCommit(SParamRow::FOnCommit::CreateSP(this, &SLightingPresetsPanel::OnValueCommitted));
				})
				.HeaderRow
				(
					SNew(SHeaderRow)
					+ SHeaderRow::Column("Key").DefaultLabel(LOCTEXT("ColKey", "Actor")).FillWidth(0.35f)
					+ SHeaderRow::Column("Property").DefaultLabel(LOCTEXT("ColProp", "Property")).FillWidth(0.35f)
					+ SHeaderRow::Column("Value").DefaultLabel(LOCTEXT("ColValue", "Value")).FillWidth(0.30f)
				)
			]
		];
}

TSharedRef<SWidget> SLightingPresetsPanel::MakeTools()
{
	auto Combo = [this](TSharedPtr<SComboBox<FItem>>& C, FItem& Sel) -> TSharedRef<SWidget>
	{
		return SAssignNew(C, SComboBox<FItem>)
			.OptionsSource(&CompareOptions)
			.OnGenerateWidget_Lambda([](FItem In) { return SNew(STextBlock).Text(FText::FromString(*In)); })
			.OnSelectionChanged_Lambda([&Sel](FItem In, ESelectInfo::Type) { Sel = In; })
			[SNew(STextBlock).Text_Lambda([&Sel] { return FText::FromString(Sel.IsValid() ? *Sel : TEXT("-")); })];
	};

	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[Section(LOCTEXT("New", "New preset"),
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 2)
			[SAssignNew(NameBox, SEditableTextBox).HintText(LOCTEXT("NameHint", "Name, e.g. CR_Day_Warm"))]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 2)
			[SAssignNew(NotesBox, SEditableTextBox).HintText(LOCTEXT("NotesHint", "Notes (optional)"))]
			+ SVerticalBox::Slot().AutoHeight()
			[Row2(
				Button(LOCTEXT("Capture", "Capture level"), LOCTEXT("CaptureTip", "Save the level's lights, sky light, fog and post process as a new preset"),
					FOnClicked::CreateLambda([this] { return OnCapture(false); })),
				Button(LOCTEXT("Derive", "Copy selected"), LOCTEXT("DeriveTip", "New preset from the selected one, without touching the level; then edit its parameters"),
					FOnClicked::CreateSP(this, &SLightingPresetsPanel::OnDerive)))])]
		+ SVerticalBox::Slot().AutoHeight()
		[Section(LOCTEXT("Compare", "Compare"),
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 2)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 4, 0)[SNew(STextBlock).Text(LOCTEXT("A", "A"))]
				+ SHorizontalBox::Slot().FillWidth(1).Padding(0, 0, 8, 0)[Combo(CompareA, SelA)]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 4, 0)[SNew(STextBlock).Text(LOCTEXT("B", "B"))]
				+ SHorizontalBox::Slot().FillWidth(1)[Combo(CompareB, SelB)]
			]
			+ SVerticalBox::Slot().AutoHeight()
			[Row2(
				Button(LOCTEXT("Diff", "Differences"), LOCTEXT("DiffTip", "Every value that differs (@world = the level now)"),
					FOnClicked::CreateSP(this, &SLightingPresetsPanel::OnDiff)),
				Button(LOCTEXT("AB", "A/B toggle"), LOCTEXT("ABTip", "Apply A, then B on the next click, to flip between them in the viewport"),
					FOnClicked::CreateSP(this, &SLightingPresetsPanel::OnAB)))])]
		+ SVerticalBox::Slot().AutoHeight()
		[Section(LOCTEXT("Exclude", "Exclude actors"),
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 2)
			[SAssignNew(IgnoreBox, SEditableTextBox).HintText(LOCTEXT("IgnoreHint", "Label prefix, e.g. Diagnostic_"))]
			+ SVerticalBox::Slot().AutoHeight()
			[Row2(
				Button(LOCTEXT("Ignore", "Exclude"), LOCTEXT("IgnoreTip", "Tag matching lights LP:Ignore and remove them from saved presets"),
					FOnClicked::CreateLambda([this] { return OnIgnore(true); })),
				Button(LOCTEXT("Unignore", "Include again"), LOCTEXT("UnignoreTip", "Remove the LP:Ignore tag"),
					FOnClicked::CreateLambda([this] { return OnIgnore(false); })))], false)];
}

TSharedRef<SWidget> SLightingPresetsPanel::MakeRender()
{
	auto CheckList = [this](TSharedPtr<SListView<FItem>>& L, TArray<FItem>* Source, TSet<FString>& Set) -> TSharedRef<SWidget>
	{
		return SNew(SBox).MaxDesiredHeight(130)
		[
			SNew(SBorder).BorderImage(FAppStyle::GetBrush("ToolPanel.GroupBorder"))
			[
				SAssignNew(L, SListView<FItem>)
				.ListItemsSource(Source)
				.SelectionMode(ESelectionMode::None)
				.OnGenerateRow_Lambda([&Set](FItem In, const TSharedRef<STableViewBase>& Owner)
				{
					return SNew(STableRow<FItem>, Owner)
					[
						SNew(SCheckBox)
						.IsChecked_Lambda([&Set, In] { return Set.Contains(*In) ? ECheckBoxState::Checked : ECheckBoxState::Unchecked; })
						.OnCheckStateChanged_Lambda([&Set, In](ECheckBoxState S) { if (S == ECheckBoxState::Checked) Set.Add(*In); else Set.Remove(*In); })
						[SNew(STextBlock).Text(FText::FromString(*In))]
					];
				})
			]
		];
	};

	return Section(LOCTEXT("Render", "Render comparison"),
		SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(LOCTEXT("RPresets", "Presets")).ColorAndOpacity(FSlateColor::UseSubduedForeground())]
		+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 4)[CheckList(RenderPresetList, &Presets, RenderPresets)]
		+ SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(LOCTEXT("RCams", "Cameras")).ColorAndOpacity(FSlateColor::UseSubduedForeground())]
		+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 4)[CheckList(CameraList, &Cameras, RenderCameras)]
		+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 4)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().FillWidth(1).Padding(0, 0, 2, 0)
			[SNew(SSpinBox<int32>).MinValue(320).MaxValue(7680).Value_Lambda([this] { return RenderWidth; })
				.OnValueChanged_Lambda([this](int32 V) { RenderWidth = V; })]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(4, 0)[SNew(STextBlock).Text(FText::FromString(TEXT("x")))]
			+ SHorizontalBox::Slot().FillWidth(1).Padding(2, 0, 0, 0)
			[SNew(SSpinBox<int32>).MinValue(180).MaxValue(4320).Value_Lambda([this] { return RenderHeight; })
				.OnValueChanged_Lambda([this](int32 V) { RenderHeight = V; })]
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 2)
		[Row2(
			SNew(SButton).HAlign(HAlign_Center)
				.Text_Lambda([this] { return bRendering ? LOCTEXT("Cancel", "Cancel") : LOCTEXT("Start", "Render"); })
				.ToolTipText(LOCTEXT("RenderTip", "Every ticked preset x camera; the level's lighting is restored afterwards. Thumbnails update from the first camera."))
				.OnClicked(this, &SLightingPresetsPanel::OnRender),
			Button(LOCTEXT("Open", "Open page"), LOCTEXT("OpenTip", "Open the last render's comparison page"),
				FOnClicked::CreateSP(this, &SLightingPresetsPanel::OnOpenPage)))]
		+ SVerticalBox::Slot().AutoHeight()
		[SNew(STextBlock).AutoWrapText(true).Text_Lambda([this] { return FText::FromString(RenderState); })]);
}

// --- python bridge ------------------------------------------------------------

FString SLightingPresetsPanel::Quote(const FString& S)
{
	return TEXT("'") + S.Replace(TEXT("\\"), TEXT("\\\\")).Replace(TEXT("'"), TEXT("\\'")) + TEXT("'");
}

bool SLightingPresetsPanel::RunUi(const FString& Call, TArray<FString>* OutData, bool bQuiet)
{
	IPythonScriptPlugin* Python = IPythonScriptPlugin::Get();
	if (!Python || !Python->IsPythonAvailable())
	{
		Output->SetText(LOCTEXT("NoPython", "Python is not available."));
		return false;
	}
	FPythonCommandEx Cmd;
	Cmd.ExecutionMode = EPythonCommandExecutionMode::ExecuteFile;
	Cmd.Command = FString::Printf(TEXT("from lighting_presets import ui\nui.%s"), *Call);
	const bool bOk = Python->ExecPythonCommandEx(Cmd);

	TArray<FString> Shown;
	for (const FPythonLogOutputEntry& E : Cmd.LogOutput)
	{
		TArray<FString> Split;
		E.Output.ParseIntoArrayLines(Split, false);
		for (FString& L : Split)
		{
			if (L.IsEmpty()) continue;
			if (L.StartsWith(TEXT("@"))) { if (OutData) OutData->Add(L); continue; }
			Shown.Add(E.Type == EPythonLogOutputType::Info ? L : TEXT("! ") + L);
		}
	}
	if (!bOk && !Cmd.CommandResult.IsEmpty())
	{
		Shown.Add(TEXT("! ") + Cmd.CommandResult);
	}
	if (!bQuiet || !bOk)
	{
		Output->SetText(FText::FromString(FString::Join(Shown, TEXT("\n"))));
	}
	return bOk;
}

const FSlateBrush* SLightingPresetsPanel::ThumbFor(const FString& Preset) const
{
	const TSharedPtr<FSlateBrush>* B = Thumbs.Find(Preset);
	return B ? B->Get() : FAppStyle::GetBrush("Brushes.Recessed");
}

void SLightingPresetsPanel::SetThumb(const FString& Preset, const FString& TexturePath)
{
	UTexture2D* Tex = LoadObject<UTexture2D>(nullptr, *TexturePath);
	if (!Tex) return;
	ThumbTextures.Add(TStrongObjectPtr<UTexture2D>(Tex));
	TSharedPtr<FSlateBrush> B = MakeShared<FSlateBrush>();
	B->SetResourceObject(Tex);
	B->ImageSize = ThumbLarge;
	Thumbs.Add(Preset, B);
}

void SLightingPresetsPanel::Refresh()
{
	const FString Keep = Selected();
	TArray<FString> Data;
	if (!RunUi(TEXT("panel_state()"), &Data, true)) return;

	Presets.Reset();
	Cameras.Reset();
	Thumbs.Reset();
	ThumbTextures.Reset();
	CompareOptions.Reset();
	CompareOptions.Add(MakeShared<FString>(TEXT("@world")));
	for (const FString& L : Data)
	{
		TArray<FString> P;
		L.ParseIntoArray(P, TEXT("\t"), false);
		if (P[0] == TEXT("@name") && P.Num() > 1) { Presets.Add(MakeShared<FString>(P[1])); CompareOptions.Add(Presets.Last()); }
		else if (P[0] == TEXT("@cam") && P.Num() > 1) Cameras.Add(MakeShared<FString>(P[1]));
		else if (P[0] == TEXT("@tn") && P.Num() > 2) SetThumb(P[1], P[2]);
	}
	List->RequestListRefresh();
	RenderPresetList->RequestListRefresh();
	CameraList->RequestListRefresh();
	CompareA->RefreshOptions();
	CompareB->RefreshOptions();
	for (const FItem& P : Presets)
	{
		if (*P == Keep) List->SetSelection(P);
	}
	LoadSelected();
}

bool SLightingPresetsPanel::SelectForReview(const FString& Name, const FString& Filter)
{
	if (!List.IsValid() || !RowFilter.IsValid()) return false;
	for (const FItem& Item : Presets)
	{
		if (Item.IsValid() && *Item == Name)
		{
			List->SetSelection(Item);
			List->RequestScrollIntoView(Item);
			RowFilter->SetText(FText::FromString(Filter));
			return Selected() == Name && FilteredRows.Num() > 0;
		}
	}
	return false;
}

void SLightingPresetsPanel::LoadSelected()
{
	Rows.Reset();
	const FString Name = Selected();
	if (!Name.IsEmpty())
	{
		TArray<FString> Data;
		RunUi(FString::Printf(TEXT("rows(%s)"), *Quote(Name)), &Data, true);
		for (const FString& L : Data)
		{
			TArray<FString> P;
			L.ParseIntoArray(P, TEXT("\t"), false);
			if (P[0] == TEXT("@row") && P.Num() > 3)
			{
				Rows.Add(MakeShared<FParamRow>(FParamRow{P[1], P[2], P[3]}));
			}
			else if (P[0] == TEXT("@thumb") && P.Num() > 1 && !Thumbs.Contains(Name))
			{
				SetThumb(Name, P[1]);
			}
		}
	}
	RefreshFilteredRows();
}

void SLightingPresetsPanel::RefreshFilteredRows()
{
	const FString Filter = RowFilter.IsValid() ? RowFilter->GetText().ToString().TrimStartAndEnd() : FString();
	FilteredRows.Reset();
	for (const FRow& Row : Rows)
	{
		if (Filter.IsEmpty() || Row->Key.Contains(Filter) || Row->Property.Contains(Filter))
		{
			FilteredRows.Add(Row);
		}
	}
	if (RowList.IsValid())
	{
		RowList->RequestListRefresh();
		RowList->ScrollToTop();
	}
}

FString SLightingPresetsPanel::Selected() const
{
	if (!List.IsValid()) return FString();
	TArray<FItem> Sel = List->GetSelectedItems();
	return Sel.Num() ? *Sel[0] : FString();
}

// --- actions --------------------------------------------------------------------

#define REQUIRE_SELECTION(Name) \
	const FString Name = Selected(); \
	if (Name.IsEmpty()) { Output->SetText(LOCTEXT("PickOne", "Select a preset first.")); return FReply::Handled(); }

FReply SLightingPresetsPanel::OnApply(bool bDryRun)
{
	REQUIRE_SELECTION(Name)
	RunUi(FString::Printf(TEXT("apply(%s, %s, %s)"), *Quote(Name), *Py(bDryRun), *Py(bTransforms)));
	return FReply::Handled();
}

FReply SLightingPresetsPanel::OnCapture(bool bOverwriteSelected)
{
	const FString Name = bOverwriteSelected ? Selected() : NameBox->GetText().ToString().TrimStartAndEnd();
	if (Name.IsEmpty())
	{
		Output->SetText(bOverwriteSelected ? LOCTEXT("PickOne", "Select a preset first.") : LOCTEXT("NeedName", "Enter a preset name."));
		return FReply::Handled();
	}
	const bool bExists = Presets.ContainsByPredicate([&Name](const FItem& P) { return *P == Name; });
	if (bExists && FMessageDialog::Open(EAppMsgType::YesNo, FText::Format(
		LOCTEXT("OverwriteQ", "Overwrite preset {0} with the level as it is now?"), FText::FromString(Name))) != EAppReturnType::Yes)
	{
		return FReply::Handled();
	}
	if (RunUi(FString::Printf(TEXT("capture(%s, %s, %s)"), *Quote(Name), *Quote(NotesBox->GetText().ToString()), *Py(bTransforms))))
	{
		Refresh();
	}
	return FReply::Handled();
}

FReply SLightingPresetsPanel::OnDerive()
{
	REQUIRE_SELECTION(Base)
	const FString Name = NameBox->GetText().ToString().TrimStartAndEnd();
	if (Name.IsEmpty()) { Output->SetText(LOCTEXT("NeedName", "Enter a preset name.")); return FReply::Handled(); }
	if (Presets.ContainsByPredicate([&Name](const FItem& P) { return *P == Name; }))
	{
		Output->SetText(LOCTEXT("Exists", "A preset with that name exists."));
		return FReply::Handled();
	}
	if (RunUi(FString::Printf(TEXT("derive(%s, %s, %s)"), *Quote(Base), *Quote(Name), *Quote(NotesBox->GetText().ToString()))))
	{
		Refresh();
		for (const FItem& P : Presets) { if (*P == Name) List->SetSelection(P); }
	}
	return FReply::Handled();
}

void SLightingPresetsPanel::OnValueCommitted(const FText& Text, ETextCommit::Type, FRow Row)
{
	const FString Name = Selected();
	if (Name.IsEmpty()) return;
	if (RunUi(FString::Printf(TEXT("set_value(%s, %s, %s, %s, %s)"), *Quote(Name), *Quote(Row->Key),
		*Quote(Row->Property), *Quote(Text.ToString()), *Py(bApplyEdits))))
	{
		Row->Value = Text.ToString();
	}
	else
	{
		LoadSelected();      // put the stored value back in the box
	}
}

FReply SLightingPresetsPanel::OnDiff()
{
	if (!SelA.IsValid() || !SelB.IsValid()) { Output->SetText(LOCTEXT("PickAB", "Pick A and B.")); return FReply::Handled(); }
	RunUi(FString::Printf(TEXT("diff(%s, %s)"), *Quote(*SelA), *Quote(*SelB)));
	return FReply::Handled();
}

FReply SLightingPresetsPanel::OnValidate()
{
	REQUIRE_SELECTION(Name)
	RunUi(FString::Printf(TEXT("validate(%s)"), *Quote(Name)));
	return FReply::Handled();
}

FReply SLightingPresetsPanel::OnAB()
{
	if (!SelA.IsValid() || !SelB.IsValid() || *SelA == TEXT("@world") || *SelB == TEXT("@world"))
	{
		Output->SetText(LOCTEXT("PickABPresets", "Pick two presets (not @world) for A and B."));
		return FReply::Handled();
	}
	RunUi(FString::Printf(TEXT("ab(%s, %s, %s)"), *Quote(*SelA), *Quote(*SelB), *Py(bTransforms)));
	return FReply::Handled();
}

FReply SLightingPresetsPanel::OnDelete()
{
	REQUIRE_SELECTION(Name)
	if (FMessageDialog::Open(EAppMsgType::YesNo, FText::Format(
		LOCTEXT("DeleteQ", "Delete preset {0}?"), FText::FromString(Name))) == EAppReturnType::Yes
		&& RunUi(FString::Printf(TEXT("delete(%s)"), *Quote(Name))))
	{
		Refresh();
	}
	return FReply::Handled();
}

FReply SLightingPresetsPanel::OnExport()
{
	REQUIRE_SELECTION(Name)
	RunUi(FString::Printf(TEXT("export(%s)"), *Quote(Name)));
	return FReply::Handled();
}

FReply SLightingPresetsPanel::OnIgnore(bool bIgnore)
{
	if (RunUi(FString::Printf(TEXT("ignore(%s, %s)"), *Quote(IgnoreBox->GetText().ToString()), *Py(bIgnore))))
	{
		LoadSelected();
	}
	return FReply::Handled();
}

bool SLightingPresetsPanel::ConfigureRender(const TArray<FString>& PresetNames,
	const TArray<FString>& CameraNames, int32 Width, int32 Height)
{
	// Background/minimized windows may stop active timers although the renderer
	// has already finished. Synchronize before treating the panel as busy.
	if (bRendering && PollRender(0, 0) == EActiveTimerReturnType::Stop)
	{
		if (TSharedPtr<FActiveTimerHandle> Timer = RenderPollTimer.Pin()) UnRegisterActiveTimer(Timer.ToSharedRef());
		RenderPollTimer.Reset();
	}
	if (bRendering || PresetNames.IsEmpty() || CameraNames.IsEmpty() ||
		Width < 320 || Width > 7680 || Height < 180 || Height > 4320) return false;
	Refresh();
	auto Has = [](const TArray<FItem>& Items, const FString& Name)
	{
		return Items.ContainsByPredicate([&Name](const FItem& Item) { return *Item == Name; });
	};
	for (const FString& Name : PresetNames) if (!Has(Presets, Name)) return false;
	for (const FString& Name : CameraNames) if (!Has(Cameras, Name)) return false;
	RenderPresets.Reset();
	RenderCameras.Reset();
	for (const FString& Name : PresetNames) RenderPresets.Add(Name);
	for (const FString& Name : CameraNames) RenderCameras.Add(Name);
	RenderWidth = Width;
	RenderHeight = Height;
	for (const FItem& Item : Presets)
		if (*Item == PresetNames.Last()) RenderPresetList->RequestScrollIntoView(Item);
	for (const FItem& Item : Cameras)
		if (*Item == CameraNames.Last()) CameraList->RequestScrollIntoView(Item);
	return true;
}

FString SLightingPresetsPanel::RenderConfigurationJson() const
{
	TSharedRef<FJsonObject> Data = MakeShared<FJsonObject>();
	TArray<TSharedPtr<FJsonValue>> P, C;
	for (const FItem& Item : Presets)
		if (RenderPresets.Contains(*Item)) P.Add(MakeShared<FJsonValueString>(*Item));
	for (const FItem& Item : Cameras)
		if (RenderCameras.Contains(*Item)) C.Add(MakeShared<FJsonValueString>(*Item));
	Data->SetArrayField(TEXT("presets"), P);
	Data->SetArrayField(TEXT("cameras"), C);
	Data->SetNumberField(TEXT("width"), RenderWidth);
	Data->SetNumberField(TEXT("height"), RenderHeight);
	Data->SetBoolField(TEXT("running"), bRendering);
	Data->SetStringField(TEXT("state"), RenderState);
	Data->SetStringField(TEXT("folder"), RenderFolder);
	FString Json;
	FJsonSerializer::Serialize(Data, TJsonWriterFactory<>::Create(&Json));
	return Json;
}

FReply SLightingPresetsPanel::OnRender()
{
	if (bRendering)
	{
		RunUi(TEXT("render_cancel()"));
		return FReply::Handled();
	}
	// keep list order, not set order
	TArray<FString> P, C;
	for (const FItem& I : Presets) { if (RenderPresets.Contains(*I)) P.Add(*I); }
	for (const FItem& I : Cameras) { if (RenderCameras.Contains(*I)) C.Add(*I); }
	if (RunUi(FString::Printf(TEXT("render_start(%s, %s, %d, %d)"), *Quote(FString::Join(P, TEXT(","))),
		*Quote(FString::Join(C, TEXT(","))), RenderWidth, RenderHeight)))
	{
		bRendering = true;
		RenderState = TEXT("Starting...");
		RenderPollTimer = RegisterActiveTimer(0.5f, FWidgetActiveTimerDelegate::CreateSP(this, &SLightingPresetsPanel::PollRender));
	}
	return FReply::Handled();
}

EActiveTimerReturnType SLightingPresetsPanel::PollRender(double, float)
{
	TArray<FString> Data;
	RunUi(TEXT("render_status()"), &Data, true);
	for (const FString& L : Data)
	{
		if (!L.StartsWith(TEXT("@status\t"))) continue;
		TSharedPtr<FJsonObject> S;
		if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(L.Mid(8)), S) || !S.IsValid()) continue;
		const FString State = S->GetStringField(TEXT("state"));
		RenderFolder = S->GetStringField(TEXT("folder"));
		RenderState = FString::Printf(TEXT("%s: %d / %d"), *State,
			(int32)S->GetNumberField(TEXT("done")), (int32)S->GetNumberField(TEXT("total")));
		const TArray<TSharedPtr<FJsonValue>>* W;
		if (S->TryGetArrayField(TEXT("warnings"), W))
		{
			for (const TSharedPtr<FJsonValue>& V : *W) RenderState += TEXT("\n! ") + V->AsString();
		}
		FString Err;
		if (S->TryGetStringField(TEXT("error"), Err) && !Err.IsEmpty()) RenderState += TEXT("\n! ") + Err.Left(400);
		if (State != TEXT("running"))
		{
			bRendering = false;
			Refresh();          // new thumbnails
			if (State == TEXT("done")) OnOpenPage();
			return EActiveTimerReturnType::Stop;
		}
	}
	return EActiveTimerReturnType::Continue;
}

FReply SLightingPresetsPanel::OnOpenPage()
{
	if (RenderFolder.IsEmpty()) { Output->SetText(LOCTEXT("NoRender", "Nothing rendered in this session yet.")); return FReply::Handled(); }
	FPlatformProcess::LaunchURL(*(FPaths::Combine(RenderFolder, TEXT("index.html"))), nullptr, nullptr);
	return FReply::Handled();
}

#undef REQUIRE_SELECTION
#undef LOCTEXT_NAMESPACE
