# Manny 衬衫干湿材质

2026-10-24 更新：已增加天气驱动、遮雨、入水、局部湿度历史和衣摆物理代理。当前使用说明见 [PRODUCTION.md](PRODUCTION.md)，下文保留最初材质适配说明。

已基于 `/Game/Stormfall/Weather/Cloth/Reference/M_Cloth_Reference_NodesOnly` 完成衬衫适配。原参考材质和共享函数保持原样，衬衫使用独立副本。两份衬衫网格的默认材质槽已接入。

## 直接查看

打开 `/Game/Stormfall/ShirtTrial/Wetness/L_ShirtWetness`。

从左到右是干燥、半湿、湿透、自动循环。选择任一人物，在 Details → **Shirt Wetness** 调整：

| 属性 | 用途 |
| --- | --- |
| Wetness | 0 干燥，0.5 中间状态，1 湿透；修改后通过 Construction Script 更新外观 |
| AutoCycle | 勾选后在 Play / Simulate 中循环干湿；编辑器静止状态不自动推进 |
| CycleSeconds | 循环总时长，默认 40 秒；运算最低按 1 秒处理 |

手动调试时先取消 AutoCycle，再调 Wetness。最右人物默认启用循环：0–5 秒干燥、5–15 秒变湿、15–25 秒湿透、25–35 秒变干、35–40 秒干燥，然后重复。关卡自带概览相机，Play 时自动使用。

## 使用到角色上

- 直接将 `/Game/Stormfall/ShirtTrial/Wetness/BP_ShirtWetness` 拖入关卡，即得到带衬衫的 Manny 和完整湿润控制。
- 运行时调用 **SetShirtWetness(Value)**，会关闭自动演示、将 Value 限制到 0–1，并同步更新所有布料动态材质。调用 **ApplyWetness** 则应用当前 Wetness。
- 现有角色可使用已适配的 `SK_Manny_MotionStudio_Shirt`；保留兼容的 Manny 动画蓝图。将 `Set Scalar Parameter Value on Materials` 的 Target 接到实际穿衣网格，Parameter Name 设为 `Wetness`，即可接入自己的天气逻辑。
- 独立衣服 `SK_MotionStudio_Shirt_Manny` 的七个槽也已适配。单独作为角色子组件时，还需由身体组件带动骨骼姿态；本次没有替换原游戏角色的骨架或动画。

## 材质和贴图

母材质：`/Game/Stormfall/ShirtTrial/Wetness/Materials/M_Shirt_ReferenceWet`。

五个 `MI_ShirtWet_*` 分别对应 Front、Back、Sleeve_Left、Sleeve_Right、Cuffs_Boundry。每个实例均有本区域的 Garment Albedo、Garment Normal、Garment Glossiness、Garment AO 和 Garment Specular。细缝线使用黑色袖口布料，塑料纽扣保留原材质和外观，并保存引擎自动补齐的骨骼网格使用标记。

底色使用 sRGB；法线和数据贴图使用线性采样。原衬衫法线已经翻绿适配 UE，继续使用 BC5/Normalmap，不重复翻转。Glossiness 反转后作为干态粗糙度，保留原贴图变化。实际衬衫实例的 Wet Roughness 为 **0.46**、Wet Albedo Multiplier 为 **0.48**；母材质保留参考起点 0.38 / 0.55，实例覆盖为更克制的棉布湿态。

原大褶皱、细褶皱、织纹、绒毛函数保留。额外大褶皱和细褶皱分别使用 0.96 / 0.98 Flatness，衬衫自己的烘焙法线作为主体，通过角度修正法线混合叠加细节。织纹和纤维法线强度为 0.12 / 0.06。湿后绒毛从干态量逐步降至 20%。

参考图原先的两路底色相加会让衬衫贴图重复变亮；适配版已消除重复相加，Tint 默认白色。AO 和有界的非金属 Specular 也已接到输出。所有直接及递归函数纹理采样均非空。

## 验证与范围

UE 实拍对比：`Preview/ShirtWetness/comparison.png`；最终正面为 `final_dry.png`、`final_halfwet.png`、`final_soaked.png`；背面为 `accepted_back_dry.png`、`accepted_back_soaked.png`。同一人物、相机、光照下调整湿度，截图没有调色。

`Verification/ShirtWetness/REPORT.md` 记录编译、运行、材质槽同步、循环阶段、保存重载及原资源哈希核对。

本次完成的是材质外观、手动湿度输入和演示循环。尚未连接实际雨量、遮雨检测、入水重叠、持久湿度历史，也没有增加衣料碰撞或湿后贴身变形。半湿分布仍沿用参考材质的 UV 渐变逻辑，UV 接缝处可能不连续。

## 维护

备份：`Saved/Revisions/ShirtWetness_20261022_144532`，包含修改前两份衬衫网格、原材质和参考资源。

不要在已完成材质上重跑 `build_materials.py`。它是受保护的一次性构建记录，保留原节点并附加衬衫输入。当前桥接器的批量接图工具返回零节点，因此使用编辑器 Python 完成材质构建；Blueprint 使用原生图工具创建。Cloth 的 Fuzz 输入在 UE 反射存储中名为 `ClearCoat`，已经用原生属性工具连接到 `Wet cloth fuzz amount`；材质 Shading Model 始终是 Cloth。

`audit_assets.py` 为只读资产审计；`verify_runtime.py` 必须在此演示关卡 PIE 时运行，会临时修改最右演示人物并测试其已编译蓝图。停止 PIE 后恢复关卡原状态。
