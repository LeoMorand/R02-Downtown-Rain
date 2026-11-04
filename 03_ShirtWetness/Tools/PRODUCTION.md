# 衬衫湿润系统使用与维护

入口关卡：`/Game/Stormfall/ShirtTrial/Wetness/L_ShirtWetness`。
原四组干、半湿、湿透、40秒循环继续保留；右侧独立灯光展示区增加四组真实状态演示。
Play 后点击画面取得键盘焦点，按 1 查看原对照，按 2 查看天气实验。
天气实验为48秒循环，前半段吸水或受到局部命中，后半段逐渐干燥。

## 接入角色

可直接拖入 `BP_ShirtWeatherRuntime`。它是原生 `StormfallShirtWeatherDemo` 的配置包装，默认关闭演示脚本、读取现有天气集合，包含已适配的衣服和湿润组件。

现有玩家角色可以添加 `StormfallShirtWetnessComponent`，将 Garment 指向自己的穿衣 SkeletalMeshComponent，并配置12个锚点。只会为具有 `SpatialWetnessEnable` 参数的布料槽创建 MID，不改变身体和纽扣。配套材质、组件源码、骨骼和纹理需要一起迁移；运行不需要 Python、MCP 或外部程序。

不要让旧 `BP_ShirtWetness.AutoCycle` 与新组件同时驱动同一件衣服。旧蓝图继续用于参考材质演示，新组件用于天气状态。蓝图包装的 Run Scenario 必须保持关闭才能接入实际游戏天气。

## 天气与遮雨

Weather Collection 使用 `/Game/MPC_RoadWeather`。组件读取 RainAmount、Humidity；ManualMode / ManualRain 按现有天气艺术控制约定混合雨量。Humidity 影响蒸发速度，并不会直接把干燥衣物设置为湿透。

关闭 Read Weather Collection 后，可由蓝图写入 Rain Amount 和 Air Humidity。雨方向为雨滴运动方向，默认 (0,0,-1)。每个锚点沿反雨方向做碰撞检测；默认每0.2秒更新一次，共12条 Visibility Trace。用 Shelter Channel 选择专用检测通道也可以；屋顶必须在该通道上 Block。组件会忽略自身角色及其附属 Actor，避免衣服遮住自己的雨。

雨中逐渐吸水；进入屋檐只停止新的吸收，原湿度继续缓慢蒸发。Rain Absorption Seconds 和 Drying Seconds 是指数响应的时间常数，不是精确达到100%/0%的时间。一个时间常数约完成63.2%的变化。

## 入水与局部命中

在实际水面放置 `StormfallShirtWaterZone`，通过 WaterBounds 调整三维盒体。盒体上表面就是水面，旋转和缩放均参与采样；在盒外、上方和盒底下方不会产生入水。边缘限制是有界盒体，水面羽化宽度3cm。

已有 Water 插件或游戏水域系统可以调用 `SetWaterContact(Active, SurfaceZ, Contact)`。这是全局水平面适配接口，调用方负责进入/离开水域时启用和关闭。不同高度水域、倾斜水面优先使用各自的 Water Zone。

雨滴或溅水碰撞事件调用 `AddWetImpact(WorldPosition, RadiusCm, Amount)`。位置、半径单位为厘米，Amount 范围0～1。锚点按距离衰减吸水，之后保留历史并向邻近锚点扩散。组件没有自动订阅任意 Niagara 粒子系统；粒子事件或游戏碰撞逻辑需要调用此接口。

## 状态与保存

`SetUniformWetness` 设置全部锚点；`CaptureWetness` 返回版本、骨骼顺序和12个湿度值；`RestoreWetness` 校验版本、数量、骨骼顺序和有限数值，验证失败时不改现有状态。把返回结构存入自己游戏的 SaveGame，再在角色初始化完成后恢复，即可跨关卡/存档保留湿度。系统不会自动写入磁盘或替游戏选择存档槽。

平均湿度、12组 Wetness / Exposure / Immersion、MID数量和 Cloth 数量都可在组件状态中查看。Draw Debug 显示随骨骼移动的采样球。Manual Preview 只覆盖显示，不覆盖存储的湿度历史。

## HLSL 与材质

`Shaders/ShirtSpatialWetness.hlsl` 是空间重建源码；`upgrade_production.py` 将源码写入现有母材质的 Custom 节点。编辑磁盘 HLSL 不会自动刷新 uasset，需要运行升级脚本重新写入和编译。

每个 `WetAnchor0..11` 为 RGBA：XYZ 是当前骨骼点变换到网格组件空间的位置，A 是湿度。材质使用不含 WPO 的位置转换到同一空间，再做归一化逆四次距离插值。运行模式直接控制最终颜色/粗糙度/Fuzz 的湿润权重，绕过旧 UV 渐变；旧参考演示通过 SpatialWetnessEnable=0 保持原逻辑。

