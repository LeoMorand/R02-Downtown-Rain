"""Add an opt-in smoke delay to the isolated host, never the frozen project."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
path = root / 'Verification/MudShaderHost/Plugins/MudShaderLab/Source/MudShaderIntegration/Private/MudShaderPreviewActor.cpp'
text = path.read_text(encoding='utf-8-sig')
if 'float SmokeDelay = 5;' not in text:
    old = '        if (GetWorld()->GetTimeSeconds() > 60)'
    assert text.count(old) == 1, 'Unrecognized host source; review the profiling patch.'
    assert text.count('GetWorld()->GetTimeSeconds() > 5 &&') == 1
    text = text.replace(old, '''        float SmokeDelay = 5;
        FParse::Value(FCommandLine::Get(), TEXT("MudShaderSmokeDelay="), SmokeDelay);
        SmokeDelay = FMath::Clamp(SmokeDelay, 5.0f, 120.0f);
        if (GetWorld()->GetTimeSeconds() > SmokeDelay + 60)''')
    text = text.replace('GetWorld()->GetTimeSeconds() > 5 &&', 'GetWorld()->GetTimeSeconds() > SmokeDelay &&')
    path.write_text(text, encoding='utf-8')
print('Isolated profiling host prepared; ordinary smoke delay remains 5 seconds.')
