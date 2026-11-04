# R02 · Downtown Rain

**实时渲染 / 技术美术作品集**  
Unreal Engine 5.8 · Windows · HLSL / Material Editor · Development build  
工程：`/Game/TA_Demos/R02_Downtown_Rain`

> 一句话介绍：把一套现成的天气方案接入一个大型城市场景，让地面、玻璃和街道物件随天气湿润、积水、出现涟漪；不改变原资产外观，一个控制器驱动全场景。涟漪从逐像素程序化逐步优化到烘焙序列帧贴图，开销从约 2.16 ms 降到约 0.34 ms，每一步都经过实测。

## 项目概览

R02 聚焦雨天街景的实时材质表现：让道路、混凝土、砖面、玻璃和一组街道物件随天气状态产生湿润、积水、水痕与涟漪变化。系统保留素材原有底色和材质实例继承，通过天气参数统一驱动不同材质族。

## 素材来源与我的工作

| 来源 | 内容 |
|---|---|
| 第三方：Downtown_West | 城市场景、网格和地面母材质（`M_Ground_Master` 及其天气变体） |
| 第三方：天气包 | 雨 Niagara、天气管理蓝图 `WeatherManagmentBP`、参数集合 `MPC_RoadWeather`，以及只在其演示材质上生效的积水/UV 涟漪/水痕函数 |
| 我的工作 | 材质使用审计与共享实例拆分；湿润函数与渐进积水；世界空间程序化涟漪（替换 UV 涟漪）；物体与玻璃水痕接入；美术控制器 `BP_WeatherArtController`；涟漪性能优化与实测；捕获、基准、DXC、打包等验证工具 |
| 工作方式 | 使用 LLM 辅助编写部分 HLSL、脚本与工具；所有改动由我审查，并用 DXC 编译对比、GPU 实测和数值等价测试验证 |

本项目使用 Unreal Engine 的延迟渲染、材质编译、灯光/反射、透明合成和后处理能力。自定义工作位于材质层，不是自定义引擎渲染 Pass，也不将底层引擎功能或原始资产归为原创。

## 为什么需要"接入"

天气包的效果只在它自己的演示材质上生效。把它放进 Downtown_West，只会出现雨粒子，地面不会湿、不会积水。把天气接入真实场景时遇到的问题：

- **规模**：关卡有 1855 个网格组件、多个母材质家族（地面、土壤、建筑）。最终接入约 345 个地面组件、约 129 个玻璃组件（131 个材质槽）。
- **共享实例**：审计发现同一材质实例被地面和墙面共用，例如 `MI_Bricks_Ground_A_Straight` 也用在建筑墙上，`MI_Concrete_Ground_Tiles_A_WS` 也用在咖啡馆墙上。直接修改会让墙面也积水，因此按实例复制天气版本，只对审核过的地面组件替换材质槽，不修改网格默认材质。
- **UV 涟漪不可用**：原涟漪按模型 UV 滚动，场景中各模型的 UV 尺度不同，涟漪忽大忽小、跨模型断开。改写为按世界厘米生成的程序化涟漪。
- **可控性**：原参数分散在各材质中。新增美术控制器，把手动湿度/雨量/积水、材质类别倍率和四个涟漪倍率集中写入同一个 MPC，同时保留原天气蓝图的自动雨量逻辑。

## 渲染管线与数据流

```text
天气蓝图 / 美术控制器（CPU，每帧）
  └─ 更新 MPC_RoadWeather（雨量、湿度、手动覆盖、材质类别倍率、涟漪倍率）
       ├─ 地面天气母材质（Base Pass，写入 GBuffer）
       │    底材 → 湿润函数 → 积水遮罩 → 世界空间涟漪 → 按雨量缩放 → 颜色/粗糙度/法线
       ├─ 物体天气母材质：世界坐标水痕 UV → 遮罩/法线 → 湿润属性 → UE 表面着色
       ├─ 玻璃材质：透明表面与水痕扰动 → UE 透明合成
       └─ 雨粒子材质/系统：雨量驱动可见雨效
```

地面材质保持不透明表面路径：同一个空间遮罩协调基础湿色、粗糙度、平面水面法线与涟漪扰动。积水的镜面倒影来自 UE 的反射（Lumen/SSR）对低粗糙度表面的计算，材质只负责提供粗糙度和法线。积水由遮罩和参数塑形，不模拟守恒水量。

