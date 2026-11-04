# 城市雨天天气系统

雨跟随相机、湿脚印、昼夜切换，以及地面涟漪烘焙和性能对照工具。

关键文件：`Source/StormfallFollowViewComponent.*`、`Source/StormfallWetFootprints.*`、`Source/StormfallLightingLibrary.*`、`Tools/R02/ripple_flipbook.hlsl`、`Tools/R02/ab_ripple.py`；说明见 `Docs/R02_Downtown_Rain_CN.md`。

城市雨天：地面涟漪 GPU 2.16 → 0.34 ms（RTX 4060 Laptop，1920×1080，Development 独立进程，ABAB 交替实测）；静态指令 6943 → 204。

演示视频：待补 B 站链接

本目录为代码与文档摘录，路径引用以原 Stormfall 工程为准，不能单独打开为 UE 工程。
