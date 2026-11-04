#include "MudShaderLibrary.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Engine/TextureRenderTarget2D.h"
#include "TextureResource.h"
#include "UObject/StrongObjectPtr.h"
#include "RenderingThread.h"
#include "RHICommandList.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMudHeightNormalTest, "Mud.ShaderLab.HeightNormalGPU",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FMudHeightNormalTest::RunTest(const FString& Parameters)
{
    if (GUsingNullRHI)
    {
        AddError(TEXT("This test requires a real GPU RHI; NullRHI is not a GPU pass."));
        return false;
    }
    // Non-multiple-of-eight dimensions exercise dispatch bounds. 1x1 exercises
    // derivative denominators and no-neighbor behavior.
    for (const FIntPoint Extent : {FIntPoint(19, 13), FIntPoint(1, 1)})
    {
        TStrongObjectPtr<UTextureRenderTarget2D> Source(NewObject<UTextureRenderTarget2D>());
        TStrongObjectPtr<UTextureRenderTarget2D> Output(NewObject<UTextureRenderTarget2D>());
        for (UTextureRenderTarget2D* RT : {Source.Get(), Output.Get()})
        {
            RT->bCanCreateUAV = true;
            RT->InitCustomFormat(Extent.X, Extent.Y, PF_FloatRGBA, true);
            RT->UpdateResourceImmediate(true);
        }
        TestFalse(TEXT("Reject aliasing"), UMudShaderLibrary::DispatchHeightNormal(Source.Get(), Source.Get()));
        TestFalse(TEXT("Reject zero world size"), UMudShaderLibrary::DispatchHeightNormal(Source.Get(), Output.Get(), 1, FVector2D::ZeroVector));
        TestFalse(TEXT("Reject null source"), UMudShaderLibrary::DispatchHeightNormal(nullptr, Output.Get()));

        for (int32 Fixture = 0; Fixture < 3; ++Fixture)
        {
            TArray<FFloat16Color> Pixels;
            Pixels.SetNum(Extent.X * Extent.Y);
            for (int32 Y = 0; Y < Extent.Y; ++Y)
            for (int32 X = 0; X < Extent.X; ++X)
            {
                const float H = Fixture == 0 ? 0.25f : Fixture == 1 ? (X + 2 * Y) / 64.0f :
                    ((X == Extent.X / 2 && Y == Extent.Y / 2) ? 1.0f : 0.0f);
                Pixels[Y * Extent.X + X] = FFloat16Color(FLinearColor(0, 0, H, 1));
            }
            auto* Resource = Source->GameThread_GetRenderTargetResource();
            ENQUEUE_RENDER_COMMAND(MudUploadFixture)([Resource, Extent, Pixels](FRHICommandListImmediate& RHICmdList)
            {
                RHICmdList.UpdateTexture2D(Resource->GetRenderTargetTexture(), 0,
                    FUpdateTextureRegion2D(0, 0, 0, 0, Extent.X, Extent.Y),
                    Extent.X * sizeof(FFloat16Color), reinterpret_cast<const uint8*>(Pixels.GetData()));
            });
            constexpr float HeightScale = 8;
            TestTrue(TEXT("Dispatch accepted"), UMudShaderLibrary::DispatchHeightNormal(Source.Get(), Output.Get(),
                HeightScale, FVector2D(Extent.X * 2, Extent.Y * 4)));
            FlushRenderingCommands(); // Test-only synchronization, never in the runtime dispatch.
            TArray<FFloat16Color> Actual;
            if (!Output->GameThread_GetRenderTargetResource()->ReadFloat16Pixels(Actual) || Actual.Num() != Pixels.Num())
            {
                AddError(TEXT("GPU readback failed"));
                return false;
            }
            float MaxError = 0;
            auto Height = [&](int32 X, int32 Y) { return Pixels[Y * Extent.X + X].B.GetFloat(); };
            for (int32 Y = 0; Y < Extent.Y; ++Y)
            for (int32 X = 0; X < Extent.X; ++X)
            {
                const int32 L = FMath::Max(X - 1, 0), R = FMath::Min(X + 1, Extent.X - 1);
                const int32 D = FMath::Max(Y - 1, 0), U = FMath::Min(Y + 1, Extent.Y - 1);
                const float DX = (Height(R, Y) - Height(L, Y)) * HeightScale / (FMath::Max(R - L, 1) * 2);
                const float DY = (Height(X, U) - Height(X, D)) * HeightScale / (FMath::Max(U - D, 1) * 4);
                const FVector3f N = FVector3f(-DX, -DY, 1).GetSafeNormal() * 0.5f + FVector3f(0.5f);
                const FLinearColor Expected(N.X, N.Y, N.Z, Height(X, Y));
                const FLinearColor Got = Actual[Y * Extent.X + X].GetFloats();
                for (int32 C = 0; C < 4; ++C)
                {
                    if (!FMath::IsFinite(Got.Component(C)))
                    {
                        AddError(TEXT("Non-finite GPU output"));
                        return false;
                    }
                    MaxError = FMath::Max(MaxError, FMath::Abs(Expected.Component(C) - Got.Component(C)));
                }
            }
            AddInfo(FString::Printf(TEXT("%dx%d fixture=%d max_abs_error=%.9g"), Extent.X, Extent.Y, Fixture, MaxError));
            TestTrue(TEXT("GPU matches CPU reference within RGBA16F tolerance"), MaxError < 0.001f);
        }
    }
    return !HasAnyErrors();
}
#endif
