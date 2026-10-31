# R02 天气系统完善与验收工具

> **2026-10-24 状态更新：** 下文为最初离线阶段的设计记录，执行状态以 [最新实装报告](../../Verification/R02/REPORT-20261024.md) 为准。材质架构、HLSL 与来源见 [Shader 说明](SHADERS.md)，45 张有效截图见 [评审页](../../Preview/R02/index.html)。
>
> 现已安装地面修正、修复 emitter 名称、加入独立物体水痕函数、将物体覆盖扩至 11 个组件并清理植物失效缓存。六个天气母材质 UE 编译、14 项离线回归、DXC、180 秒自动天气参数循环通过。Windows Development 打包与实际启动检查通过。打包八段采样的固定近景涟漪 GPU 增量中位数为 1.64695 ms；外层性能启动脚本退出状态仍需复核，不宣称完整入口全绿。完整连续天气视听、更多材质族、玻璃曲面和反射异常归因仍未完成。
>
> 当前正式性能入口为 `RuntimeBenchmark.ps1 -Execute`，支持 `-PackageRoot`；打包启动入口为 `PackageSmoke.ps1 -PackageRoot <归档目录> -Execute`。归档中的 `Launch_R02.cmd` 显式打开 R02。旧编辑器 benchmark 仅用于诊断。

目标关卡 `/Game/TA_Demos/R02_Downtown_Rain`。本目录创建于 2026-10-23，属于现有天气整合的后续工程化工具。当前用户要求其他聊天继续使用工程，因此本轮只完成离线代码、数学检查、独立 DXC 编译与命令预演。

## 当前已验证与未验证

- 已验证：9 项离线回归、Python 语法、PowerShell 语法、6 个命令入口的 dry-run；候选 Shader 在 Windows SDK DXC 中以 `ps_6_0`、`-Ges -WX` 编译通过。
- UE worker 依据本地 UE 5.8 头文件和既有工具编写，尚未在专用进程执行。UE Python 参数映射、截图、PIE、CSV 输出仍需首次集成验证。
- 现有 `.uasset`、关卡、蓝图、MPC 和项目 INI 均未由这些工具修改。候选代码尚未安装。
- GPU 数据、全场景外观、自动雨停循环、Cook、打包运行均未验收。

## 离线执行

在工程根目录运行：

```powershell
./Tools/R02/Test.ps1
python Tools/R02/preflight.py
./Tools/R02/Run.ps1 -Mode capture
```

前两条检查离线工具和磁盘基线，第三条只输出计划命令，不启动 UE。`preflight.py` 为每次检查建立唯一 UTC 目录，记录目标地图、MPC、天气资产与候选代码 SHA256；读取最近引擎日志中的缺依赖记录。它不会修改资产或调用编辑器。

首次测试发现系统沙盒临时目录不可写，测试夹具已改用工程 `tmp/R02-tests`，每个用例使用独立临时目录。合成 CSV 仅验证统计逻辑，不作为实测数据。

## 独占工程后的执行顺序

确认其他聊天和工具不再操作该工程，关闭 Stormfall 编辑器后，才使用两个显式执行开关：

```powershell
./Tools/R02/Run.ps1 -Mode audit -Execute -Exclusive
./Tools/R02/Run.ps1 -Mode capture -Execute -Exclusive
./Tools/R02/Run.ps1 -Mode cycle -Execute -Exclusive
./Tools/R02/Run.ps1 -Mode benchmark -Execute -Exclusive
./Tools/R02/Run.ps1 -Mode cook -Execute -Exclusive
./Tools/R02/Run.ps1 -Mode package -Execute -Exclusive
```

每次执行输出到 `Verification/R02/<UTC>-<随机ID>-<mode>`，记录命令、独立引擎日志和结果。审计使用 NullRHI；截图、循环、性能工具使用独立离屏编辑器并关闭桥接插件，避免争用其他聊天的桥接连接。执行前检查工程编辑器是否打开；检查失败则停止。工具只在超时后停止自己启动的 PID。

执行并非接受：进程退出成功仍需检查 `result.json` 和日志；截图需要人工审核，GPU CSV 需要确认有效数据，打包需要实际启动测试。

