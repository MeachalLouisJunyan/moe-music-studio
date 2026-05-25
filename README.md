# ✨ 萌音工作室 · Moe Music Studio ✨

> 🎶 **本地音乐管理播放器 —— 管理、播放、转换，一站搞定** 🎶

![Python](https://img.shields.io/badge/Python-3.10+-EE82EE?logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-7B68EE?logo=sqlite&logoColor=white)
![pygame](https://img.shields.io/badge/pygame-2-FF69B4?logo=pygame&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-98FB98)

---

## 🌸 这是什么？

**萌音工作室**是一只萌萌哒本地音乐管理播放器 desu~  
用 Python 精心打造，帮你把乱糟糟的音乐库整理得井井有条！  
播放、管理、转换格式，**一键搞定**，再也不用在多个软件之间切来切去啦 (๑•̀ㅂ•́)و✧

---

## ✨ 功能特色

| | |
|---|---|
| 🗂️ **音乐库管理** | 基于 SQLite 数据库，自动扫描目录，导入 **50+** 种音频格式 |
| ▶️ **音频播放** | pygame 引擎驱动，流畅播放各种主流音频格式 |
| 🏷️ **标签编辑** | 直接修改音频文件的元数据标签，想改就改 |
| 📋 **播放列表** | 创建你的专属播放列表，随心组合 |
| 🔄 **格式转换** | 内置转换工具，轻轻一点格式就变啦 |
| 🎨 **三款主题** | 萌系粉 ✦ 暗黑系 ✦ 清新白，总有一款适合你 |
| 🖱️ **拖拽支持** | 文件直接拖进来，超方便的说~ |

---

## 🚀 安装指南

### 📥 前置条件

- Python **3.10** 或更高版本
- **ffmpeg** 要添加到系统 PATH（转换格式需要她帮忙）

### 🛠️ 安装步骤

```bash
# 第一步：安装依赖
pip install -r requirements.txt

# 第二步：启动~\\(≧▽≦)/~
python main.py
```

### 📦 依赖酱

| 名称 | 使命 |
|------|------|
| **pygame** 🎵 | 音频播放引擎，让音乐响起来！ |
| **tkinterdnd2** 🖱️ | 可选，支持文件拖拽操作 |

### 🎵 支持的音乐格式

> **50+ 种格式全兼容！** 包括但不限于：
>
> `mp3` `flac` `wav` `ogg` `aac` `wma` `m4a` `ape` `opus` `aiff` `au` `mid` `midi` `voc` `raw` `tta` `tak` `wv` `xm` `mod` `it` `s3m` …… 还有好多好多！

---

## ⚙️ 技术栈

```
🎨 UI 界面  ——  Tkinter
🗄️ 数据库  ——  SQLite
🎵 播放引擎 ——  pygame
🔄 格式转换 ——  audio-converter + ffmpeg
🖱️ 拖拽支持 ——  tkinterdnd2
```

---

## 📸 截图

> 🖼️ 截图酱正在赶来的路上……

---

## 🤝 一起来玩！

发现了 Bug？有好的想法？欢迎提 **Issue** 或 **Pull Request** 哦！  
在动手之前，记得先看看项目规范 (◕‿◕✿)

---

## 📄 许可证

本项目采用 [MIT](LICENSE) 许可证 — 随意玩耍，开心就好 ✨

---

<p align="center">
  <b>⭐ 如果觉得有用，给个星星吧！ ⭐</b><br>
  <a href="https://github.com/MeachalLouisJunyan/moe-music-studio">https://github.com/MeachalLouisJunyan/moe-music-studio</a>
</p>
