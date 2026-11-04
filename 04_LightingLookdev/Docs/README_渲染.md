# Stormfall.Hiss 渲染说明

Hiss 是 Tonemap 后的屏幕空间后处理，读取 SceneColor 和 SceneDepth，输出到后处理目标。参数通过快照跨线程传递；强度为 0 时不注册 pass。HISS_Volume 在已保存场景中默认关闭，CR_Day_Hiss 是可选预设。

01 / 06 两机位开关对照位于 `../images/`，管线示意为 `pipeline.svg`。真实 GPU trace `../../hiss/merge/M2_gpu.utrace` 经 Unreal Insights 导出，包含 GPU 轨道 `Stormfall.Hiss` 事件；事件列表和耗时见同目录 `M2_timers.tsv`、`M2_events.tsv`。轨道选中事件的截图、RenderDoc 的事件及输入输出截图未完成。

HissHost 简单测试场景曾记录 0.382 ms；这不是 Stormfall 目标场景性能。1920×1080 的 LP_Hero_01 与 LP_Hero_06 各三次有效 ProfileGPU、整帧 GPU 时间均未取得：捕获只得到 Slate 或空帧，因此 `perf.json` 使用 null，保留未测状态。效果依赖深度和屏幕空间数据，性能会随场景、分辨率和硬件变化。
