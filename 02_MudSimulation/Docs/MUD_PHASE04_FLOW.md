# Phase04：速度驱动的细节流动

后续进展：[Phase05 可重放交互与自动采集](MUD_PHASE05_REPLAY.md) 已落地；轨迹与局部状态检查通过，流畅成片采集尚待解决。

已在独立实验关卡接入带符号速度驱动的双相细节法线，保留 Phase03 的 POM 对齐与坡度混合。完成 GPU 算术和真实材质的可控速度验证。持续移动笔刷、停留和边界下的完整交互尚未验收。

## 速度与位移

`niagara_solver_stage8.py` 的 Advection 用 `back = uv - velocity * (1 / grid_size) * SimSpeed`，在固定步内执行。`niagara_author_stage7.py` 的 Export 保留 RG 符号，并乘边缘衰减；B 则为转换后的可见高度。运行时查到 SimSpeed=8，既有网格证据为 2048²、固定 dt=0.01667。

因此为当前预设使用 `DetailFlowUVRate = 8/(2048*0.01667) = 0.2343281344`，单位是每单位导出速度对应的模拟 UV/秒。此处使用的是求解网格 2048，不是输出纹理 512。导出的边缘衰减已经存在，不应再次除掉。这个换算是从当前平流公式得到的局部映射，不代表导出速度就是输入物体的厘米每秒速度。

换算常数保存在材质参数中，没有自动跟随 Niagara 改配置；修改 SimSpeed、网格或固定步长后必须重算。非方形网格当前未覆盖。

## 采样与合成

Common Custom 212 在 POM 命中点读取 RG（源节点18），形成每周期的模拟 UV 位移；163/170 各乘自己的平铺尺度，转换到细节纹理坐标。采样方向取负，使每个活动相位使用回溯坐标。两组相位错开半周期，在重置处将该组权重平滑降为零；坡度先在两相之间混合，再进入 Phase03 的大坡度与细节坡度合成。

两相权重使用平滑三角函数 `r*r*(3-2*r)`，r 为三角权重。每层使用六次高度采样（两相各中心/X/Y），两层共十二次，前一版为六次；本轮没有测完整 GPU 成本。采样使用原始平铺 UV 的 ddx/ddy 作梯度，避免将速度跳变直接放大到 mip 梯度中；速度剧烈变化处的过滤品质仍需场景验证。

这是周期性的局部速度流动着色，没有持续保存并运输一张微高度纹理；它不保证一个微表面特征跨多个周期保持同一身份，也不保证瞬时速度变化时纹理路径与模拟轨迹严格重合。

## 保存位置与控制

研究工程：`D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy/FluidNinjaLive.uproject`。

- `/Game/MudStudy/Professional/Phase04/L_Mud_FlowDetail`
- `/Game/MudStudy/Professional/Phase04/M_Surface_FlowDetail`
- `/Game/MudStudy/Professional/Phase04/MI_Surface_FlowDetail`
- 同目录 M_FlowFixture / RT_FlowFixture 为数值验证资产。

DetailFlowUVRate：换算系数，设为 0 可关闭流动位移。DetailFlowPeriod：周期秒数，默认1，代码至少限制为0.001。DetailFlowTimeOverride：默认-1读取原有时间节点；非负值用于冻结流动时钟。

DetailFlowTestVelocity 为验证入口：XY 指定速度，Z=1 启用，Z=0 关闭；默认全零。正常材质读取模拟速度。测试结束已读回确认入口关闭、时钟=-1、换算系数恢复。它们都只在运行时 MID 上临时改变，保存的实验资产没有启用测试速度。

214 个节点全部可达，图验证无问题。HLSL 可读副本为 `Reference/DetailFlowPhases.hlsl` 和 `Reference/FlowDetailNormal.hlsl`，已与实际资产读回代码核对。副本不自动同步到资产。原始及前三阶段共118个文件哈希未变，见 integrity.json；新资产快照仍依赖研究工程资源。

## 验证记录

证据目录：`Verification/MudProfessional/phase04-flow/`。

GPU fixture 覆盖 5 种速度（零、正负X、正负Y）与12个时间点，共60个像素。用同一相位和坡度代码，将纹理读取替换为解析正弦高度函数，以便与独立 CPU 参考比较；前半列使用正常速度输入，后半列清空正常输入、改用验证入口，覆盖两条选择路径。该 fixture 不验证纹理过滤，也不代表整套动态等价。

- 最大编码RGB误差 0.000382693，小于半精度容差0.001。
- 零速度下所有时间结果一致；相隔一周期的结果一致。
- 正负速度输出可区分，并符合带符号参考值。这里确认运算方向，不宣称连续运动时纹理特征的绝对位移已经与模拟轨迹吻合。
- 0.5与1.0附近 ±0.0001 的 GPU 样本在半精度读回下相同；CPU 在 ±0.00001 的最大差约5.88e-7。这是所测输入的连续性交接证据。

真实材质第一组冻结模拟时刻为11.66680181，改变测试时钟0.125/0.375所得图完全一致。此前尝试读取中心时用了 PixelX/PixelY，而引擎函数实际参数名为 X/Y；那次读回不能当作中心速度为零的证据，也不能据此确定图像相同的原因。此组没有证明可见流动，不能误报为通过。

随后在第二次运行的同一冻结时刻5.3333348，给实际材质输入可控速度(0.5,0)，测试时钟从0.125到0.375：1280×720全帧平均RGB差约0.8965，164948个像素存在任一通道大于2的差异。保持这个非零验证速度、将换算率设为0后，改变测试时钟的图像差为0。它支持真实材质的纹理采样分支会对速度/时间做出响应，而不是持续移动笔刷已经验收。

最初视口截图请求只排队而没有落盘，故改用临时 SceneCapture PNG。它们采用固定相机(0,1250,600)、旋转(-28,-90,0)、FOV55；视口EV设置不控制独立捕获的曝光，捕获使用自己的默认设置。图中有单帧噪点；重复捕获差为0，各自的 captureMetadata 已保存。`comparison.png` 为可控速度两时刻的相同裁切，无调色；不是最终作品集画面。

采集中曾因把 HLSL 保留字 triangle 用作变量名而编译失败，读回全黑；失败证据在 gpu_fixture.json。修正为 phaseRamp 后重编译，最终证据为 gpu_fixture_final.json。失败没有计为通过。异步视口请求对应的 T0125/T0375 文件即使日后落盘，也不参与本轮对照。

最终已退出SIE、脏包为零。gpu_fixture_final.json、flow_results.json、controlled_runtime_evidence.json、final_audit.json、image_metrics.json 和 integrity.json 分别保存算术、运行时、实际代码、图像与完整性证据。

## 复核与下一步

`python Tools/MudStudy/verify_detail_flow.py` 重新检查已保存的 GPU 读回、源代码与实际节点、可控图像差异和参数恢复状态；不会重新启动GPU采集。PowerShell脚本 `measure_phase04_images.ps1` 重算已有图片并生成对比图，依赖 Windows System.Drawing。

重采GPU：将 M_FlowFixture 绘制到 RT_FlowFixture，再调用 ReadRenderTargetRaw（bNormalize=false）；RT像素不随资产保存。

下一项需要持续且可重放的笔刷轨迹：在运动中、停留后和交互边界采集速度场/材质帧，并检查变化速度、相位交接、不同帧率和整体GPU成本。本轮无打包测试或完整动态等价结论。
