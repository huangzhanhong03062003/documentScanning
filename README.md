# Windows 文件扫描工具

包含两个版本：

- `file_scanner_cli.py`：命令行版
- `file_scanner_gui.py`：`tkinter` 图形界面版
- `start_cli.bat`：双击启动命令行版
- `start_gui.bat`：双击启动 GUI 版

## 功能

- 自动识别 Windows 所有可用磁盘
- 用户选择磁盘后开始扫描
- 扫描全部文件并导出 CSV
- 输出文件名、大小、扩展名、完整路径
- 忽略无权限目录，不因报错中断
- 扫描过程中提供进度提示
- 按文件大小维护 Top100 最大文件列表
- 支持从 Top100 列表中选择文件进行清理
- 适配大文件系统：扫描明细流式写入 CSV，只在内存中保留 Top100

## 启动方式

### 双击启动

- 双击 `start_gui.bat`：打开图形界面版
- 双击 `start_cli.bat`：打开命令行版

## 清理功能

- 命令行版：扫描完成后，可按编号选择 Top100 文件并删除
- GUI 版：扫描完成后，可在列表中多选文件，点击 `Delete Selected`
- 删除为永久删除，不会自动移入回收站

### 命令行启动

```powershell
python file_scanner_cli.py
python file_scanner_gui.py
```

## 输出位置

程序会在当前目录下自动创建 `outputs` 文件夹，并生成：

- `scan_磁盘号_时间戳.csv`：全部文件明细
- `largest_100_磁盘号_时间戳.csv`：最大文件 Top100
