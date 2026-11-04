# Phase11：可行走泥浆平台

日期：2026-10-30。实际工程为 `D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy/FluidNinjaLive.uproject`。

## 打开和游玩

地图：`/Game/MudStudy/Professional/Phase11/L_Mud_Playground`。研究编辑器当前已打开此地图。

点击工具栏 **Play**，点击游戏视口捕获输入：

- **WASD**：移动。
- **鼠标**：转动第三人称视角。
- **空格**：跳跃。
- **C**：沿用原角色的行走速度切换。
- **Shift+F1**：释放鼠标。
- **Esc**：结束运行。

角色从西侧步道出生，正前方即为泥浆。场景使用40×40米的平台，中间为20×20米的泥浆区域，包含外围步道、边缘挡条、青色标线和操作提示。中央底板低于泥浆，避免遮挡POM深度；角色碰撞仍为顶部平面。

## 调节泥浆

停止Play后，选择 `Integrated_Mud_GlobalNormal → MudControls`，继续调节Phase10已有的厚度、深浅颜色、细节密度/强度、粗糙度和流动速度，保存关卡即可。

本场景默认 `RegionShape=FullPlane`，让泥浆填满中央方形试验区。修改成椭圆或不规则轮廓会露出下方底板，但碰撞平面不会跟着轮廓裁切。要独立观察形状调节，可打开Phase10的 `L_Mud_Adjustable`。

## 实现

- 新地图由Phase10复制；删除了新地图内的自动球体回放控制器和会抢占玩家视角的旧相机。
- `BP_Mud_Manny` 复制自研究工程已有的 `/Game/FluidNinjaLive/Meshes/ThirdPersonCharacter`，使用 `SKM_Manny_Simple`、`ABP_Unarmed` 和现有Enhanced Input映射。复用了原有角色和动画，没有重新制作Manny模型或行走动画。
- 新角色默认速度400 cm/s、行走速度180 cm/s、加速度1200 cm/s²、相机臂长500 cm。删除了副本里的调试冲刺、布娃娃等键盘入口，空格保留标准跳跃输入；原蓝图未修改。
- `BP_Mud_GameMode` 负责自动生成并接管Manny，地图使用专用PlayerStart；无需手动放置或Possess角色。
- 泥浆启用 `TrackPlayer` 和 `TrackPhysicsBones`，沿用原运行模块把角色骨骼位置写入Niagara输入数组；不再使用旧球体BrushActors。当前会跟踪所有满足高度过滤的物理骨骼，不是仅两脚输入。
- 旧球体预览隐藏，球体视觉接触关闭。Phase10的外观控制仍统一驱动表面高度与法线。
- 场景新增3个简洁平台材质，全部只赋给放置组件，没有修改Engine基础Cube或厂商网格的默认材质。

新增的6个UE资产位于研究工程 `Content/MudStudy/Professional/Phase11/`：地图、角色蓝图、GameMode蓝图及3个材质。本轮场景逻辑主要保存在蓝图和关卡中，没有新增运行C++类。

## 验证

记录：`Verification/MudProfessional/phase11-playground/`。

- 实际通过Enhanced Input动作驱动角色，记录70组运行状态：前进1021 cm，最高速度400 cm/s；跳跃后落地，视角转动正常，脚骨相对角色根节点有动画运动。
- Niagara输入读回含9个有效骨骼点，其中2个位于距泥浆参考面20 cm以内；输出区域采样有变化。前后采样时刻不同，不能单靠这组差值声称严格隔离了玩家输入的因果贡献。
- 完整退出并重开研究编辑器，从磁盘载入地图后，普通Play仍正确生成Manny并使用角色相机，泥浆参数契约有效；冷启动未发现Blueprint Runtime Error、Accessed None或材质编译失败。
- `validation.json` 的15项记录检查通过，`integrity.json` 检查的155个历史文件全部未变。新资产有SHA256及本地快照。
- `player-walk.png` 为实际角色机位截图；`platform-play.png` 为运行中的平台全景。原生截图IEND后的分配尾部已移除，像素压缩数据未变。

自动输入测试使用临时 `Tools/MudStudy/mud_playground_test.py`：旧桥接插件缺少持续输入接口，因此通过Python逐帧注入实际Enhanced Input动作。脚本有研究工程/地图检查，完成后注销回调并清零输入；正常游玩无需运行此脚本。普通Play通过原生LevelEditorSubsystem调用验证。没有升级或重编译桥接插件。

重新检查已有记录（不会启动UE）：

```powershell
python Tools/MudStudy/verify_mud_playground.py
```

当前是角色交互展示：泥浆凹陷仍为POM/法线视觉重建，碰撞保持平面，未实现贴合动态高度场的脚部IK、脚陷深度、真实泥浆阻力或严格鞋底印痕。未重新测量本地图实时性能或打包本版，也不代表求解器完整动态等价。
