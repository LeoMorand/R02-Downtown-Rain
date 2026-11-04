# Research Render

## 当前主镜头与材质研究

最新验证的研究入口为 `study_latest.txt` 指向目录中的 `review.html`，包含 12 个 MRQ 机位试拍、同机位三阶段对照、材质诊断视图、新进程材质回读和 4K 图片。原单镜头流程保留在下方，两个入口互相独立。

`Launch.ps1 -Study` 根据 `study.json` 运行：`mode=scout` 使用 shots 列表；`mode=refine` 使用 hero 机位，生成 Baseline / MaterialOnly / Lookdev 三份关卡及 MRQ 输出。refine 会为具有合适法线输入的 Control 材质创建独立父级和实例，保持纹理引用，统一采样器语义，增加粗糙度下限和高光倍率；叶片另外使用双面植被着色。没有合适法线输入的材质列入跳过记录，不自动替换纹理。

`Launch.ps1 -StudyFinal` 在新进程回读逐槽引用、纹理、采样器与植被设置，检查源文件哈希后输出 4K。`python build_review.py` 检查 PNG 尺寸与输出完整性并生成对照入口。主编辑器内可运行 `OpenStudy.py` 打开验证关卡；当前地图未保存时会拒绝切换。

这些是本轮验证流程，不代表所有材质物理正确、原游戏着色器完全恢复或实时性能已经验收。输出中的源几何接缝、黑区和既有未适配项须继续处理。

研究大厅 v04 专用外观与渲染流程。现阶段是可重复的灯光/材质小样管线，不代表已达到作品集成片标准。

## 运行

从工程根目录执行 `powershell -ExecutionPolicy Bypass -File Tools/ResearchRender/Launch.ps1`。

启动隐藏的独立 UE 编辑器；不会切换主编辑器当前关卡。首次启动和资源加载需要时间。每次生成唯一的新关卡和结果目录，不覆盖 v04。

`latest.txt` 指向最近一次运行，首先检查该目录的 `report.json`：`phase=complete`、`errors=[]`、`source_files_unchanged=true` 才表示该轮通过。`before.png` 与 `after.png` 是同机位、同尺寸的诊断图。实测 SceneCapture 与 MRQ 亮度差异明显，因此不能用这两张图决定最终灯光和曝光。

推荐实际流程：`Launch.ps1` 建立关卡与材质后，在同一预热进程自动输出 1600×900 MRQ 预览 → 查看 `Draft/LS_Hero.0000.png` 和 `draft_result.json` → 调整预设重新建立 → 满意后 `Launch.ps1 -Final`。`Launch.ps1 -Draft` 可单独重跑预览。Draft 和 Final 使用同一套 MRQ 配置，Draft 只覆盖分辨率与输出目录；不会修改保存的 4K 预设。

在主编辑器保存当前关卡后，运行 `OpenLatest.py` 可打开该轮独立关卡。脚本会拒绝丢弃未保存关卡。

## 调整

编辑 `preset.json`，再启动一次新运行：

- `camera`：原重建坐标系下的位置、目标、FOV。流程根据 `CR_04486_research_sector_lobby_main_new` 的当前位置解析平移；旋转过的锚点会明确拒绝，不猜测。
- `lights`：矩形光的位置、目标、流明、线性 RGB、尺寸和作用距离。
- `ambient_intensity`：原诊断环境立方体的补光量。
- `exposure_bias`：固定曝光条件下的补偿。
- `material_groups`：按材质路径关键词选择颜色组，复制材质实例后乘以线性 RGB。支持现有 `ControlColorMultiplier` 和 `CR_Color`；无接口的材质会列入报告，不改图强行适配。
- `width/height`：小样实际尺寸，以 JSON 为准。

灯光预设是艺术起点，不是对原游戏光照的恢复，也不是对所有硬件的最优配置。未添加自定义 Shader 或修改引擎管线。

## 产物

- `inventory.json`：材质、用户、父材质、贴图和参数清单。
- `material_assignments.json`：逐槽原引用和新引用；恢复到 v04 可直接打开原关卡，本轮资产留在自己的 Render 目录。
- `report.json`：实际生效的预设、锚点偏移、源资产哈希、几何验证、错误与输出信息。
- 独立关卡：新增灯光、相机和私有材质实例。保留原网格、贴图、材质父级和布局。

前后画面使用持久 SceneCapture2D，显式启用 Lumen 并跨真实编辑器帧预热。这个小样路径和 MRQ 路径并不完全一致，不能用小样代替正式输出验收，也不能从后台采集耗时推断实时帧率。

## 正式输出

若报告包含 `mrq`，表示已保存一帧的相机序列和 3840×2160 PNG 输出预设。执行 `Launch.ps1 -Final` 在专用进程渲染最近一次成功运行。输出位于该轮 `Final4K`，完成状态写入 `final_result.json`。

若出现 `mrq_unavailable`，需先修复该错误；小样成功不能作为 MRQ 成功的证据。默认空间采样 1、时间采样 8、引擎预热 64、渲染预热 32，是初始设置，按实际噪点/稳定性调整。此流程当前仅做静态主视觉，不宣称已验证动画、EXR 色彩交付或性能预算。

参考：[Epic Movie Render Pipeline](https://dev.epicgames.com/documentation/unreal-engine/movie-render-pipeline-in-unreal-engine)、[Warm Up](https://dev.epicgames.com/documentation/unreal-engine/setting-up-pre-roll)。