### audit：资产与节点基线

导出组件材质槽位、控制器参数、MPC 读回、四个天气母材质的 Custom 代码、代码 SHA256、输入名称和表达式数量。不调用保存、不重新生成材质。首先检查实际 Custom 代码是否仍与历史 Scatter 导出一致；其他聊天可能已经修改，不能按旧索引盲写。

### capture：状态矩阵

`acceptance.json` 包含 15 个对照状态，覆盖干燥、潮湿、湿地、满积水、雨后，以及大小/密度/速度/强度/随机度端点。每张图记录机位、输入、MPC 和图片 SHA256。每次换状态先恢复基线涟漪倍率，再应用单项变化，避免上一组参数污染下一组。

目前只填入有历史依据的沥青机位 `(12175,500,150), (-40,270,0)`；FOV 新统一为 70°，需要实际确认构图。不能把这一个机位当作全场景验收。独占时先增加混凝土、砖地、路缘、玻璃、物体与街区全景，再按近/中/远景补拍；不得编造未经观察的坐标。

图像是实际引擎时间采样，未锁定事件相位，不能对两个涟漪帧做严格逐像素差分。需要严格材质差分时，应另做固定时间输入和固定曝光，记录全部渲染设置。

### cycle：完整自动天气读回

在专用编辑器中启动 PIE，强制该进程进入自动模式，调用天气管理器 `SwitchWeather`。按游戏时间采样 180 秒，75 秒时停雨，每 0.5 秒记录 Humidity/RainAmount/ManualMode。检查初始干燥、达到湿润、雨量上升、停雨、最终干燥和全程自动模式。

此检查验证参数链路；还需同机位录像检查自然过渡、粒子、声音、水痕和涟漪。若关卡管理器函数改名或默认状态改变，工具应失败并读取新实现，不强行制造通过结果。

### benchmark：涟漪成本诊断

顺序 `off/on/on/off/on/off/off/on`，每段预热 25 秒、采样 20 秒，屏幕比例 100%，禁用 VSync、动态分辨率和后台限速；控制器其余参数恢复为读回基线。设置并记录机位 FOV，开启 Realtime/GameView。

CSV 命令已核对 UE 5.8 `CsvProfiler.cpp`：先 `csvprofile STARTFILE=<唯一文件名>`，再 `csvprofile START`、`csvprofile STOP`。该接口忽略 START 后的 `-filename`，并且对 START/STOP 作大小写敏感比较。工具从原生 `Profiling/CSV` 输出等待稳定后复制到本轮结果目录。

```powershell
python Tools/R02/summarize.py Verification/R02/<本轮benchmark目录>
```

汇总剔除 metadata、NaN、Infinity，拒绝缺失/零值/少于 120 个有效 GPUTime 样本，按相邻正反顺序配对计算 GPU 中位数差，保留四组差值和符号一致性。GPU 嵌套 Pass 时间不能相加。

这是编辑器视口诊断，不是独立游戏或打包性能。窗口大小、GPU 时钟、温度、PSO misses、后台 GPU 负载和 Streaming 仍需记录；正式成本结论必须在独立游戏/打包固定机位复测。启动参数的 1920×1080 不证明编辑器视口实际绘制尺寸等于该值。

### cook / package：指定地图交付

Cook 使用明确 `-Map=/Game/TA_Demos/R02_Downtown_Rain`。Package 使用 UAT `BuildCookRun`，Development/Win64，明确 R02 地图，输出到本轮唯一目录，不修改共享 INI，也不把旧地图配置当作 R02 已包含的证据。

首次打包前需要解决依赖与插件扫描问题。打包后实际启动归档 `.exe`，检查默认入口、Q 键、完整天气循环、玻璃/地面、材质回退、日志、声音和关闭重开。Cook 成功并不等于这个测试已通过。

## 候选 Shader

`ripple_candidate.hlsl` 以当前历史 Scatter 代码为基础，有两项变化：

