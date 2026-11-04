# Phase07：球体与POM泥面的视觉接触（2026-10-29）

当前结果：新关卡中，球体的可见网格根据同一实时高度场调整Z位置。同一冻结状态下的两个机位均能看到原有间隙收窄。24秒720p30离线预览、36项GPU算术用例通过；这不是物理碰撞实现或实时性能验收。

## 观看和打开

研究工程：`D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy/FluidNinjaLive.uproject`。

地图：`/Game/MudStudy/Professional/Phase07/L_Mud_Contact`。运行后自动播放新序列 `LS_Mud_Contact`，沿用既有60秒输入轨迹。

最新视频：`Verification/MudProfessional/phase07-contact/20261029T143843152519Z/contact_720p30_offline.mp4`，24秒、1280×720、H.264、720帧。已完整解码检查，并用ffprobe核对帧数、帧率与时长。画面标明离线采集；录制包括同步GPU读回、场景采集、人工冻结对照，耗时约276秒，不能用来估计正常运行帧率。

冻结对照：同目录上一级的 `moving_contact_off.png` / `moving_contact_on.png`，以及 `grazing_contact_off.png` / `grazing_contact_on.png`。四张图均为模拟时间12.633333992秒，两组分别保持相机一致，只切换球体材质的ContactEnabled。原始PNG保留。`contact_off.png` / `contact_on.png` 是早期平整初始状态诊断，不能用于证明改善。

## 问题与修正

之前输入球的中心固定Z=20cm，半径20cm，球底始终在几何平面Z=0。POM仅改变地面的UV和像素深度，泥面凹下后，球体仍停在原高度，所以近景会出现间隙。

另一个问题是原POM Custom26的参考面：UV使用ReferencePlane偏移，PDO的距离仍以高度1为起点。原Phase02文档把两者一起解释为 `20*(h-0.9)`，现已更正；历史资产没有改动。Phase07的新表面实例将实际参数ParallaxPlane设为1，在当前水平、方形、2000cm世界映射下统一为：

`surfaceZ = SimCenter.z + 20 * (height - 1)`。

可见球体需要的支撑高度来自球面下半部与高度场的接触关系：

`centerZ = max(heightWorld(offsetXY) + sqrt(radius² - dot(offsetXY, offsetXY)))`，其中offsetXY位于半径圆盘内。

只读取球心下方高度，在斜坡上容易穿插。因此着色器增加法线指向的接触候选点，以及4个半径、每圈16个方向的圆盘采样。中心1次、法线候选最多1次、圆盘最多64次，每顶点最多66次Level0纹理读取。法线候选在理想平面上给出解析接触点；曲面仍是有限采样近似。

## 数据与资产链

1. 原输入球Integrated_Brush继续沿序列运动，根位置和碰撞保持原配置，仍负责Niagara输入。
2. 实时状态B经GlobalShaderNormal输出到法线RT的A；RGB为编码法线。
3. 主Mud Actor已有NormalPreview组件改为球体可见代理，附着到输入球，继承0.4缩放；原球网格隐藏显示。
4. 复用现有NormalPreviewMaterial的MID创建和逐帧MudNormalBuffer绑定，新材质读取该RT，在WPO中进行整球Z平移。正常运行不做逐帧CPU高度读回，也没有加入GPU到CPU的接触反馈。
5. NormalPreview的BoundsScale=2.5覆盖当前负向位移；其组件位置读回仍是输入根位置，不能用它充当GPU位移后的球心读回。

新增六个资产均在Phase07：L_Mud_Contact、LS_Mud_Contact、MI_Surface_Contact、M_Sphere_Contact、M_ContactFixture、RT_ContactFixture。表面实例继承Phase04，覆盖ParallaxPlane=1；没有改动原表面主材质或插件C++。

源码：`Tools/MudStudy/Reference/SphereHeightContact.hlsl`。已与实际材质Custom11回读内容逐字核对；材质12个表达式均可达、原生图检查无问题。回读记录为 `contact_material_readback.json`。