这是一种12单元的粗粒度湿润场，能够跨UV接缝连续过渡，但不等于逐像素雨滴历史或真实纤维毛细传导。近距离相互靠近的袖子与躯干可能出现空间插值串色；针对复杂动作，需要更密锚点或基于表面拓扑的湿度图方案。

当前材质统计为432 pixel instructions、829 vertex instructions、12 samplers。指令数不是毫秒性能；具体帧时以最终报告中的实测条件为准。

## 湿棉布观感（2026-10-26）

`upgrade_look.py` 在 `upgrade_production.py` 之后运行，同样是幂等追加；只把 BaseColor 和 Roughness 改接到新节点，旧节点保留。三段 HLSL 位于 `Shaders/`：

- `ShirtWetFront.hlsl`：在网格组件空间叠加约16cm与6cm两层噪声，打散12锚点插值的平滑湿度，形成不规则交界。扰动乘以4W(1-W)，完全干或完全湿的区域保持0/1不变。同时输出约1cm的纤维噪声。
- `ShirtWetColor.hlsl`：湿后颜色先提高饱和度再变暗，代替整体乘系数；水渍线只在湿度沿表面有变化的位置出现，均匀半湿或全湿不会多一圈黑边。效果按布料干燥时的线性明度区分（smoothstep 0.1→0.35）：深色布（原衬衫约0.07）完全变暗、不透肤，水渍线只保留40%；浅色布变暗程度减半，透肤和水渍线完整。这是参照深色背心汗湿和浅色湿衬衫的照片做的取舍。
- `ShirtWetRoughness.hlsl`：湿后粗糙度为0.68加纤维噪声；只有湿度超过0.85时，才在局部形成粗糙度0.3的水膜高光。

参数位于材质分组 `04 Wet Cotton Look`：Wet Saturation 1.4、Skin Under Cloth、Skin Show Through 0.6、Wet Edge Darkening 0.6、Wet Front Breakup 1.0、Wet Film Roughness 0.3、Wet Film Amount 0.3。五个MI的 Wet Roughness / Wet Albedo Multiplier 已改为0.68 / 0.55。

对比图：`Preview/ShirtWetness/look_comparison.png`，由 `MakeLookReview.ps1` 拼接。`look_review.py` 的 `frame()` 设置PIE近景机位，`look(enabled=False)` 在同一组MID上恢复旧参数作为对照，`tint` 只在PIE里提亮衣服颜色（对比图下排乘6，近白色）。

限制：原衬衫是深灰色，干湿对比天然较弱，透肤与水渍线要在浅色衣服上才明显。水渍线依赖12锚点场的梯度，位置和宽度都比较粗；要得到雨点斑和流淌，需要改为UV空间湿度图。本轮未重新测量指令数，原432条像素指令的统计已过期。

## 雨夜街景展示关卡（2026-10-27）

`/Game/Stormfall/ShirtTrial/Wetness/L_ShirtWetness_Street` 复制自 `/Game/TA_Demos/R02_Downtown_Rain`，原R02地图未修改。场景和衬衫组件共用 `MPC_RoadWeather`，所以角色会跟着街景雨量自然变湿。

`build_street_showcase.py` 可以重复运行，会更新带标签的Actor，不会重复添加：
- `Shirt_Street_Hero`：`BP_ShirtWeatherRuntime`，放在R02已验证的street-wide主机位前方600cm，脚落在地面。身体槽位0/1覆盖为 `M_ShirtShowcase_Skin`（哑光肤色），以单节点方式循环播放 `MM_Idle`。
- `Shirt_Street_Camera`：头到腰的半身构图，FOV 26。网格里腿和头、躯干在同一个槽位，没有办法只给腿换裤装，所以不拍全身。`M_ShirtShowcase_Trousers` 已建好，暂未使用。
- `Shirt_Street_Key` / `Shirt_Street_Rim`：暖色主光30cd、冷色轮廓光90cd，都是可移动聚光灯。
- `WeatherArtController.UseManualControlInPlay=True`：在这张副本里，进PIE就是满雨量（R02的手动值1/1/1）。

预览：PIE中运行 `look_review.view()` 切到近景相机，`soak(30)` 把湿度模拟推进30秒；截图前执行 `DisableAllScreenMessages`。对比图：`Preview/ShirtWetness/street_showcase.png`，由 `MakeStreetReview.ps1` 拼接。

已知问题：
- PIE中提示显存超出预算约1.3GB（R02街景本身很大），截图只是隐藏了提示，并没有解决显存问题。
- 雨粒子跟随玩家位置生成，近景相机里看不到雨丝。
- 暗光下深色衬衫干湿差别较细微。
- 头部仍是没有五官的人台。

## 衣料物理

物理使用独立副本 `Physics/SK_ShirtWeatherProxy` 与匹配 Manny 骨骼的 `PA_Mannequin`。LOD0保持原193024个三角形的显示网格；LOD1按8%比例生成，前后区域抽取2709个物理顶点驱动LOD0，运行时读回297个动态粒子。前后衣摆下部20%释放最大0.25cm，其余位置固定；小幅限位避免紧身模型在衣摆处穿出身体。只制作衣摆，袖子保持原蒙皮。