## Shader / HLSL 设计

地面母材质 `M_Ground_Master_Weather` 中，天气相关的自定义逻辑由三个 Custom 节点和一个材质函数组成。HLSL 源码母本由工具写入 Custom 节点，改源码后须执行构建工具并在 UE 内重编译、保存材质。

### 湿润（`MF_GroundWetness`）

`WetColor = DryColor × lerp(1, 0.75, Wetness)`，`WetRoughness = DryRoughness × lerp(1, 0.6, Wetness)`。用比例而非固定值，保留每种地面原有的颜色与粗糙度差异。

### 渐进积水（Custom_0）

湿度超过起始阈值后才开始积水；水位经 smoothstep 曲线上升，用地面高度图与下降的阈值比较，使水坑从低洼处出现并连成片，边缘有可调的柔和过渡。支持自动与手动两种模式。

### 世界空间程序涟漪（Custom_2）

- 地面按世界厘米切成格子，每格两条独立稀疏的事件通道，避免一格一滴的规整感；两条通道的保留概率之和恒定，调随机度不改变总雨滴数。
- 整数哈希生成每格每次事件的位置、寿命、尺寸和振幅，避免 `frac(sin(x))` 在大世界坐标下精度退化成网格图案。
- 圆环截面为高斯形状，输出其**径向导数**作为法线斜率；用屏幕像素 footprint 加宽远处的环并淡出亚像素细节，避免闪烁。
- 雨量缩放（Custom_1）在无雨时把法线压回水平，积水遮罩把涟漪限制在水坑内。
- 以上是程序化（高画质）档；默认运行的是由同一套公式离线烘焙出的序列帧贴图档，见"性能优化第二步"。

### 物体水痕与玻璃

水痕 UV 从世界位置、法线方向和厘米尺度构造，使竖直立面上的纹理趋向世界向下流动，并对近水平面压制流水效果。这是材质动画，不是有状态液滴模拟。玻璃走单独的透明材质/合成路径。

## 性能优化：涟漪剔除（2026-10-25）

**问题**：涟漪节点每个像素要完整计算 3×3 格 × 2 通道 × 2 个事件 = 36 个候选，包括哈希、开方、指数、除法；而绝大多数候选根本碰不到该像素。打包版实测涟漪约占 1.65 ms GPU。

**改动**：三层提前剔除，并把与候选无关的量（环宽、最远影响距离）提到循环外。

1. **整格**：涟漪中心必在本格内，像素到格子包围盒的距离是到任一中心距离的下界；超过"最大环半径 + 3 倍环宽"时整格跳过，连哈希也省掉。
2. **整通道**：随机度为 0 时第二条通道的保留概率为 0，整条跳过。该值对一帧内所有像素相同，属于 uniform 分支，没有线程发散。
3. **单事件**：事件不存活，或像素离环线超过 3 倍环宽时，跳过后续的开方、指数和法线计算。高斯在 3 倍宽度处约为 1.2e-4。

屏幕空间导数（`ddx`/`ddy`）在所有分支之前计算，因为 GPU 按 2×2 像素组求导，分支内求导可能得到未定义值。

**验证**：

| 项目 | 结果 |
|---|---|
| DXC 静态指令数 | 6492 → 6946（分支代码使指令数**增加**，故不能据此判断快慢，必须实测） |
| GPU A/B（ABAB 交替） | 旧版涟漪开销 2.13 / 2.19 ms → 新版 0.85 / 1.17 ms，两组配对新版均更快，约省 1.1 ms |
| 数值等价 | CPU float32 移植新旧两版，400 组随机美术参数、160 万采样点，法线最大差 5.3e-4，比 8 位法线量化步长（约 0.0079）小约 15 倍 |
| 截图对比 | 同机位 15 种状态新旧并排；涟漪按真实时间动画，不做逐像素判定，目测密度、尺寸、分布一致 |

GPU A/B 条件：Development 独立运行（`-game`，未烘焙），1920×1080 固定机位，RTX 4060 Laptop；每轮 8 段开/关交替，比较每轮"开 − 关"的差值以抵消轮次间漂移；新版首次运行前有一轮丢弃的预热，排除 Shader 编译。"关"状态基线稳定（22.5/22.4、21.8/21.6 ms）。未测打包版和 Shipping，GPU 未锁频。

## 性能优化第二步：烘焙序列帧档（2026-10-26）

