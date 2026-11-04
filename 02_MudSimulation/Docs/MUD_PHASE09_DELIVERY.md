# Phase09：当天投递展示版（2026-10-29）

交付入口为 `Deliverables/MudPortfolio_20261029/`，另有轻量ZIP。73秒1080p30主片包含近景、接触A/B、流动A/B、边界段与技术拆解；另保留连续64秒回放。均为离线采集，不是实时FPS或新版Shipping验收。

## 新展示关卡

地图 `/Game/MudStudy/Professional/Phase09/L_Mud_Portfolio` 使用专用LS_Mud_Portfolio，直接绑定本关卡球体。轨迹与Phase08相同，60秒；采集额外记录4秒末尾停留。

两个新MI分别继承Phase04流动、Phase03静态材质。展示参数为ColorMult=0.7、ComputedDetailStrength=0.6、TileMapRoughness=0.035、Specular=0.3。统一高度20cm、POM参考面1及其他单位关系保持。旧阶段未改。

ProfessionalControls继续集中控制高度、接触和细节模式。新M_Sphere_PortfolioContact扩展了区域边缘的视觉交接；不改求解器、输入轨迹或CPU碰撞。源码为Reference/SphereHeightContactPortfolio.hlsl。

## 边界修复

首次完整采集20261030T015833868998Z的中心越界会直接返回零修正，0.1秒间隔的相邻读回预测出现约6.49cm差值。保留作诊断，不用于最终主片。

新着色器将距边界4个球半径内的补偿乘以smoothstep，在边界回到未补偿姿态，域外维持原输入高度。这是视觉交接；过渡带允许贴合偏差，不提供域外刚体支撑。内部66次最大读取的支撑计算保持。

新增16项解析平面的GPU混合算术检查通过，最大读回误差约0.01557cm，见edge_fixture.json与edge_fixture_validation.json。该夹具替换了纹理读取，不验证纹理过滤或物理接触。

第二次20261030T020659573086Z仍以0.1秒间隔采样，差值包含一段连续运动。最终改成逐渲染帧采样，两次跨域相邻帧预测差约0.01537cm、0.0000125cm。它们是GPU高度读回的CPU支撑预测，不是直接WPO顶点读回；不把不同采样间隔的数据当作同条件误差改善率。

## 最终记录

完整采集：`Verification/MudProfessional/phase09-delivery/20261030T021251128855Z/`。

- 64秒、1920帧、1080p；640个路径采样，路径误差约2.27e-13cm；直行、转向、停留、返回、边界和末尾停留均覆盖。
- 219次局部GPU检查，每次源状态与法线各256像素，值均有限、高度复制误差0、实时绑定通过。
- 4张冻结图位于约12秒同一模拟时刻、同一机位；切换后先稳定渲染3次。
- 全程与边界检查通过，分别见validation.json和boundary_validation.json。

流动对照：静态20261030T020930848796Z、流动20261030T021114055249Z，各12秒、360帧、同一跟随机位。采样位置差和帧序列时钟差均为0。属于同轨迹独立采集，不宣称模拟纹理像素级相同。

录制由mud_replay_capture.py调度Slate回调、图像写出和研究窗口恢复；资产、参数和序列使用原生工具编辑。没有升级工具插件或发送外部反馈。采集后结束PIE，恢复Lit、实时视口、Slate节流与原时间步设置。

复核已有记录：

```
python Tools/MudStudy/verify_replay_capture.py Verification/MudProfessional/phase09-delivery/20261030T021251128855Z
python Tools/MudStudy/verify_portfolio_delivery.py Verification/MudProfessional/phase09-delivery/20261030T021251128855Z
```

## 成片与交付

build_portfolio_reel.py使用真实UE图像序列和文字图卡制作73秒主片：4秒标题、28秒运动表现、8秒接触A/B、8秒流动A/B、6秒停留、6秒边界、13秒技术拆解。另保留连续64秒回放。

按章节抽帧检查中文、构图、对照标签及范围；视频帧数、时长和完整解码结果见交付目录video_validation.json。package_portfolio_delivery.py生成证据摘要、图卡、校验值和轻量ZIP；不发布到外部服务。

Phase08的8轮性能属于旧预设、720p、D3D12 SM6。本轮改变显示参数及边界混合，没有把旧数字套到最终1080p预设。新版Shipping、目标真实时间步性能、完整动态等价仍未验收。

参考/共享资源来源与个人贡献建议写入技术说明，避免把参考系统整体宣称为个人原创。原阶段完整性与新7个资产快照见本阶段integrity.json。R02未参与编辑。
