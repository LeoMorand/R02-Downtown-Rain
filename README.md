# 技术美术作品集 · 代码与文档

UE 5.8 / Stormfall 中的本人编写部分。

## [城市雨天天气系统](01_CityRain/)

雨跟随相机、湿脚印、昼夜切换，以及地面涟漪烘焙和性能对照工具。

城市雨天：地面涟漪 GPU 2.16 → 0.34 ms（RTX 4060 Laptop，1920×1080，Development 独立进程，ABAB 交替实测）；静态指令 6943 → 204。

演示视频：待补 B 站链接

## [实时泥浆模拟（Niagara Grid2D）](02_MudSimulation/)

泥浆模拟 Shader、运行时与编辑器插件，以及研究和验证脚本。

泥浆：流动细节 GPU 增量约 0.1 ms（RTX 4060 Laptop，1280×720，D3D12 SM6，8 轮对照）。

演示视频：待补 B 站链接

## [雨中衬衫湿润系统](03_ShirtWetness/)

骨骼锚点湿度场、湿润材质 Shader、衣料工具与自动化测试源码。

衬衫：12 个骨骼锚点湿度场；9 项原生自动化测试通过；衣料代理约 20 ms → 约 1.4 ms / 人物（编辑器 Chaos 求解读回）。

演示视频：待补 B 站链接

## [灯光与 Lookdev 工具](04_LightingLookdev/)

Lighting Presets 灯光预设、Hiss 后处理插件与渲染流程工具和说明。

灯光工具：Lighting Presets 22 项自动化测试；Hiss 后处理在独立测试场景 RTX 4060 Laptop 1080p 下 0.38 ms（目标场景未测）。

演示视频：待补 B 站链接

## 目录

| 目录 | 内容 |
|---|---|
| [01_CityRain/](01_CityRain/) | 城市雨天天气系统 |
| [02_MudSimulation/](02_MudSimulation/) | 实时泥浆模拟（Niagara Grid2D） |
| [03_ShirtWetness/](03_ShirtWetness/) | 雨中衬衫湿润系统 |
| [04_LightingLookdev/](04_LightingLookdev/) | 灯光与 Lookdev 工具 |
| [Docs/](Docs/) | 技术文档 PDF |

## 分工 / AI 辅助说明

**分工**：场景（Downtown_West）、天气包、衬衫与 Manny 模型为第三方资产，不随仓库分发；泥浆参考 FluidNinja Live 的效果与算法重建。仓库内的系统代码、Shader、工具脚本与文档为本人编写。本仓库只含代码与文档，不能单独打开为 UE 工程。

**AI 辅助**：部分代码借助 Claude（Anthropic，Claude Code）与 OpenAI Codex 起草与排错；方案取舍与全部验证（编译、引擎内读回、GPU 交替实测、数值对比）由本人完成。

联系：781076011@qq.com