**判断**：剔除后约 1.0 ms 仍然只是给地面涟漪这一个细节的开销。在 PC 演示里可以接受，但量产项目、尤其是移动端，这个预算偏贵。行业常见做法是把昂贵的计算移到离线，运行时只采样贴图。

**做法**：

- **离线烘焙**：用与运行时完全相同的涟漪公式，在 CPU 上渲染 32 帧，拼成 8×4 的序列帧贴图（每帧 256 像素，每块 121 cm = 5 个格子，2.6 秒循环）。格子编号和事件编号都取模，保证贴图在空间上无缝平铺、动画在时间上无缝循环。贴图存的是斜率，以 BC5 线性格式导入。
- **运行时**：两层采样打破重复感（第二层缩到 73%、旋转 37°，并把采样到的斜率旋转回世界坐标），每层在相邻两帧之间混合，共 4 次 `SampleGrad`。用未取模的坐标求导数，保证跨拼接处的 mip 选择正确。每层按一半密度烘焙，两层合计与程序化版的雨滴数一致。
- **画质分档**：地面材质加静态开关 `RippleUseBakedFlipbook`，默认烘焙档；程序化版保留为近景或演示用的高画质档。

**验证**：

| 项目 | 结果 |
|---|---|
| DXC 静态指令数 | 程序化 6943 → 烘焙 **204** |
| 无缝检查 | 拼接处像素差（0.54/0.52）小于普通相邻像素差（0.79）；末帧到首帧的跳变（1.36）与普通帧间跳变（1.14）相当 |
| GPU A/B（三组有效配对） | 程序化 0.64 / 1.82 / 0.80 ms → 烘焙 0.34 / 0.65 ms / 低于噪声；三组均为烘焙更便宜，中位数约 0.8 → 0.34 ms |
| 画面（高通滤波测涟漪细节能量） | 烘焙相对程序化：远处 86%、中间 85%、近处 127% |

**一组作废的数据**：第一轮刚切换静态开关就开测，没有预热，程序化版只测到 0.13 ms，明显是新的 Shader 变体还在编译、画面用的是占位材质。这组数据已标为作废，第二轮在两个变体都编译完成后重测。

**代价**：

- 中远处的涟漪弱约 15%：贴图 mip 会把细环平均掉，而程序化版会在远处主动加宽环。可以用远处 mip 偏移，或自定义 mip 链（每级 mip 按程序化的方式加宽环）补偿；评估后认为当前可以接受，暂未处理。
- "密度""随机度""大小"三个滑杆在烘焙档下不再实时生效，只有强度和速度可调；改这些参数要重跑烘焙脚本（约 15 秒）。这正是保留程序化档的理由。

## 雨势匹配：雨跟随相机与大雨涟漪（2026-10-26）

**问题一：雨只在一小片区域下。** 天气包的雨粒子发射范围是固定的 20 m × 20 m 平面，钉在场景中的一个点上，R02 的街道远大于它。直接扩大到覆盖整条街，粒子数会增加几十倍，而且大部分落在镜头外。

**做法**：游戏里的常见做法是让雨跟着相机走。新增 C++ 组件 `UStormfallFollowViewComponent`（[源码](../Source/Stormfall/StormfallFollowViewComponent.cpp)），每帧把雨的发射位置移到相机正上方（游戏里跟随玩家相机，编辑器里跟随视口相机，只跟随水平位置）。同时为 R02 复制了一份雨粒子系统，范围扩大到 50 m × 50 m，生成率按面积乘以 6.25，保持密度不变；天气包原资产不改动。

**问题二：涟漪像毛毛雨，和雨势对不上。** 换算下来，原参数只有约每平方米每秒 16 个落点，是毛毛雨的量级。

**做法**：这正是烘焙方案的优势所在：离线计算不计成本。按"大雨"预设重新烘焙：格子从 24 cm 缩到 12 cm、事件频率提高、每个像素考虑过去 4 个事件、圆环允许重叠到 0.9 格，约每平方米每秒 178 个落点。**运行时开销不变**，仍是 4 次贴图采样。烘焙脚本保留了原"毛毛雨"预设，可以随时切回。

## 交互：湿脚印与落脚涟漪（2026-10-30）

角色走过时在地面留下湿脚印，脚印约 4 秒后从边缘向中心变干，约 20 秒后消失；每一步同时产生一圈扩散的涟漪。

