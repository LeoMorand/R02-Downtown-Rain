# 泥浆求职案例：当前入口

本轮以泥浆为协作目标，R02由用户独立推进。

## 打开

新增透明积水版本：`/Game/MudStudy/Professional/Phase19/L_Water_PuddleAndPool`。原动态模拟改为水面呈现，左侧为约1cm浅积水，右侧50cm水池；保留角色交互、计算法线和细节流动。使用UE单层水着色，能透出池底和水下腿部。透明度在 `MI_Water_Flow` / `MI_Water_Static` 的 `WaterOpacity`，水色深浅在 `WaterAbsorption`，起伏和粗糙度仍由原组件调节。泥浆旧版保留。见 [Phase19](MUD_PHASE19_WATER.md)。

最新交互痕迹加强场景：`/Game/MudStudy/Professional/Phase18/L_Mud_VisibleTrails`。从用户当前双区场景另存，保留其50cm池深、12cm起伏及约1的黏稠感。新增独立保留的局部脚步/拖痕，联动凹陷和颜色变暗，逐渐消退。选择泥浆的 `Simulation`，搜索 `TrailStrength` / `TrailHalfLifeSeconds` / `TrailImprintGain` 调整；颜色对比在新材质实例 `TrailColorContrast` 中。说明见 [Phase18](MUD_PHASE18_TRACES.md)。

最新全功能实时视频：`Deliverables/MudFullFeatures_20261030/Mud_FullFeatures_Runtime_1080p30.mp4`。4分09秒1080p30，覆盖双区交互与全部外观调节、预设和显示质量；无后期标题、字幕或图卡，保留运行时中文参数和原生 FPS / CPU / GPU / 显存等统计。以真实时间录制，性能数字适用于带录制负载的完整研究编辑器 PIE。说明见 [Phase17](MUD_PHASE17_REALTIME.md)。

上一版离线短片：`Deliverables/MudSurfacePool_20261030/`。70秒1080p30，含中文字幕和技术链路，无配音；不证明实时FPS。说明见 [Phase16](MUD_PHASE16_VIDEO.md)。旧73秒球体版保留作历史版本。

最新双区体验地图：`/Game/MudStudy/Professional/Phase15/L_Mud_SurfaceAndPool`。左侧原厚度薄层（20cm表面起伏、平面行走），右侧80cm深池，中间通道相连，普通Play从薄层出生。两块沿用Phase14修正版且各自模拟；已实测连续走过薄层、通道与池子。使用见 [Phase15](MUD_PHASE15_DUAL_AREAS.md)。

最新自研外观修正版：`/Game/MudStudy/Professional/Phase14/L_Mud_VisualMatch`。修复黏稠感同时衰减密度导致泥面变平的问题，速度与密度反馈已拆开；校准颜色对比、亮度和粗糙度，保留自研Niagara、HLSL材质与计算法线。80cm深槽普通Play可走入；两端黏稠感、GPU输入和角色走动已验证。说明与范围见 [Phase14](MUD_PHASE14_VISUAL_MATCH.md)。

最新原版深泥对比地图：`/Game/MudStudy/Professional/Phase13/L_Mud_OriginalDeep`。原版 NinjaLive 蓝图、Niagara 和材质直接套入同一80cm深槽，专用角色开启网格重叠，普通Play可走入。已确认原版收到17个骨骼位置；这是完整链路体验对比，非单独模拟器或同状态性能对照。见 [Phase13](MUD_PHASE13_ORIGINAL_DEEP.md)。

研究工程：`D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy/FluidNinjaLive.uproject`。

最新可调深泥地图：`/Game/MudStudy/Professional/Phase12/L_Mud_ArtistDeep`。选择 `Integrated_Mud_GlobalNormal` 的 **ArtistControls**，可调颜色、黏稠感、泥层深度、表面起伏及 512/1024/2048 显示分辨率。默认80cm深，普通Play后沿坡道走入，泥面可漫过大腿；提供5/50/90cm预设。实际进出、速度恢复、腿部交点输入、颜色、分辨率绑定与保存重载已验证。使用与范围见 [Phase12](MUD_PHASE12_ARTIST.md)。

原可游玩地图：`/Game/MudStudy/Professional/Phase11/L_Mud_Playground`。40米平台、中央泥浆区和UE5 Manny，点击Play后用WASD/鼠标/空格游玩。角色骨骼输入接入泥浆；实际移动、跳跃与完整重启检查通过。说明见 [Phase11](MUD_PHASE11_PLAYGROUND.md)。碰撞仍为平面，未做动态脚部IK。

独立可调地图：`/Game/MudStudy/Professional/Phase10/L_Mud_Adjustable`。选择 `Integrated_Mud_GlobalNormal` 的 `MudControls`，可调厚度、双颜色、表面细节/流动和区域轮廓。用模拟模式观察动态，60秒轨迹已配置循环。使用与限制见 [Phase10](MUD_PHASE10_ADJUSTABLE.md)。

