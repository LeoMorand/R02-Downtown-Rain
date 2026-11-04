# R02 water trial — 2026-10-31

Open `/Game/Stormfall/WaterTrial/L_R02_WaterPreview` in Stormfall. This is a duplicate of `/Game/TA_Demos/R02_Downtown_Rain`, with one `R02_InteractiveWater` actor on the plaza at `(5650,-450,2.57704544)` cm. Both trial PlayerStarts are near the puddle; Play uses the existing WeatherSystem third-person character. Original R02 maps, shared materials and plugin binaries were not edited.

## Assets and controls

- Master: `/Game/Stormfall/WaterTrial/M_R02_Water_Flow`
- Instance: `/Game/Stormfall/WaterTrial/MI_R02_Water_Flow`
- Solver: `/Game/MudStudy/Professional/Phase19/NS_Water_Interactive`
- Visible region: irregular, 650 × 420 cm; simulation domain: 2000 × 2000 cm.
- Simulation output and computed normals: 2048 × 2048 each. Normal HeightScale: 1.5 cm.
- WaterOpacity 0.08, MainRoughness 0.035, ComputedDetailStrength 0.12, ParallaxHeight 0.00075.
- Surface collision disabled through actor collision; original street supports the character. NormalPreview diagnostic plane hidden.
- MI `MudRegionSize`, `MudRegionSettings`, `MudRegionShape`, `Color 1`, `WaterOpacity`, `MainRoughness` remain editable.
- RegionCenter uses MudSimCenter, updated by the native actor in Play. After moving the actor in the editor, update the MI MudSimCenter for an accurate editor preview; Play binds it automatically. Move before starting Play, because Niagara SimCenter is initialized at BeginPlay.

## Evidence and limits

`Verification/MudProfessional/phase20-r02-water/walk-check.json` records an actual Enhanced Input walk from x=5300 to x=5779, no falling, live output and normals both 2048². The center probe mean absolute velocity changes from zero to 0.02882 and mean B from 0.80425 to 0.85076 as the character crosses. This validates the input→solver→RT path for the trial, not physical water equivalence or frame performance.

The per-frame check uses `r02_water_walk_check.py` through the editor Python API because the generic UFUNCTION bridge cannot construct FInputActionValue and does not provide a timed per-frame vector injection action. It only modifies the PIE session and writes verification JSON.

Native viewport screenshots are saved alongside the JSON. R02's existing wet ground makes shallow transparent water subtle. The session displayed video-memory-over-budget warnings (roughly 0.9–1.5 GB); this trial is not performance-qualified. Preview screen percentage was reduced temporarily to 60; no config file was changed.

Native material connect resolved the requested expression name to the wrong node. Fixed the Custom Inputs RegionCenter object reference explicitly and verified readback before saving the new master. No shared master was modified.
