# Phase10：泥浆外观与区域控制

日期：2026-10-30。工程：`D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy/FluidNinjaLive.uproject`。

## 直接使用

1. 在研究工程打开 `/Game/MudStudy/Professional/Phase10/L_Mud_Adjustable`。
2. 选中 Outliner 中的 `Integrated_Mud_GlobalNormal`，在 Details 的组件列表选 `MudControls`。
3. 展开 `Mud Controls` 下的 Thickness、Color、Surface、Region 分组。参数显示为中文。不要改动 Surface 的 20×20 缩放，它代表固定 2000×2000 cm 模拟域。
4. 使用 **Simulate / 模拟（Alt+S）** 观察动态泥浆。60秒回放已配置循环。模拟中修改当前模拟对象的 MudControls，实时生效；停止模拟会丢弃运行实例的修改。
5. 要保存设计，在停止模拟后的编辑对象上修改并保存关卡。编辑态提供颜色、区域和材质纹理预览，动态高度/法线和球体接触需要运行模拟。

按钮：**预设：薄湿泥浆**、**预设：厚重泥浆**、**恢复默认**、**应用参数**。默认按钮恢复20 cm、棕色、椭圆；关卡当前保存为20 cm、棕色、不规则轮廓。

## 可调内容

- 厚度0–100 cm（滑条重点范围0–60）：统一控制计算法线高度、POM高度与球体视觉接触。5、20、40 cm已做参数同步检查。厚度表示当前高度场的深度倍率，不会生成有侧壁的实体体积；参考面在顶部，增大后向下加深。
- 浅色、深色、颜色亮度：分别写入原材质的 `Color 1`、`Color 2`、`ColorMult`。颜色沿用原材质混合逻辑。
- 细节强度、细节密度、粗糙度：写入 `ComputedDetailStrength`、两层 `TilingXYMap1/2`、`MainRoughness`。密度越大纹理越密。
- 流动开关、细节流动速度：切换真正的静态/流动父材质，并控制 `DetailFlowUVRate`。这是表面细节移动，不是模拟器黏度。
- 区域形状：完整平面、圆角矩形、椭圆、不规则泥潭。宽高、XY偏移、旋转、矩形圆角、不规则程度、种子均可调。
- 球体视觉接触开关：沿用原GPU高度采样并追加区域边界过渡。进入边缘时平滑回到输入姿态，区域外不提供刚体支撑；模拟/碰撞根仍不被移动。

区域为世界XY平面的可见裁切，模拟仍在完整2000×2000 cm域内进行。缩小轮廓不会减少模拟开销，也不会建立新的流体边界。超出平面部分被平面裁掉；不规则轮廓宽高是基础椭圆尺度，波形可能超出此尺度。现阶段不支持自由画轮廓或任意网格地形。

## 工程与源码

新增资产全部在研究工程 `Content/MudStudy/Professional/Phase10/`：独立关卡、独立回放、两套主材质、两套材质实例、球体材质，共7个资产。

运行代码（实际编译）：

- `D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy/Plugins/MudShaderLab/Source/MudShaderIntegration/Public/MudAppearanceController.h`
- 同模块 `Private/MudAppearanceController.cpp`

工作区可读镜像：`Tools/MudStudy/Runtime/MudAppearanceController.h` / `.cpp`。镜像修改不会自动更新研究工程，需同步并重新编译。

HLSL：`Tools/MudStudy/Reference/MudRegionDistance.hlsl` 和 `SphereHeightContactAdjustable.hlsl`。实际代码已写入Phase10材质Custom节点；修改文本镜像不会自动改写材质。

组件派生自原 `UMudContactController`，调用原厚度/接触同步后再应用外观与区域参数。旧控制器、旧主材质和Phase01–09关卡未改动。研究模块DLL因加入新类重新编译，不能把旧Phase08计时自动套用到本版。

## 验证记录

`Verification/MudProfessional/phase10-adjustable/`：

- `runtime-readback.json`：6组实际PIE读回，覆盖薄/厚/默认、旋转偏移矩形、红色、静态/流动往返切换。共享Normal RT、POM高度、法线高度、球体高度与区域参数一致。
- `persistence.json`：保存后切换地图再载回，不规则轮廓及参数仍在，编辑预览MID重建成功。
- `validation.json`：41项记录检查通过。4张固定相机图的轮廓IoU约0.9975–0.9989，距轮廓外10 cm以上未检出泥浆颜色泄露。分割仅适用于本次蓝天空/棕红泥浆截图，不是通用图像识别或连续接触证明。
- `integrity.json`：146个历史文件中145个未变；唯一预期变化为研究模块DLL。7个新增资产与2个新源码有SHA256记录，新源码与可读镜像一致。
- `ellipse-default.png`、`irregular.png`、`rectangle-rotated.png`、`red-static.png`、`thin-wet.png`、`thick-rough.png`：UE实际截图。原生截图分配缓冲区的IEND后尾部已移除，像素压缩数据和所有PNG块CRC不变，记录见 `capture-container-repair.json`。

本轮检查不证明完整动态等价、物理黏度变化、连续球面接触误差、实时帧率或新版打包验收。先前投递视频仍为Phase09，不自动包含本版控制。

重新检查已有记录（需要NumPy与FFmpeg，不会启动UE）：

```powershell
& D:/aco/python313/python.exe Tools/MudStudy/verify_adjustable_mud.py
```
