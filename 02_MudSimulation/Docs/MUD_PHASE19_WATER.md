# Phase19：透明积水与水池

研究工程：`D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy/FluidNinjaLive.uproject`。

打开 `/Game/MudStudy/Professional/Phase19/L_Water_PuddleAndPool`，普通Play可走动。左侧是不规则浅积水，右侧50cm水池，沿用双区平台、通道和出入坡道。原Phase18泥浆及历史资产保留。

## 做了什么

复制Phase18场景，另建两套水面父材质和实例，以及独立的 `NS_Water_Interactive`。求解器复制自Phase14分离密度版本，继续提供角色输入、速度密度和计算法线，不使用Phase18的持久脚印显示层。

材质使用 `MSM_SingleLayerWater` 与 `SingleLayerWaterMaterialOutput`，保留Masked轮廓。该模型通过独立水面通道实现透明结果，即使Blend Mode显示Masked，也不是按泥浆的不透明方式绘制。[UE官方单层水说明](https://dev.epicgames.com/documentation/zh-cn/unreal-engine/single-layer-water-shading-model-in-unreal-engine)。

吸收系数默认RGB为0.0025 / 0.0013 / 0.0007，散射系数0.00015 / 0.0003 / 0.00045，单位1/cm。Opacity默认0.08，额外水面镜面系数0.25。使用原动态计算法线与细节流动，将表面起伏从泥浆尺度降到1.5cm、细节强度降到0.12，粗糙度0.035；粗糙度输出直接接回原 `MainRoughness`，因此原美术组件的粗糙度控制仍有效。

移除泥浆的PixelDepthOffset输出，保留现有法线与POM UV链。表面WPO增加1cm高度，左侧底板升至Z=0，使浅水表面与不透明底面分开。左侧碰撞仍在Z=0，角色站立高度不变；右侧保留50cm可走入底面，水面位于Z约1cm。

右侧黏稠感改为0.1、细节流动倍率1.5、行走阻力关闭，作为更流动的水面外观预设。它仍是原二维场的水面呈现，未实现三维水体、飞溅或浮力，也未声称物理水模拟等价。四块旧英文泥浆说明牌仅在新场景中隐藏。

旧桥接的 `set_shading_model` 未识别SingleLayerWater并返回DefaultLit，因此改用原生反射设置材质ShadingModel。已读回 `MSM_SingleLayerWater`、ShadingModelField=1024、BLEND_Masked；没有升级桥接或改C++源码。

## 调节入口

- `MI_Water_Flow` / `MI_Water_Static`：`WaterOpacity` 越小越透，1会遮挡水下部分；`WaterAbsorption` 控制水中光衰减和色偏，数值越大越浑暗；`WaterScattering` 调整散射；`WaterSpecular` 调整镜面强度。
- 左侧 `Mud_ThinSurface → MudControls`：ThicknessCm为波面起伏，Roughness为水面粗糙度，保留区域轮廓和细节流动开关。位置和组件名沿用原场景。
- 右侧 `Mud_DeepPool → ArtistControls`：LayerDepthCm为池深，SurfaceReliefCm为波面起伏，Roughness为水面粗糙度。LightColor影响表面色，水体透射色主要由WaterAbsorption决定。原泥浆Brightness及底纹密度等参数在水面材质中的作用不能等同于泥浆版。

## 验证

证据目录：`Verification/MudProfessional/phase19-water/`。

- 两块水面完成真实Enhanced Input走动；浅水胶囊中心Z约92.15cm，池内约42.2cm。池内有效腿部输入2个。
- 实际高度纹理的64×64局部读回随走动变化。池区平均B约0.932→0.840，浅水约0.932→0.819。记录只证明动态链路在运行，不是同输入算法等价对照。
- 两区各自2048输出与2048计算法线绑定正确；两处32×32读回中，来源高度B与计算法线A最大误差为0。
- `water-preview.png` 是普通PIE视口的实际运行截图，显示透明水面、水下腿部和倒影；`pool-opaque-comparison.png` 为Opacity=1的遮挡检查。期间曾调整粗糙度，因此不作严格逐像素A/B结论。
- `puddle-walk.png` 为浅积水高角度截图，`pool-walk.png` 为池区斜视截图；SceneCapture的一帧效果和普通PIE的时序积累画面存在差异。普通Play图作为主要外观证据。
- 场景和材质已保存，退出测试回到可普通Play状态。本版没有重新录视频，没有重测完整性能或Shipping。

测试脚本 `Tools/MudStudy/water_variant_test.py` 仅用于PIE验证，不参与正常运行。材质图与着色模型读回均在证据目录保存；新资产快照及历史文件检查见integrity.json。
