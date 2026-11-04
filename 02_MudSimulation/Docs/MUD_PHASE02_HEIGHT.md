# Phase02：高度单位校准（2026-10-29）

后续进展：[Phase03 细节法线接入](MUD_PHASE03_DETAIL.md) 已完成静态验证。

## 结果

当前测试平面上的 POM 与计算法线已经校准到同一高度尺度：**每单位状态纹理 B 对应 20cm**。具体改变是新实验关卡内 `GlobalShaderNormal.HeightScale: 30 → 20`，保留现有 POM 参数和 Phase01 的 UV 对齐。

这修正了旧预设中计算坡度相对 POM 高度放大 1.5 倍的问题。它是当前预设的校准，不是新建一套物理泥浆模型，也没有证明动态等价或最终画质。

## 如何确定 20cm

直接从 `/Engine/BasicShapes/Plane` 读取的四个顶点覆盖 [-50,50]，UV0 满足 `u=x/100+0.5, v=y/100+0.5`。实际 Surface 缩放 (20,20,1)，Actor 使用原点、零旋转、单位缩放，因此纹理一单位 UV 覆盖 2000cm。

POM 的 `ratio = ParallaxHeight * RebuildHeightScale = 0.01 * 1`，在此映射下高度尺度是 `0.01 * 2000 = 20cm`。

**2026-10-29 Phase07 更正：** 原文用 `z = 20 * (h - 0.9)` 同时解释可见 UV 与像素深度，这不准确。实际 Custom26 对 UV 使用 ReferencePlane 偏移，但 PDO 距离仍从高度 1 向下累计；参考面小于 1 时，startUV 的导数也会影响深度换算。Phase02 的坡度比例与 CPU UV 求交检查仍成立，但它们没有验证 PDO 的几何接触。新 Phase07 实例将实际参数 `ParallaxPlane` 设为 1，使此预设的 UV 与深度统一到 `z = SimCenter.z + 20 * (h - 1)`，历史 Phase02 资产保持不变。

计算法线使用 `dx = HeightScale * Δh / Δx_cm`，Y 同理，再归一化 `(-dx,-dy,1)`。旧值 30 把坡度放大到 20cm 模型的 1.5 倍；这是坡度比例，不是归一化法线长度比例。

## 已落地资产

研究工程：`D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy/FluidNinjaLive.uproject`。

- `/Game/MudStudy/Professional/Phase02/L_Mud_HeightCalibrated`：复制 Phase01，主 Actor 的计算高度保存为 20，SurfaceMaterial 指向新 MI。
- `/Game/MudStudy/Professional/Phase02/MI_Surface_HeightCalibrated`：继承 Phase01 的 `M_Surface_AlignmentAB`；NormalAlignToPOM=1，POM 比例仍继承 0.01，RebuildHeightScale 仍为 1。
- `/Game/MudStudy/Professional/Phase02/M_HeightFixture`、`RT_HeightFixture`：用于重建 16×16 校准输入，包含线性斜坡、平面、尖峰和凹坑。RT 像素本身不随资产保存，重新测试时必须先绘制 fixture 材质。

原始 106 个基线文件和 Phase01 的 3 个新资产，共 109 个文件哈希均未改变。新资产快照在 `Verification/MudProfessional/phase02-height/Assets/`，依赖研究工程已有插件与资源，不是独立交付包。没有修改插件 C++ 或原始 Shader。

## 检查范围和证据

证据目录：`Verification/MudProfessional/phase02-height/`。