1. 最终寿命统一限制 `min(lerp(...),1.95/rate)`。旧代码只限制随机寿命分支；当 rate=3、随机度=0 时，寿命可达 0.9 秒，但两个历史周期只有约 0.667 秒，事件可能在衰减完前被丢弃。默认 rate=1.5 时原寿命范围不受影响。
2. 像素 footprint 大于所有候选最大半径，或密度/强度为零时，提前返回平法线。导数在分支前求值；远处提前退出基于现有 AA=0 条件，不宣称实际 GPU 提速。

3×3 邻格可覆盖最大 0.6 单元半径的环脊，先前“半径随机放大导致邻格不足”的疑点经核算不成立；Gaussian 尾部本身不是严格紧支撑，仍需检查边界连续性。

`validate_shader.hlsl` 仅提供独立 DXC 语法环境。其通过不证明 UE Custom 节点、World→Tangent、目标平台和材质实例编译通过。安装前必须备份实际母材质、导出最新代码与连接，按实际 Custom 节点身份更新，保留原输入、描述和节点；编译、回读、截图后再单资产保存。不提供会自动覆盖当前艺术资产的一次性安装器。

## 当前需要现场处理的事项

1. 植被依赖 `/Game/ProceduralNtr_vol2/pnp_v2_assets/Textures/Wind/wind_normal` 缺失。磁盘有 `/Game/Downtown_West/Textures/Wind/T_wind_normal`，需检查像素内容、NormalMap/LinearColor 类型与采样约定，确认兼容后修复真实引用，不能只建立同名空资产掩盖错误。
2. 启动报告 GameFeatureData 扫描缺失。先审查实际 GameFeature 插件与资产，再添加准确扫描规则或排除不需要的插件；不在其他工作进行时改共享配置。
3. 长条反射：同机位分别关闭程序涟漪、底材法线、反射贡献，配合 roughness/normal 视图和 TSR/反射对照定位。任何一次没复现都不能算修复。
4. 物体仍需按材质家族扩展白名单，并统一世界向下水痕；玻璃检查四向、镜像、曲面和尺度。审计槽位记录可用作替换前后对照。
5. R02 与 M13–M19 独立屋顶实现的合并需要依赖和效果验收。优先交付 R02 当前链路，合并前逐组件验证状态、单位与遮雨模型。

详细状态与后续验收门槛见 `Verification/R02/REPORT-20261023.md`。

## 录制用天气时间线

`weather_timeline.py` 按固定时间线驱动 WeatherArtController（手动模式），每次重录天气变化都一样：0–3 秒干燥，3–8 秒雨量升到 1，8–18 秒地面变湿，18–28 秒积水长出并出现涟漪，28–36 秒保持。按真实时间推进，编辑器掉帧也不影响节奏。结束后恢复控制器原值，不保存任何东西。

在已打开 R02、视口 Realtime 开启的编辑器里，于 Output Log 的 Cmd 输入框执行：

```
py "D:/aco/unreal/Stormfall/Tools/R02/weather_timeline.py"
py "D:/aco/unreal/Stormfall/Tools/R02/weather_timeline.py" stop
```

运行期间关卡会被标记为已修改；不要在运行中保存。时间线定义在脚本顶部的 `KEYS`，可以直接改。

## 昼夜切换与氛围（2026-10-31）

R02 复用 Downtown_West 自带的两个光照子关卡。白天：体积雾密度 0.006→0.025、消光 2→4、散射方向 0.98→0.85，太阳体积散射 2.5→6、光束泛光 0.005→0.15，形成雨天雾气与丁达尔光。夜晚：雾密度 0.0125→0.022、散射方向 0.98→0.6（路灯周围出现光晕）、环境雾亮度加倍；夜晚后期的自动曝光最低亮度 0.5→0.05、曝光补偿 +1.5。修改前的子关卡备份在 `Saved/Revisions/Before_R02_LightingLook_*`。

在编辑器视口里切换（只改编辑器可见性，不保存）：

```
py "D:/aco/unreal/Stormfall/Tools/R02/lighting_look.py" night
py "D:/aco/unreal/Stormfall/Tools/R02/lighting_look.py" day
```

Play 模式仍使用白天（白天子关卡是常驻加载）；夜景请在编辑器视口中录制。离屏截图没有自动曝光，夜景亮度以视口为准。
