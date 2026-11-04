# Lighting Presets 光照预设

把关卡里的灯光、天光、高度雾和后期存成**光照预设**，随时应用、对比、批量出图。
UE 5.8 编辑器插件，不依赖任何项目内容，拷进别的项目的 `Plugins/` 就能用。

## 能做什么

| 功能 | 说明 |
|---|---|
| 捕获 | 当前关卡的光照 → 一个 `LP_<名字>` 数据资产 |
| 派生 | 复制一个预设再改参数，全程不碰关卡 |
| 改参数 | 面板参数表里直接改值，可选同时实时应用到关卡 |
| 应用 | 先预览改动，再写入；一次 Ctrl+Z 撤销；坏数据整次不写 |
| 对比 | 两个预设（或预设 vs 当前关卡）的逐项差异；视口里 A/B 来回切 |
| 校验 | 预设里哪些灯在本关卡找不到、哪些灯没被预设管到 |
| 排除 | 给不该管的灯打 `LP:Ignore`，永远不进预设 |
| 出图 | 预设 × 机位批量截图 → 带 A/B 滑块的对比页，并自动更新预设缩略图 |
| 导入导出 | JSON，方便放进版本管理看 diff |

## 面板

**Window → Lighting Presets**，三栏：

**左：预设库**：缩略图 + 名字，双击 = 预览。

**中：选中的预设**
- 大缩略图
- **Preview** 列出会改什么，不写入；**Apply** 写入关卡（一步撤销，不自动保存）；**Validate** 校验
- **Update from level** 用当前关卡覆盖它；**Export JSON**；**Delete**
- **Include light positions**：是否连灯的位置朝向一起存/应用
- **参数表**：灯 / 属性 / 值。上方输入框过滤（如 `TopLight`、`intensity`）。改值后回车保存；
  勾选 **Apply edits live** 时同时应用到关卡。值的写法：数字 `8e7`，颜色 `[255,240,220,255]`，开关 `true/false`

**右：工具**
- **New preset**：**Capture level** 抓当前关卡；**Copy selected** 从选中预设派生（再去参数表改）
- **Compare**：A、B 选预设或 `@world`；**Differences** 列差异；**A/B toggle** 视口来回切
- **Exclude actors**：按名字前缀排除 / 恢复（例如 `Diagnostic_`）
- **Render comparison**：勾预设和相机、设分辨率，**Render** 开始（再点 = 取消）；显示进度和警告，完成后自动打开对比页

底部输出框显示每次操作的结果。

## 典型流程

1. 调好一套光 → **Capture level** 存成 `Day_A`
2. 选中 `Day_A` → **Copy selected** 得到 `Day_B` → 在参数表里改几个值（勾着 Apply edits live 就能在视口里看）
3. **Compare** 选 A、B → **A/B toggle** 来回看
4. **Render comparison** 勾上两个预设和几台相机 → **Render** → 对比页自动打开
5. 选定的那套 **Apply**，Ctrl+S 保存关卡

## 灯是怎么对上号的

每个被管理的 Actor（点光、聚光、矩形光、平行光、天光、高度雾、后期体积）用一个 **key** 识别：

- 有 `LP:<key>` 标签就用标签
- 没有就用 Actor 名字（label）

想让一个预设用到另一个关卡，给两边对应的灯打上同样的 `LP:` 标签即可。

后期体积由预设"完整接管"：预设里没记录的覆盖项，应用时会被关掉，保证效果完全还原。

## 出图

出图用场景里的相机（CameraActor / CineCameraActor）。**相机自己带曝光覆盖时，预设的曝光对它无效**——开始出图时会给出警告。

结果在 `Saved/LightingPresets/Renders/<tag>/`：
- `<预设>__<相机>.png`
- `index.html`：网格总览 + A/B 滑块对比
- `manifest.json`

出图结束（成功、取消或出错）都会把关卡光照恢复成开始前的样子。出图期间使用临时实时视口覆盖，并主动处理后台视口的截图请求；结束时移除插件自己的覆盖，保留原有实时设置。

自动化面板操作时，可用 `unreal.LightingPresetRenderLibrary.configure_panel_render(presets, cameras, width, height)`
设置真实面板的勾选项与分辨率，再用 `get_panel_render_configuration()` 读回 JSON 核对。
配置接口会刷新列表并拒绝不存在的名称、非法尺寸或出图期间的改动；它不启动出图、不应用光照。
核对后仍通过面板 **Render** 按钮开始。出图前开启视口 Game View，避免编辑器辅助网格进入构图预览。
窗口在后台或最小化时，配置接口会先同步已完成批次的状态，清除旧的轮询计时器，
避免实际出图完成后面板仍误报忙碌。正在出图的批次仍拒绝重新配置。

## AI / 脚本接口

插件注册了工具集 `lighting_presets.toolset.LightingPresetTools`（MCP 里用 `epic.call_tool` 调）：
`list_presets` `capture_preset` `derive_preset` `apply_preset` `diff_presets` `validate_preset` `set_ignored`
`list_cameras` `add_camera` `render_start` `render_status` `render_cancel` `run_tests`

Python 直接用：

```python
from lighting_presets import core, store
p = core.capture("Day")                    # 抓当前关卡
store.save(p)                              # -> /Game/LightingPresets/LP_Day
core.apply(store.load("Day"), dry_run=True)
core.apply(store.load("Day"), overrides={"KeyLight": {"intensity": 5e7}})
```

## 结构

```
Source/LightingPresets         ULightingPreset 数据资产（运行时模块）
Source/LightingPresetsEditor   Slate 面板（编辑器模块）
Content/Python/lighting_presets
  core.py     捕获 / 应用 / 对比 / 校验（不含任何项目名）
  store.py    资产与 JSON 存取
  render.py   批量出图 + 对比页
  ui.py       面板调用的入口
  toolset.py  AI 工具接口
  tests.py    自动化测试
Content/Tests/LP_TestMap       测试专用空地图
```

逻辑全部在 Python 核心里，面板和 AI 接口都只是调用它。

## 测试

```python
from lighting_presets import tests; tests.run()
```

或 MCP：`run_tests`。在插件自带的空地图里跑，跑完回到原关卡；当前关卡有未保存改动时拒绝运行。

覆盖：属性名在当前引擎版本存在、捕获→应用完整还原、预览不写入、一步撤销、覆盖参数、
坏 key / 坏数值整次不写、标签 key 与校验、颜色通道顺序、资产与 JSON 往返，以及非实时视口的临时覆盖与恢复，共 19 项。

开发中测试抓到的坑（都已修复并有对应测试）：
- `unreal.Rotator(a, b, c)` 位置参数顺序是 roll, pitch, yaw
- `unreal.Color(a, b, c, d)` 位置参数顺序是 B, G, R, A
- `FColor` 收到 0–1 浮点会被截断成接近黑色
- 后期覆盖项没被关掉，预设无法完整还原
- 高分辨率截图调用内部会推进编辑器帧，导致出图状态机重入

## 已知限制

- AI 调用时，默认值为空列表/空字符串的参数仍需显式传入（工具集注册的限制）
- 参数表的值以文本编辑（JSON），还没有取色器和滑条；改参数存进资产这一步没有撤销（有 JSON 导出和 git 兜底）
- 只管灯光、天光、高度雾、后期；天空大气、体积云等暂未纳入
- 出图用编辑器高分辨率截图，不是 Movie Render Queue 的最终质量
