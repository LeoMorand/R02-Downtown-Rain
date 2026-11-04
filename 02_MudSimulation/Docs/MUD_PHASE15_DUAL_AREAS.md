# 一张地图：原厚度薄层与深泥池

研究工程：`D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy/FluidNinjaLive.uproject`。

打开 `/Game/MudStudy/Professional/Phase15/L_Mud_SurfaceAndPool`。当前已打开，停在可看到两块的总览视角；点击普通Play，出生在左侧薄层外。WASD移动、鼠标转向、空格跳跃，沿中间通道可从薄层进入右侧池子。

- 左侧 `Mud_ThinSurface`：保留原来的平面行走支撑，表面POM/计算法线起伏20cm。这里的20cm是视觉起伏，不是20cm真实浸入深度；角色仍站在Z=0的碰撞平面上。选择组件 `MudControls` 调ThicknessCm、颜色、细节与轮廓；输出分辨率在Actor的OutputResolution中修改，停止Play后调整再运行。
- 右侧 `Mud_DeepPool`：泥面Z=0，池底Z=-80cm，沿坡道可以走到泥面以下，腿部继续推动泥浆。选择 `ArtistControls` 调颜色、泥层深度、黏稠感与显示分辨率。

两块各有20×20m泥面和40×40m平台，中心分别X=-2200/+2200cm，使用约4m长、8m宽通道连接。相邻边墙已打开；坡道仅保留在深池。两块都沿用Phase14的自研分离密度输运、外观材质和计算法线，默认输出2048，模拟/输出/材质动态实例各自独立。薄层沿用原C++骨骼采集，池子沿用腿部泥面交点采集；它们不是同输入的严格算法对照。

新增地图通过复制Phase14，再原生批量复制场地和泥浆Actor搭建。薄层移除深池专用ArtistControls，恢复表面阻挡与骨骼输入；池子保留原深度控制。没有修改旧版地图、共享材质或求解器资产。

## 验证

普通Play已实际走过薄层、通道和池子：薄层角色胶囊中心Z约92.15cm，池底Z约12.15cm，下降约80cm。两段逐帧输入记录均完成、无异常，采样未发现跌落。薄层读回9个骨骼输入，池子有效腿部输入2个。两块ContractValid均为True；各自2048输出与2048法线纹理正确绑定且对象路径不同。

证据位于 `Verification/MudProfessional/phase15-surface-pool/`：`thin-walk.json`、`surface-to-pool.json`、`evidence.json`、`thin-surface.png`、`deep-pool.png`。`overview.png` 为运行时总览，`layout.png` 为带标识的编辑器布局图；编辑器预览不代表实时模拟。`mud_dual_test.py` 仅用于临时逐帧Enhanced Input测试。

两块同时运行的整帧性能未测；本轮没有添加体积流体、动态脚部IK或真实泥浆支撑形变。
