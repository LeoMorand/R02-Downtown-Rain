# R02 Downtown Rain · Shader 与系统说明

本说明对应 2026-10-24 的主工程实装。R02 是既有城市场景的天气材质接入；M13–M19 屋顶雨棚是另一条历史实现，不能把两者合计为同一套已经集成的系统。

## 状态链路

`WeatherManagmentBP / BP_WeatherArtController → MPC_RoadWeather → MF_WeatherArtistState → 各类 Weather 母材质 → 保留继承关系的实例 → 场景组件材质槽位`。

管理器负责自动雨量与表面湿度，控制器提供编辑器预览和 Play 手动模式。默认 Play 使用自动天气；手动湿润、雨量和积水相互独立。控制器和共享状态函数负责全局倍率，各实例保留原贴图、局部遮罩、粗糙度和水痕强度。

## 六个天气母材质

- `/Game/Downtown_West/Materials/M_Ground_Master_Weather`：硬质地面，包含湿润、积水遮罩和世界坐标涟漪。
- `/Game/Stormfall/Weather/M_Ground_Soil_Weather`：土壤湿润，保留原底材细节。
- `/Game/Stormfall/Weather/M_Ground_Special_Weather`：建筑材质派生的特殊地面湿润。
- `/Game/Stormfall/Weather/Objects/M_Object_Default_Weather`：长椅、消防栓等已接入物体。
- `/Game/Stormfall/Weather/Objects/M_Object_Building_Weather`：已接入砖墙样本。
- `/Game/Stormfall/Weather/Objects/M_WindowGlass_Rain`：窗玻璃湿润与滑落水痕。

六个母材质本轮均在独立进程重新编译，错误数组为空。土壤、特殊地面没有因此新增积水或流体计算。

## 地面湿润与积水

`MF_GroundWetness` 对湿润值 Saturate 后，分别插值干/湿颜色和干/湿粗糙度。原有颜色纹理、法线和实例参数保留。

积水 Custom 节点先将自动湿度转换为延迟成长阶段；手动模式改用 ManualPuddles。对阶段作 smoothstep 型平滑 `g=w*w*(3-2*w)`，再结合最大覆盖、局部积水量、全局覆盖倍率，移动固定高度遮罩上的阈值。这样水洼可以扩展，空间遮罩不随湿度一起缩放。

导出参考为 `Verification/WeatherReuse/Learning/PuddleMask.hlsl`。它是材质代码快照；修改文件不会自动更新 `.uasset`。

## 世界坐标涟漪

实际代码在地面母材质的 `MaterialExpressionCustom_2`，11 个输入为世界位置、时间、局部间距/半径/频率/密度，以及美术大小、密度、速度、强度、随机度。代码快照位于 `Tools/R02/ripple_candidate.hlsl`；虽然文件沿用 candidate 名称，本轮已按 SHA256 校验并安装到资产。

算法扫描 3×3 相邻单元，每格两条候选事件通道，每条考虑当前和上一周期，共最多 36 个候选。整数 hash 产生稳定的相位、落点、寿命、半径和幅度。两通道按 `1-0.5r` 与 `0.5r` 接受事件，让高随机度出现空隙和聚集，同时保持每格候选期望数为 1。

圆环半径随年龄增长。Gaussian 环脊的解析斜率累加为世界空间法线，随后 World→Tangent 变换，经过雨量、局部强度和积水遮罩进入地面 Normal。像素 footprint 由 `ddx/ddy` 计算，用于远处过滤。

本轮修正最终寿命的两周期上界：`min(lerp(...),1.95/rate)`。旧版只限制其中一个寿命分支，高频时可能提前丢弃仍存活的事件。新增 footprint 超出所有事件最大半径、密度或强度为零时的平法线早退；导数仍在分支之前计算。

这里表现的是法线扰动。半径以厘米计，但没有真实水深、流量、质量守恒、几何水面厚度或逐像素湿润历史。

## 玻璃与物体世界向下水痕

玻璃原有 `MF_GlassWorldSlideUV` 使用：

```hlsl
float u = abs(N.x) > abs(N.y) ? P.y : P.x;
return float2(u, -P.z) / max(SizeCm, 1.0);
```

时间驱动的 V 偏移因此沿世界负 Z 方向移动，不依赖网格 UV 的旋转。它适合静态、近垂直表面；主轴投影在曲面和拐角上仍可能存在接缝，不能作为连续曲面流动的通用解。

本轮为物体建立独立 `MF_ObjectWorldSlideUV` 和 `MF_SurfaceRainWorld`。只有两个活动物体 Weather 母材质切换到新函数；旧 `MF_SurfaceRain` 及依赖它的历史备份保留。独立尺寸参数为 ObjectPatternSizeCm。

新增竖直表面水痕权重：

```hlsl
return 1.0-smoothstep(0.45,0.85,abs(N.z));
```

该权重乘在水痕法线覆盖上，抑制长椅坐面等水平表面的滑落水痕，不取消这些表面的湿润颜色和粗糙度响应。水痕来自既有 SlidingDrops/DropsMask/DropsNormal 纹理函数，不是流体求解器。

## 雨粒子与蓝图修复

R02 采用 `/Game/WeatherSystem/Rain/Particles/RainNiagaraSystem`。系统中实际 emitter 的名称是 RainNiagaraEmitter；管理器 SetRainComponentState 的两处分支此前使用 Rain，导致 emitter 启停告警。本轮已将两个 EmitterName 引脚改为实际名称，并编译验证零错误、零警告。

原有速度对齐设置保留；没有把旧屋顶的 GPU 雨丝和飞溅代码换进 R02。单个截图也不能证明雨丝在所有视角都正确缩短、所有粒子都发生真实碰撞。

## 历史屋顶 HLSL 的归属

`Shaders/RainModel.hlsl`、RainPosition、RainOpacity、RainImpactTiming/Position/Opacity、SurfaceGrain、CloudDensityM18 主要服务 M13–M19 屋顶原型。其中 RainModel 共享确定性事件和单个 AABB 雨棚遮挡；Position/Opacity 生成雨丝和面片飞溅；SurfaceGrain 提供程序化底材；CloudDensityM18 定义体积云密度及距离 LOD。

这些文件的存在不证明 R02 正在使用它们。R02 当前有效图和 Custom 代码以本轮 `material-code.json`、组件槽位审计和资产引用为准。

## 贡献与验证边界

UE 提供材质编译、Niagara、Lumen、阴影与资产系统；Downtown_West 和原天气包提供既有场景与材质资源。本工程定制的重点是保留资产外观的接入、统一美术控制、程序化涟漪、世界坐标水痕、限定范围修复和可复核验收工具。代码与工程操作含 Codex 辅助，不能把引擎功能或外部资源当作个人原创。

当前实测证据和剩余限制见 `Verification/R02/REPORT-20261024.md`；原始截图索引为 `Preview/R02/index.html`。