1. 原有 `Mud.ShaderLab.HeightNormalGPU` 在研究编辑器运行通过：1 项测试、0 错误、0 警告。这是既有的 19×13 / 1×1 GPU 用例，不是下面的新增测试。
2. 新增真实 GPU 读回：16×16，分别运行高度 0/20/30、世界范围 2000×2000，以及高度 20、世界范围 32×64，共四组 1024 像素。输入纹理先读回并核对 fixture，源 B 误差为 0。
3. 输出 RGB 与有限差分参考、线性斜坡解析法线比较；最大编码误差 0.000484485，小于沿用的 RGBA16F 容差 0.001。Alpha 与源高度的复制误差为 0。零高度时所有法线精确为 (0.5,0.5,1)。非方形范围仅验证计算法线，不代表现有标量 POM 支持非方形表面。
4. 54 组 CPU POM UV 求交检查：将现有 marching 算法的 CPU 翻译与线性高度面的闭式射线交点比较，最大 UV 误差约 1.11e-16。覆盖平面、正负梯度、零高度、两个采样步数与三个观察方向。**这不是 GPU POM、PDO 或纹理过滤验证。**
5. 实际运行时：计算高度 20、WorldSize 2000×2000、POM 比例约 0.01、倍率 1、NormalAlignToPOM=1、UseGlobalNormal=1；计算出的 POM 高度约 19.99999955cm。法线纹理参数与 NormalPass.NormalOutput 对象一致，dispatch 计数大于零。

主要文件：`gpu_readbacks_verified.json`（完整成功读回）、`runtime_evidence.json`（运行时绑定与相机）、`calibration_results.json`（重新计算结果）、`integrity.json`（原资产完整性）、`calibrated_runtime.png`（实图）。本次实图与 Phase01 不是同一模拟状态，不能拿来量化前后画质差异。

初次非方形用例发生过一次临时 RT 被 GC 回收导致读取失败，保留在 `gpu_readbacks.json`。随后创建支持 UAV 的新 RT，并在实验 Actor 的 transient NormalOutput 属性持有引用，重新 dispatch 和 readback 成功。测试结束后已清空该引用；普通运行会创建自己的 RT。失败未计为通过。

## 复核和重跑

在 Stormfall 根目录运行 `python Tools/MudStudy/verify_height_calibration.py`，只需 Python 标准库。它会重新检查**已有 GPU 读回记录**、验证当前记录的运行时高度关系，并生成 calibration_results.json；不会启动 UE 或重新运行 GPU。

重新采集 GPU 数据的已执行链路如下（通过原生 UE MCP）：

1. 在实验关卡的编辑状态，将 M_HeightFixture 用 KismetRenderingLibrary.DrawMaterialToRenderTarget 绘制到 RT_HeightFixture。
2. 用 KismetRenderingLibrary.CreateRenderTarget2D 创建 16×16、RTF_RGBA16f、bSupportUAVs=true 的独立目标，保持 UObject 引用以防 GC。普通资产创建工具当前不能设置该非反射 UAV 标志，所以不能直接用普通目标 RT 替代。
3. 调用 MudShaderLibrary.DispatchHeightNormal，Source 和 Destination 必须不同；按上述四组 HeightScale/WorldSize 逐组运行。
4. 每组使用 KismetRenderingLibrary.ReadRenderTargetRaw，bNormalize=false，读出 256 个 LinearColor；必须检查成功、长度与有限值。Dispatch 返回 True 只表示接受排队，不能当作 GPU 验证通过。
5. 结束后释放测试引用；保留源纹理和目标读回，重新运行 Python 比较。测试同步读回只用于验收，不进入正常每帧流程。

## 下一步和边界

- 当前已校准数值，但参数仍分布在组件与材质两处。后续若开放高度调节，需要建立单一高度控制并同步两端，或运行时校验；不能宣称已经防止未来参数漂移。
- 旋转、非均匀缩放、非方形 POM、负高度与任意 UV 平铺尚未支持或验证。上述 20cm 结论仅适用于已核对的当前平面。
- 下一项先恢复细节法线：查清原分支的大形变与流动细节，避免整条原法线和计算法线相加而重复计算大坡度，再做固定输入的开关对照。
- 随后补确定性输入回放和动态稳定性，最后再测完整效果 GPU 成本。本轮没有新性能数据、打包检查或完整动态等价结论。
