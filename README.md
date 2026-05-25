# 🎵 Moe Music Studio

**萌系音乐管理播放器** — 一款 Python 桌面应用，集音乐库管理、播放与格式转换于一体。

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ 功能特色

| 功能 | 说明 |
|------|------|
| 🗂️ **音乐库管理** | 基于 SQLite，支持扫描目录并导入 50+ 种音频格式 |
| ▶️ **音频播放** | 集成 pygame 引擎，流畅播放主流音频格式 |
| 🏷️ **标签编辑** | 直接修改音频文件的元数据标签 |
| 📋 **播放列表** | 创建与管理自定义播放列表 |
| 🔄 **格式转换** | 调用 audio-converter 工具，轻松转换音频格式 |
| 🎨 **三款主题** | 萌系粉、深色、浅色，随心切换 |

## 🚀 快速开始

### 前置条件

- Python 3.10+
- **ffmpeg** 需添加到系统 PATH（格式转换功能需要）

### 安装与运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动应用
python main.py
```

## 📦 依赖说明

- **pygame** — 音频播放引擎
- **tkinterdnd2** — 拖拽支持（可选，用于 GUI 拖放文件）

## 🧩 支持的音频格式

50+ 种格式，包括但不限于：`mp3`, `flac`, `wav`, `ogg`, `aac`, `wma`, `m4a`, `ape`, `opus`, `aiff`, `au`, `mid`, `midi`, `voc`, `vox`, `raw`, `dwd`, `smp`, `sds`, `snd`, `sln`, `sln16`, `sln32`, `vox`, `gsm`, `g72x`, `ima`, `oki`, `mpeg`, `mpc`, `mp+`, `mpp`, `ofr`, `ofs`, `tta`, `tak`, `wv`, `xm`, `mod`, `it`, `s3m`, `mtm`, `umx`, `stm`, `med`, `far`, `669`, `amf`, `dsm`, `mdl`, `okt`, `ptm`, `ult`, `dmf`, `dbm`, `digi`, `imf`, `j2b`。

## 🖼️ 截图

> 待补充

## ⚙️ 技术栈

- **UI 框架**: Tkinter
- **数据库**: SQLite
- **音频播放**: pygame
- **格式转换**: audio-converter + ffmpeg
- **拖拽支持**: tkinterdnd2

## 🤝 贡献

欢迎提交 Issue 或 Pull Request！在开始之前请先阅读项目规范。

## 📄 许可证

[MIT](LICENSE)