## 验证结果与适用范围

证据目录：`Verification/MudProfessional/phase07-contact/`。

- `gpu_fixture.json`、`contact_results.json`：4种半径5/10/20/40cm乘9种情况，共36个真实GPU输出。覆盖两个平面、线性斜坡、偏心凸起、中央凹坑、中心越界、禁用、零高度和场景中心平移。输出通过浮点RT读回，最大算术误差0.01410cm，小于0.04cm容差。GPU夹具用解析场替换纹理读取，因此不验证纹理过滤、实时材质绑定或物理碰撞。
- 同一验证器以192圈、每圈720方向做更密集的独立支撑采样。这组曲面用例最大低估支撑约1.07584cm，属于当前算法实际限制；密集参考本身也不是严格连续域上界。
- `frozen_contact.json`：实际实时RT的32×32区域共1024像素、运行参数和双机位元数据。`frozen_prediction.json`使用这些保存数据进行双线性采样预测：球心下方表面约-7.703cm，支撑球心约15.751cm，相对根位置20cm下降约4.249cm。这是CPU预测，不能描述成GPU WPO位置的直接读回。
- 新视频目录的 `validation.json`：720帧、240个路径采样、4次各256像素的GPU检查通过。记录的输入数始终为1，轨迹误差小于0.01cm；状态B与法线RT A的局部复制误差为0；表面材质和球体材质都绑定到同一个实时法线RT。只覆盖前24秒的直行、转向、停留和再次移动。
- `integrity.json`：原始106文件加Phase01–06的21文件，共127个文件哈希未变。新六个资产快照在Assets中，依赖研究工程的已有资源与插件，不是独立交付包。R02未参与本轮编辑。

复核已有记录：

```
python Tools/MudStudy/verify_sphere_contact.py
python Tools/MudStudy/verify_replay_capture.py Verification/MudProfessional/phase07-contact/20261029T143843152519Z --scope short-preview
```

重采GPU夹具时，先DrawMaterialToRenderTarget(M_ContactFixture, RT_ContactFixture)，再ReadRenderTargetRaw(bNormalize=false)。RT像素不随资产保存。夹具源码在SphereHeightContactFixture.hlsl，读取替换之外保留接触计算；不能把成功提交绘制当作读回通过。

视频采集脚本mud_replay_capture.py已允许Phase07，归档harness.py与research_window.py供复核。原生工具缺少连续采集调度和研究窗口恢复，因此使用UE Python驱动已有脚本；没有发送外部反馈。完成后PIE退出，t.MaxFPS和t.OverrideFPS、窗口状态按采集前恢复，视口恢复Lit和实时更新，Slate节流恢复1，未保存全局配置。

## 当前限制和下一步

当前是固定预设：水平场、WorldSize=2000×2000cm、SimCenter=(0,0,0)、HeightCm=20、RadiusCm=20。参数存在组件与材质两处，尚未建立自动同步；更换网格、缩放或高度时需要重新校准。法线RT的Alpha必须继续保存对应高度。

可见代理只做竖直平移，不包含真实刚体接触、滚动、摩擦、惯性或人体脚部IK；原碰撞仍在输入球根位置。圆盘有限采样可能低估尖锐曲面的支撑，高度场像素过滤与POM步进也可能产生误差。POM地面仍没有真正几何轮廓或碰撞形变。

中心越界时着色器返回零修正；地图虽有60秒序列，本轮没有新录制完整边界段，不宣称边界连续。完整动态等价仍未验证。

下一轮优先在同一分辨率、相机、轨迹下测整体GPU成本，并比较接触开关与细节流动开关；明确66次每顶点读取是否值得保留，再决定是否改为单次GPU求解或更少采样。此后统一参数控制，补完整回放与更多曲面，最后整理投递成片和个人贡献拆解。