- **落脚检测**：C++ Actor `AStormfallWetFootprints`（[源码](../Source/Stormfall/StormfallWetFootprints.cpp)）每帧读取角色左右脚骨骼，向下射线求地面高度；脚低于 18 cm 视为落地，高于 26 cm 视为抬起，两个阈值之间的间隔保证一步只盖一次章。阈值来自实测：GASP 角色落地时脚踝离地 9–12 cm，迈步时抬到 31–61 cm。
- **脚印**：用贴花（decal）实现，不修改地面材质，对所有地面类型都有效。[footprint_decal.hlsl](../Tools/WetFootprints/footprint_decal.hlsl) 用前掌、足弓、脚跟三块构成鞋底距离场（足弓偏外侧、水量较淡），叠加横向鞋底纹路（纹槽少水、纹块多水）；右脚把贴花沿横向镜像，左右脚不同。变干时阈值随贴花寿命上升，所以最薄的边缘先干、最厚的中心最后干，比整体淡出更接近真实。
- **两处校正（2026-10-31）**：射线起点是脚踝，位于脚跟上方，所以脚印向前偏移 0.3 倍鞋长到鞋底中心；俯视截图发现纹路方向反了，确认贴花 UV 的 U 沿脚长、V 沿脚宽，在 HLSL 中交换坐标。
- **适用条件**：湿脚印是"变暗 + 变光滑"，在全湿、积水的地面上几乎没有对比；在半干地面（湿度约 0.3、无积水）上最清楚，演示按此设置。
- **落脚涟漪**：[footstep_ripple_decal.hlsl](../Tools/WetFootprints/footstep_ripple_decal.hlsl) 是只写法线的贴花，原理与雨滴涟漪相同（高斯环的径向导数作为斜率），两圈环先快后慢地扩散。
- **开销**：同时存活的脚印约 50 个，上限 120，超出时最早的先移除；涟漪贴花寿命 0.9 秒。

**一个踩过的坑**：贴花用 `SpawnDecalAtLocation` 生成时，它的所有者是 WorldSettings Actor。如果淡出时设置"销毁所有者"，会把 WorldSettings 一起销毁。所以改用贴花自身的寿命来销毁它。

## 控制器：昼夜切换与雨丝参数（2026-10-31）

- **昼夜**：控制器新增 `Night` 开关，调用 C++ `UStormfallLightingLibrary::SetNightLighting`（[源码](../Source/Stormfall/StormfallLightingLibrary.cpp)）切换 Downtown_West 的白天/夜晚灯光子关卡。编辑器里改编辑器可见性、不弄脏关卡；Play 里改流送可见性。为此把白天子关卡从"常驻加载"改为动态流送。踩过的坑：Play 时子关卡包名带 `UEDPIE_0_` 前缀，需要先去掉再比较。
- **雨丝**：雨粒子新增 `RainStreakSize`、`RainBrightness` 用户参数，控制器的 `RainDensity` 乘以雨量写入生成倍率。排查"看不到雨"时用粒子缓存读数定位到三个原因：天气包把生成倍率重置为 1（同屏只有 9 个雨滴）、寿命 1.5 秒不够从 15 m 落到地面、编辑器后台降频。修正后同屏约 5600 个雨滴，平均下落速度约 33 m/s。
- **展示工具**：[buildup_sequence.py](../Tools/R02/buildup_sequence.py) 按"原始 → 雾 → 丁达尔 → 雨 → 湿润 → 积水"逐层叠加，用于对比图和录屏；[weather_timeline.py](../Tools/R02/weather_timeline.py) 驱动干到湿的渐变，可放慢倍数。

## 工程文件

| 模块 | 文件 | 行数 |
|---|---|---|
| 雨跟随相机（C++） | `Source/Stormfall/StormfallFollowViewComponent.h/.cpp` | 143 |
| 湿脚印（C++） | `Source/Stormfall/StormfallWetFootprints.h/.cpp` | 188 |
| 昼夜切换（C++） | `Source/Stormfall/StormfallLightingLibrary.h/.cpp` | 76 |
| 涟漪烘焙运行时 HLSL | `Tools/R02/ripple_flipbook.hlsl` | 47 |
| 程序化涟漪 HLSL（v1 / v2） | `Tools/R02/ripple_candidate_v1.hlsl` / `_v2.hlsl` | 63 / 90 |
| 脚印 / 落脚涟漪 HLSL | `Tools/WetFootprints/footprint_decal.hlsl` / `footstep_ripple_decal.hlsl` | 32 / 26 |
| 烘焙与安装（Python） | `bake_ripple_flipbook.py`、`install_ripple_flipbook.py`、`install_wet_footprints.py` | 132 / 149 / 135 |
| 测量与验收（Python） | `ab_ripple.py`（ABAB GPU 对比）、`test_offline.py`（数值回归）、`ue_acceptance.py` | 198 / 177 / 409 |
| 展示工具（Python） | `buildup_sequence.py`、`weather_timeline.py`、`lighting_look.py` | 114 / 103 / 28 |

