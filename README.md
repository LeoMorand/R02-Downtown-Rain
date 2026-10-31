# R02 Downtown Rain · 源码包

UE 5.8 项目 Stormfall 中 R02 关卡的**本人编写部分**。场景美术（Downtown_West）和天气包是第三方资产，按授权不随包分发；本包只含代码、Shader、工具和文档，可直接阅读，不能单独打开为 UE 工程。

完整说明、性能数据与测量条件见 [Docs/R02_Downtown_Rain_CN.md](Docs/R02_Downtown_Rain_CN.md)。

## 目录

| 路径 | 内容 |
|---|---|
| `Source/` | C++：雨跟随相机 `StormfallFollowViewComponent`、湿脚印 `StormfallWetFootprints`、昼夜切换 `StormfallLightingLibrary` |
| `Tools/R02/*.hlsl` | 涟漪 Shader：程序化（v1 原始 / v2 剔除版）、烘焙序列帧运行时 `ripple_flipbook.hlsl` |
| `Tools/R02/*.py` | 涟漪烘焙与安装、ABAB GPU 对比（`ab_ripple.py`）、离线数值回归、自动验收、展示脚本 |
| `Tools/R02/RippleBake/` | 烘焙出的涟漪序列帧贴图 |
| `Tools/WetFootprints/` | 脚印与落脚涟漪贴花 HLSL、安装脚本、Play 行走测试 |
| `Docs/` | 作品说明页与图表 |

## 关键数据

- 地面涟漪 GPU：2.16 ms → 1.00 ms（剔除）→ 0.34 ms（烘焙），ABAB 交替实测，RTX 4060 Laptop，1920×1080。
- 涟漪静态指令数：6943 → 204（DXC）。

HLSL 在 UE 材质的 Custom 节点中运行，源文件由安装脚本写入材质；项目使用 UE 原生渲染管线，没有自定义渲染 Pass。部分代码借助 LLM 编写，均经过编译、实测和数值测试验证。
