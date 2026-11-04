# Phase03：恢复细节法线

后续进展：[Phase04 速度驱动细节](MUD_PHASE04_FLOW.md) 已完成算术和真实材质可控输入验证。

已在独立实验材质中接回两层平铺细节，使用 POM 命中坐标，并通过坡度相加保留已校准的 20cm 大形变法线。实验 MI 的 `ComputedDetailStrength=1`；在 `UseGlobalNormal=1` 时设为 0，可回到仅计算法线的对照。

这轮验证的是静态细节接入。原细节层的 OffsetAnimated 参数为零；本轮没有新加速度平流，因此不能称为已经恢复了随泥浆运动的流动法线。

## 源头与接法

原图 138 的法线来自 139：主密度法线 140/141，加上遮罩后的平铺细节 147，再乘 TwoSidedSign。147 的两个纹理源为 TileMap1（T_NoiseTemplate1）、TileMap2（T_foam5），经过各自有限差分，再按原来的密度、速度相关遮罩和距离权重参与输出。它们与独立的双相 FlowMap 颜色采样分支不同。

原来的计算法线开关设为 1，会绕过这两层细节。新图将 147 作为细节贡献，201 作为已变换到切线空间的计算法线；新节点 206 只使用细节 XY，忽略原平铺向量累加附带的 Z 偏置：

`normalize(float3(n.xy + Detail.xy * max(Strength,0) * n.z, n.z))`

对当前正面高度场，它等价于将大形变和微表面的坡度相加。没有从 138 整条原法线中取数据，因此不会把主密度坡度再次叠加。细节强度仍沿用原来的经验系数，本轮没有给微表面高度建立新的厘米标定。

两个新 UV 节点 207/208 使用 `TileUV + (ParallaxUV - BaseUV) * Tiling`，使原有平铺、偏移保持在 POM 命中点上。只改细节法线的 UV 输入；TileUV 的其他消费者保持原连接。由于 163/170 仍被旧法线支路共享，UseGlobalNormal=0 的支路也会使用校正后的细节 UV；它不再是逐位不变的旧版对照。

## 保存位置

研究工程：`D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy/FluidNinjaLive.uproject`。

- `/Game/MudStudy/Professional/Phase03/L_Mud_DetailNormals`
- `/Game/MudStudy/Professional/Phase03/M_Surface_DetailNormals`
- `/Game/MudStudy/Professional/Phase03/MI_Surface_DetailNormals`
- 同目录的 `M_DetailBlendFixture` 和 `RT_DetailBlendFixture` 为 GPU 算术检查资产。

HLSL 可读副本：`Reference/ComputedDetailSlopeBlend.hlsl`、`Reference/DetailPOMUV.hlsl`。源文件与资产不自动同步；本轮由原生 UE MCP 图工具写入，并已读回 206 的实际代码核对。图验证 209 个节点全部可达、issues 为空。没有修改插件或原始 Shader。

## 已执行验证

证据位于 `Verification/MudProfessional/phase03-detail/`。

GPU 小样使用与正式混合节点相同的算术，绘制到 4×5 RGBA16F 目标，再以 bNormalize=false 读取 20 个像素，与高度梯度的解析法线比较。覆盖四档基础坡度，以及零强度、零细节、普通细节、Detail.z 从 1 改成 999、相反坡度抵消五类输入。

最大编码 RGB 误差为 0.000380465，小于 0.001 容差；零强度与零细节结果一致，改变细节 Z 不影响结果，相反坡度恢复竖直。这里检查的是合成算术，不是整张材质的逐像素数值等价。

真实材质截图：游戏时间在参数切换前后均为 49.028778，Actor 缓存 dispatch 计数均为 2913。位置 (0,1250,600)，旋转 (-28,-90,0)，FOV55，固定 EV100=0，2521×1660。游戏暂停不意味着所有渲染时序噪声消失，因此保留 A 重拍估计噪声：

- A：ComputedDetailStrength=0，RebuildTileNormalScale=1。
- B：ComputedDetailStrength=1，RebuildTileNormalScale=1。
- C：ComputedDetailStrength=1，RebuildTileNormalScale=0，细节归零的负对照。

全帧 RGB 8-bit 平均绝对差异：A 重拍 0.4802，A/B 0.9767，A/C 0.5307。细节开启的差异高于重复截图，细节归零后回到接近噪声的水平；结合图连接与实图，支持效果来自细节坡度。该数值不是画质得分，也不证明动态稳定性。

`comparison.png` 对两个原图使用相同裁切 (500,350,1500,700) 和缩放，没有调色。原图、GPU 原始读回、运行时参数、节点连线、验证结果及新资产快照均已保存。原始基线及前两阶段共 113 个文件 SHA-256 无变化；研究工程已退出 SIE，脏包为零。新资产快照依赖研究工程既有资源，不能单独运行。

## 复核

- `python Tools/MudStudy/verify_detail_blend.py`：重新检查已有 GPU 读回与实际节点代码，生成 blend_results.json；不会重新运行 GPU。
- PowerShell 7.6 / .NET10：`./Tools/MudStudy/measure_phase03_images.ps1` 重新比较已有截图、生成 image_metrics.json 和 comparison.png。依赖 Windows System.Drawing。
- 重采 GPU：将 M_DetailBlendFixture 用 KismetRenderingLibrary.DrawMaterialToRenderTarget 绘制到 RT_DetailBlendFixture，再 ReadRenderTargetRaw（bNormalize=false）。RT 像素不会随资产保存，必须重新绘制。
- 实际查看：打开实验关卡运行，固定状态后切换运行时 MID 的 ComputedDetailStrength。MI 保存值为 1。当前检查只覆盖轴对齐平面的正面显示。

下一项是速度驱动的细节平流：先明确速度到纹理位移的单位，验证零速度不漂移、正负速度方向、双相交接连续性，再做移动/停留/边界的固定输入对照。本轮没有新性能数据、打包测试或完整动态等价结论。
