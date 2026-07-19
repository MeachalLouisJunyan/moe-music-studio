# 打包说明

正式发版不需要手动打包：**推一个 `v*` 开头的 tag**（如 `v1.0.0`），
GitHub Actions（`.github/workflows/release.yml`）会自动构建
Windows zip 和 macOS dmg 并挂到 GitHub Release 上。
想先验证打包流程，可以在 GitHub 的 Actions 页面手动触发
「Build Release」（workflow_dispatch），产物在 run 的 artifacts 里下载。

## 发版步骤

1. 改 `version.py` 里的 `__version__`
2. `git tag v1.0.0 && git push origin v1.0.0`
3. 等 Actions 跑完，去 Releases 页检查产物，编辑发布说明

## 本地手动打包（可选）

```bash
pip install -r requirements.txt pyinstaller pillow
python packaging/make_icons.py
pyinstaller packaging/moe-music.spec --noconfirm
```

产物在 `dist/JyMusic/`（macOS 还会生成 `dist/Jy Music.app`）。
要做到用户零配置，把静态编译的 `ffmpeg` 和 `ffprobe`
拷进 `dist/JyMusic/`（macOS 拷进 `Jy Music.app/Contents/MacOS/`），
程序会优先使用同目录下的 ffmpeg（见 `scanner.py` 的 `find_ffmpeg`）。

## 图标

`packaging/assets/icon.png` / `icon.ico` 由 `make_icons.py` 生成（需要 Pillow）。
macOS 的 `icon.icns` 在 CI 里用 `sips` + `iconutil` 从 png 现场生成，不入库。

## 注意事项

- **未做代码签名/公证**：macOS 用户首次打开需要右键 →「打开」，
  或执行 `xattr -cr "/Applications/Jy Music.app"`；Windows SmartScreen
  可能提示「未知发布者」，点「仍要运行」。README 下载区已写明。
- **ffmpeg 许可**：随包分发的 ffmpeg 静态版是 GPL 许可，它作为独立
  程序与本项目（MIT）聚合分发，发布说明里保留 ffmpeg 的来源链接即可。