HLSL 都写在材质的 Custom 节点里，源文件和材质中的代码由安装脚本同步；运行时没有自定义渲染 Pass。

## 性能预算

| 功能 | 运行时成本 | 数据来源 |
|---|---|---|
| 地面涟漪（烘焙档） | 约 0.34 ms GPU（程序化档约 0.8 ms，优化前约 2.16 ms） | ABAB 实测，条件见上文 |
| 涟漪静态指令数 | 6943 → 204 | DXC |
| 雨粒子 | 同屏约 5600 个，GPU 未单独测 | Niagara 缓存读数 |
| 湿脚印 | 贴花上限 120 个（正常行走约 50 个存活），每个寿命 20 秒；GPU 未单独测 | C++ 参数、Play 计数 |
| 落脚涟漪 | 每步 1 个贴花，寿命 0.9 秒；GPU 未单独测 | C++ 参数 |
| 昼夜切换 | 只切换子关卡可见性，无每帧开销 | 代码 |

## 验证与结果

- **场景状态**：45 张 1920×1080 捕获汇总了 8 个机位的干燥/积水/关闭涟漪状态、沥青 15 组端点，以及 3 张同源展示机位街景图。截图索引见 [R02 Preview](../Preview/R02/index.html)。
- **材质编译**：6 个天气母材质在 UE 中重新编译，`errors=[]`；涟漪新版安装后 `M_Ground_Master_Weather` 编译无错误。
- **离线回归**：14 项回归通过；DXC `ps_6_0` 严格编译（`-WX`）通过。
- **自动天气参数**：180 秒读回循环通过初始干燥、变湿、雨量上升、停雨、最终干燥和全程自动模式检查。此数据早于 emitter 修复，不等同于完整打包雨粒子连续录像。
- **Cook/打包**：指定 R02 的 Windows Development Build 完成，`BUILD SUCCESSFUL`；独立启动地图、截图和正常退出检查通过。
- **GPU 采样（优化前，打包版）**：1920×1080 固定机位，8 段交替开/关涟漪，4 组配对差中位数 1.647 ms。此为优化前的涟漪边际成本；优化后的数据见上一节。

## 已知边界与下一步

- 玻璃水痕在静帧中偏弱；不同朝向、曲面和镜像条件尚未完整验收。
- 物件天气材质只覆盖限定白名单（11 个组件），不代表全街区建筑/道具已接入。
- 尚无完整自动天气的连续视听演示；长条反射异常未稳定复现，不能标记已修复。
- 涟漪优化的收益为 Development 未烘焙版数据，打包版与 Shipping 未复测；GPU 未锁频，单轮波动较大。
- 烘焙档中远处涟漪比程序化档弱约 15%，部分美术滑杆在烘焙档下失效（见上文"代价"）。
- 雨只覆盖相机周围 50 m，看向更远处时远处没有雨丝；远景雨幕尚未制作。
- 湿脚印已在 Play 中验证会生成（走 14 m 生成 9 个），鞋底形状经俯视截图确认；在全湿积水地面上看不清，落脚涟漪的观感尚未在视频中检查。
- 雨粒子、湿脚印贴花的 GPU 开销尚未单独测量。
- 项目自动化报告为 48 成功、12 失败，失败对应两个旧人物资产的既有校验项；保留原始结果，不宣称全工程全绿。
- 下一步：录制 30–60 秒演示（干燥 → 下雨 → 渐湿 → 积水 → 涟漪，以及控制器调参）；补"天气包演示 / 直接放入场景 / 接入后"三联对比图和正常曝光的首图。

## 面试讲解建议（约 90 秒）

