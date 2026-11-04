# Phase01：POM 与计算法线采样对齐

后续进展：[Phase02 高度尺度校准](MUD_PHASE02_HEIGHT.md) 已落地；本文件保留第一阶段的原始结论和实验记录。

本轮处理泥浆。R02 由用户独立推进。使用工程专用的 stormfall-material-assistant 工作流，检查源代码、资产图与运行时证据。

## 当前结论

完成一个隔离的修复候选：表面颜色和原法线已经使用 POM 命中 UV，新增计算法线原来却用未偏移的世界 XY 坐标。现在增加 `NormalAlignToPOM` 开关，使计算法线可以读取同一 POM 命中点。

这是**静态坐标一致性**验收。没有声称完整动态等价、法线幅度正确、性能改善或达到最终作品集质量。

## 实际修改

独立研究工程：`D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy/FluidNinjaLive.uproject`。

新资产统一位于 `/Game/MudStudy/Professional/Phase01/`：

- `L_Mud_AlignmentAB`：复制整合关卡，主 Actor 指向实验 MI。
- `M_Surface_AlignmentAB`：复制原材质，仅改变计算法线的采样坐标选择。
- `MI_Surface_AlignmentAB`：复制并重设父材质，最终保存 `NormalAlignToPOM=1`；改为 0 即返回原坐标路径。

图连接：Custom 26 的 POM 输出 → Mask 32（RG）→ Custom 200 的 `ParallaxUV`；Scalar 204 → `AlignToPOM`。Custom 200 原有 Texture/World/Center/Size 输入保留，后续 World→Tangent 201 和混合 203 保留。父材质开关默认值为 0，实验 MI 覆盖为 1。节点编号仅适用于本轮保存的图。

HLSL 可读副本在 [ComputedNormalPOMAlignment.hlsl](Reference/ComputedNormalPOMAlignment.hlsl)。该文件不会自动同步到资产：资产由原生 UE MCP 图工具写入，后续改源码也必须同步 Custom 节点并重新编译。

## 验证记录

数据目录：`Verification/MudProfessional/phase01-70105e39/`。

- 在 SIE 中冻结 game time = 19.073341；结束采集时再次读回相同值，Actor 记录的 ProducerGraphDispatches 为 611。没有逐像素导出 RT，也没有证明所有渲染线程状态完全静止。
- 视口 2521×1660，FOV 55，固定 EV100=0，Game View 开启。
- 普通视角：位置 (0,1250,600)，旋转 Pitch=-28、Yaw=-90、Roll=0。
- 低角度：位置 (0,1000,240)，旋转 Pitch=-15、Yaw=-90、Roll=0。
- `UseGlobalNormal=1`。普通 A/B 只切换 `NormalAlignToPOM`；负对照额外将 `RebuildHeightScale=0`，然后只切换对齐参数。负对照结束恢复 HeightScale=1。
- A 重拍与 B 切回 A 用于估算时序渲染噪声。暂停游戏仍不保证截图完全一致。

全帧 RGB 8-bit 平均绝对差异：A 重拍 0.422；切回 A 0.529；POM=0 的 A/B 0.478；正常 POM 的 A/B 1.954；低角度 A/B 2.098。关闭 POM 后差异接近测得噪声水平，支持偏移来自 POM 坐标选择。**像素差异数值不是画质评分，不能单独证明 B 更正确。** 结合图中实际连接与沟槽高光位置，接受此候选继续验证。

`image_metrics.json` 还保留固定矩形 (500,600,1500,700) 的统计；所有输入图片使用完全相同的矩形。`comparison.png` 是普通视角相同矩形的并排裁切，没有调色。`initial_A.png` 使用不同曝光且有编辑器网格，不参与任何对照。

图结构验证：205 个节点均可达，issues 为空。运行时已显示该材质并验证参数切换。本轮未重新打包、未做新 GPU 性能测量，也未把图结构验证当成所有平台编译通过。

原始 106 个基线文件 SHA-256 全部未变，见 `integrity.json`；三个新资产的快照和哈希也在同目录。该快照依赖研究工程已有内容和插件，不是独立可运行项目。实验 MI 保存后确认没有脏包，SIE 已结束。

## 重看和继续

1. 在研究工程打开实验关卡并运行，确认主 Actor 使用实验 MI。
2. 在同一次模拟中暂停后，切换运行时 MID 的 `NormalAlignToPOM`，固定相机与曝光拍摄。直接编辑 MI 适合下一次启动的默认配置；当前 MID 应使用运行时参数接口。
3. 重算现有截图指标：在 Stormfall 根目录用 PowerShell 7.6 / .NET 10 执行 `./Tools/MudStudy/measure_phase01_images.ps1`。脚本只读截图，覆盖本轮 metrics 和对比图。当前实现依赖 Windows System.Drawing；其他 PowerShell/.NET 版本未验证。

本轮保存的是一次运行的图片证据，尚无可跨启动复现同一 RT 的输入回放或状态存档。下一轮需要补齐确定性输入/RT 冻结方式。

## 下一步验收顺序

1. **统一高度单位**：当前 Compute HeightScale=30；POM ratio=0.01、平面跨度 2000cm，在单位 UV 覆盖整面的假设下对应 20cm。先用线性斜坡、峰谷、零高度确认单位、方向与映射，再决定统一参数；不凭画面直接改成 20 或 30。
2. **恢复细节法线**：UseGlobalNormal=1 会完全覆盖原法线分支。区分大形变法线与流动微表面法线，建立各自强度和正确混合；保持采样点一致。
3. **动态验证**：固定路径、速度、步长和相机，检查连续移动、停留、重叠、边界、帧率变化及纹理时序。低角度另查 POM 拉伸与闪烁。
4. **展示与成本**：完成干湿分层和可读场景后测整体 GPU 成本，再整理镜头、消融对照与个人贡献说明。

面试可讲的核心：POM 求出了视线与虚拟高度面的交点；在旧 UV 读法线，就可能用另一个位置的坡度给这个交点打光。修复时复用已有 POM 结果；通过关闭偏移的负对照和重复截图，排除基础坐标差异与截图噪声的主要影响。旋转平面、非方形范围和缩放后的映射尚未验证。