冻结投递地图：`/Game/MudStudy/Professional/Phase09/L_Mud_Portfolio`。进入运行会自动播放60秒专用轨迹，使用统一参数组件和边界平滑交接。输入是球体夹具。

**投递入口：`Deliverables/MudPortfolio_20261029/`。** Mud_Portfolio_73s_Submit.mp4为73秒1080p30主片，Full_Replay_64s_1080p30.mp4为连续回放，另有技术说明、面试提纲和轻量ZIP。视频均为离线采集。

历史短预览：`Verification/MudProfessional/phase07-contact/20261029T143843152519Z/contact_720p30_offline.mp4`，24秒、1280×720、30帧/秒，包含日光、三个机位与接触修正。采用固定时间步离线录制，不能作为实时30FPS证明。冻结开关对照为 `phase07-contact/moving_contact_off.png` / `moving_contact_on.png`，另有低角度 `grazing_contact_off.png` / `grazing_contact_on.png`。

历史逐帧轨迹：`Verification/MudProfessional/phase06-capture/20261029T113604578794Z/replay_720p30_offline.mp4`，64秒、720p30，同样为离线录制。旧Phase05的3Hz视频保留作历史诊断，已不是最新观看入口。

## 已有证据

- [Phase01](MUD_PHASE01_ALIGNMENT.md)：POM与计算法线采样点对齐。
- [Phase02](MUD_PHASE02_HEIGHT.md)：当前平面的大形变高度统一到20cm。
- [Phase03](MUD_PHASE03_DETAIL.md)：恢复两层平铺细节，避免大坡度重复叠加。
- [Phase04](MUD_PHASE04_FLOW.md)：带符号速度、双相流动与可控输入验证。
- [Phase05](MUD_PHASE05_REPLAY.md)：自动播放轨迹、真实输入与局部状态检查；采集品质未达成片标准。
- [Phase06](MUD_PHASE06_CAPTURE.md)：720p30离线视频、日光与三个机位；接触高度与实时性能仍待完善。
- [Phase07](MUD_PHASE07_CONTACT.md)：统一POM深度参考面、GPU球体视觉接触、36项算术用例与同状态双机位对照；实时成本和物理接触未验收。
- [Phase08](MUD_PHASE08_CONTROL.md)：统一参数组件与真实静态/流动切换；8轮独立D3D12 SM6动态对照通过。当前协议下流动增量约0.09–0.10ms，接触增量未超出重复波动；仍非实时FPS或新版Shipping验收。

最近验证命令：`python Tools/MudStudy/verify_replay_capture.py Verification/MudProfessional/phase07-contact/20261029T143843152519Z --scope short-preview`，以及 `python Tools/MudStudy/verify_sphere_contact.py`。它们检查已有记录，不重跑UE。

最新性能复核：`python Tools/MudStudy/summarize_contact_profile.py Verification/MudProfessional/phase08-control/20261029T164518117Z`。核对8轮退出码、实际RHI/分辨率/相机、轨迹和GPU记录；只重算已有数据。

- [Phase09](MUD_PHASE09_DELIVERY.md)：完整64秒回放、219次局部GPU检查和边界逐帧预测通过；73秒投递主片与说明完成。
- [Phase10](MUD_PHASE10_ADJUSTABLE.md)：集中外观控制、四种可见轮廓、两套预设；6组PIE读回与保存重载通过。轮廓裁切不改变2000cm模拟域，流速控制不代表黏度，旧性能记录不覆盖本版。
- [Phase11](MUD_PHASE11_PLAYGROUND.md)：大平台、Manny及普通Play；15项记录检查通过，实际走动约10米并完成跳跃落地和完整重启验证，155个历史文件未变。
- [Phase12](MUD_PHASE12_ARTIST.md)：美术中文参数、可走入的深泥凹槽、腿部泥面交点输入、行走阻力与三档显示分辨率。黏稠感是艺术联动，非物理黏度；深泥仍为二维场配合较低碰撞底面。

## 后续扩展

1. 完整回放和边界交接已补齐；继续扩展更多曲面与交互输入，尖锐曲面的有限采样误差仍在。
2. 统一参数已落地，但只支持当前水平2000cm方形场与均匀缩放球体。后续验证目标平台真实时间步与新版Shipping，不能把本轮固定步进GPU对照当作实时帧率证明。
3. 按投递目标进一步迭代艺术表现。当前已提供73秒主片、技术说明和面试讲述，不等于最高档次或完整生产验收。

历史七项运行回归、最小宿主打包和旧性能基线仍见 `MUD_ACCEPTANCE_20261027.md`；这些通过项不自动覆盖最新流动材质与完整演示包。完整动态等价仍未验证。