1. **问题**：现成天气方案只在演示材质上生效，如何把它接入一个有 1855 个组件、材质实例互相共用的城市场景，同时不破坏原外观？
2. **方案**：审计材质使用，拆分共享实例只改地面；湿润、积水、涟漪分层叠加在原材质输出前；所有参数集中到一个 MPC 和一个控制器。
3. **技术取舍**：UV 涟漪跨模型尺度不一，改为世界空间程序化；采用 UE 原生材质与延迟渲染集成，而不是为一个场景维护自定义渲染 Pass。
4. **性能**：先做三层剔除，静态指令数反而增加，所以用 ABAB 交替实测，约 2.16 → 1.0 ms，并用数值测试证明画面等价。再判断 1 ms 对量产仍然偏贵，把涟漪烘焙成无缝序列帧贴图，运行时只采样 4 次，约降到 0.34 ms；程序化版保留为高画质档。主动说明烘焙的代价：中远处弱约 15%、部分滑杆失效。
5. **诚实边界**：说明哪些来自第三方、哪些借助了 LLM、哪些仍未完成，以及每项数据的测量条件。

## 工程证据索引

- 涟漪优化与 Shader 整理报告：[ShaderCleanup REPORT](../Verification/ShaderCleanup/REPORT.md)
- 新旧涟漪源码：[v1](../Tools/R02/ripple_candidate_v1.hlsl) / [v2](../Tools/R02/ripple_candidate_v2.hlsl)
- GPU A/B 记录：`Verification/R02/20261025T055634056Z-ripple-ab.json`（含 A1/B1/A2/B2 四轮运行目录）
- 新旧截图并排：`Verification/ShaderCleanup/ripple_capture/`
- A/B 编排脚本：[Tools/R02/ab_ripple.py](../Tools/R02/ab_ripple.py)
- 烘焙档：[烘焙脚本](../Tools/R02/bake_ripple_flipbook.py) / [运行时 HLSL](../Tools/R02/ripple_flipbook.hlsl) / [安装脚本](../Tools/R02/install_ripple_flipbook.py) / [烘焙贴图](../Tools/R02/RippleBake/T_RippleFlipbook.png)
- 程序化与烘焙并排截图：`Verification/ShaderCleanup/ripple_tier_capture/`
- 程序化与烘焙 GPU A/B 记录：`Verification/R02/20261026T054921071Z-ripple-tier-ab.json`、`Verification/R02/20261026T062406444Z-ripple-tier-ab-round2.json`
- 接入计划与共享实例审计：[WeatherReuse PLAN](../Verification/WeatherReuse/PLAN.md)
- 最新范围与风险记录：[R02 验收报告](../Verification/R02/REPORT-20261024.md)
- HLSL 类别和运行时边界：[HLSL 总览](../HLSL_OVERVIEW.md)
- R02 自动化工具说明：[Tools/R02 README](../Tools/R02/README.md)

---

# R02 · Downtown Rain — Interview Summary (EN)

**Real-time Rendering / Technical Art · Unreal Engine 5.8**

Integrated a third-party weather package, whose wet, puddle and ripple effects only worked on its own demo materials, into a large third-party city scene (1855 mesh components, shared material instances across ground and walls). I audited material usage and split shared instances so only ground surfaces respond; layered wetness, progressive puddles and world-space procedural ripples over the original materials without changing their dry look; and centralised all controls in one MPC driven by an artist controller. About 345 ground and 129 glass components are covered.

The ripple shader was optimised in two steps. First, three levels of early culling: static DXIL instructions increased (6492 → 6946), so I measured it, and an ABAB GPU comparison in an uncooked Development build showed ripple cost falling from about 2.16 ms to about 1.0 ms; a CPU float32 port of both versions over 1.6 million samples showed a maximum normal difference of 5.3e-4. Second, judging 1 ms still too expensive for production, I baked the same procedural ripple offline into a seamlessly tiling, looping 32-frame flipbook and sample it four times at runtime (two rotated layers, frame blending, SampleGrad for correct mips). Static instructions dropped from 6943 to 204 and measured cost fell to about 0.34 ms. The procedural version stays available behind a static switch as a high-quality tier; the baked tier is about 15% weaker at mid and far distance and fixes the density, randomness and size sliders at bake time. Parts of the code were written with LLM assistance and verified with DXC comparison, GPU measurement and numerical tests. The project uses Unreal's rendering pipeline; it does not implement a custom renderer or RDG pass.