Drive Cloth Response 开启后，组件对本角色的 Chaos interactor 写入阻尼和动画约束：默认阻尼0.08→0.30，Anim Drive 0.15→0.45。参数仅影响当前组件的求解器，不修改共享布料配置。它表达湿后摆动收敛，不代表真实吸水质量、皮肤吸附或体积守恒；没有添加全身收缩WPO。

演示和运行蓝图固定显示LOD0，以验证低模代理驱动高模。若项目启用自动LOD，当前LOD1不模拟衣料，仅用于远景蒙皮回退；需要动态LOD的项目应按各LOD建立衣料映射。纯材质应用可使用原无衣料物理的两套网格，并关闭 Drive Cloth Response。旧 `SK_ShirtWeatherCloth` 是高成本物理试验记录，当前演示不使用它。

首次运行会暂时隐藏衣料网格，等待第一次有限、非空的衣料模拟数据完成后再显示，避免UE 5.8在首帧绘制离屏衣料阴影时读取尚未创建的GPU缓冲。此步骤不重置湿度历史。

## 验证与维护

`verify_production.py` 在此关卡 PIE 下验证实际组件、真实屋檐、MPC输入、局部入水/命中、存储恢复、组件空间跟随和120次MID复用。它会临时改变运行中的演示人物，停止PIE恢复关卡。

`Stormfall.ShirtWetness` 是9项原生自动化测试。全工程测试通过 `Tools/Test.ps1` 运行；已有 MetaHuman 失败必须与本次衬衫结果分开记录，不能把完整工程描述成全部通过。

`Package.ps1` 执行此关卡的 Win64 Development Build/Cook/Stage/Pak/Archive，输出 `Saved/Packages/ShirtWetness`，日志写入 `Verification/ShirtWetness/Production/package.log`。必须检查真实退出状态和运行结果，脚本存在不表示已经打包成功。

当前包已完成普通独立运行检查，退出码0。运行 `RunPackaged.ps1` 查看；运行 `CheckPackage.ps1` 重做15秒启动/退出检查，结果为 `packaged-runtime.json`。可选 `-Benchmark` 使用固定60Hz步进，另存 `packaged-benchmark.json`，不代表实测稳定60FPS。`-CaptureCsv` 是独立诊断开关：目前CSV采集后退出返回777003，仍待排查，结果另存 `packaged-csv-diagnostic.json`。普通运行和固定步进不需要开启它。`Package.ps1 -Iterative -SkipBuild` 仅适用于C++二进制已是最新、只更新内容的情况；修改源码后应执行默认完整构建。

备份：`Saved/Revisions/ShirtWetness_Production_20261023-155052`。不要重跑旧 `build_materials.py`；升级使用新的幂等脚本，保留原节点。绑定衣料时必须持久化 `UserSectionsData`，否则重建后 `BindToSkeletalMesh=true` 仍可能没有活动衣料分区。

从备份重建代理时，先复制原网格到 `Physics/SK_ShirtWeatherProxy`，用原生 `generate_skeletal_mesh_lods` 生成 `lodCount=2, trianglePercentages=[8]`，再执行升级脚本。脚本不会重复生成已有LOD或删除原参考图。


## 显存：Downtown_West 贴图限制到 2K（2026-10-27）
- 原因：8GB 显卡 + `r.Streaming.PoolSize=2300` + 大量 4K 贴图，纹理常驻约 2.05GB，当前画面只需约 180MB。
- 处理：`cap_textures_2k.py` 把 /Game/Downtown_West 下 334 张 >2048 的贴图设 MaxTextureSize=2048（源图保留）。纹理常驻 2052MB → 约 258MB，磁盘数据 5419MB → 2097MB。
- 影响所有用到这些贴图的关卡（含 R02）。回退：`run(restore=True)`，旧值在 Verification/ShirtWetness/Look/texture_cap_2k.json。
- 未改 DefaultEngine.ini。

## 近景雨丝与干湿对比（2026-10-27）
- 雨丝看不到的原因：R02 雨（NS_R02_RainFollowView）跟随相机，但在相机上方约 15m 生成、密度低，近景基本拍不到。不改共享资产，在副本关卡加 `Shirt_Street_RainClose`（同一 Niagara，位于相机→角色 60% 处、Z=500，SpawnRateMultiplyer=10）。
- 干湿对比：主光 30→70 cd，轮廓光 90→250 cd。夜里深色衬衫干态被打亮成浅灰，湿后（0.88）成深炭灰，差别肉眼可见。
- 参数在 `build_street_showcase.py` 的 CLOSE_RAIN 和灯光表；对比图 Preview/ShirtWetness/street_showcase.png（street_dry_v4 / street_soak30_v4）。
- 已知：镜头前偶有大而糊的近处雨滴；雨滴偏暗（材质不受逆光提亮）。
