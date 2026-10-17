# 打包与发布说明

面向维护者：如何把源码打成可分发目录、组装发布包、上传 Release，以及这些环节踩过的坑。
普通使用请看 [README](../README.md)。

## 发布包结构

```
release/Playtime_x64/
├─ Playtime.exe          # 269 KB 启动器（免提权）
├─ Playtime_admin.exe    # 269 KB 启动器（请求管理员，弹一次 UAC）
├─ Playtime_debug.bat    # 调试启动：直接跑 Playtime\Playtime.exe 并显示退出码
├─ Playtime\             # 程序本体
│  ├─ Playtime.exe       #   PyInstaller 产物
│  └─ files\             #   运行库：Qt / Python / 插件
├─ userconfig\           # 便携数据：data.json
├─ LICENSES\             # Qt(LGPLv3) / 三款字体(OFL) 许可文本
├─ README.md
└─ 使用说明.txt
```

根目录只放两个同图标、同体积的启动器，程序本体与运行库收在 `Playtime\` 子目录里。

## 数据目录优先级

`app/storage.py` 按以下顺序决定 `data.json` 的位置：

1. 启动器传入的 `--data-dir <路径>`（发布包固定指向根目录 `userconfig\`）
2. 冻结运行时，exe 同级的 `userconfig\`（可写性探测失败则跳过）
3. `%LOCALAPPDATA%\Playtime\data.json`

首次落到新位置时，若旧位置已有 `data.json` 会自动复制过来，不会丢记录。
从源码运行（未打包）时忽略 `--data-dir`，始终用 `%LOCALAPPDATA%`，避免污染仓库。

## 打包

需要 `pyinstaller>=6.11`，脚本会自动挑选解释器（优先 `.venv\Scripts\python.exe`，否则 PATH 上的 `python`）。

```bash
build.bat                  # 目录版 -> dist\Playtime\{Playtime.exe, files\}
build.bat onefile          # 单文件 -> dist\Playtime.exe（自动请求管理员权限）
tools\build_launchers.bat  # 编译两个启动器到 release\Playtime_x64\
```

关键参数：

- `--contents-directory files`：运行库全部落到 `files\`，顶层只留一个 exe
- `--add-data "assets\fonts;assets\fonts"`：字体随包
- `--version-file version_info.txt`：exe 属性页的公司 / 产品 / 版本
- 排除未使用的 Qt 模块（WebEngine / Pdf / Quick / Qml / Charts / Multimedia / Network 等）以压缩体积

## 组装发布包

1. `build.bat` 得到 `dist\Playtime\`
2. 把整个目录复制成 `release\Playtime_x64\Playtime\`
3. `tools\build_launchers.bat` 在根目录生成 `Playtime.exe` 与 `Playtime_admin.exe`
4. 补上 `userconfig\`（含说明）、`LICENSES\`、`使用说明.txt`
5. 压缩 `release\Playtime_x64.zip`
6. 在 GitHub 新建 Release 并上传 zip

## 必做：DLL 完整性校验

这台机器上曾出现「文件大小正确、内容全是 0」的写入损坏：`qjpeg.dll` 等 27 个 Qt 插件被写成全零，
程序启动后报 `Shiboken: 不是有效的 Win32 应用程序`。构建后务必逐个检查：

```powershell
Get-ChildItem dist\Playtime\files -Recurse -File -Include *.dll,*.pyd |
  ForEach-Object {
    $fs = [IO.File]::OpenRead($_.FullName)
    $b = New-Object byte[] 2
    $null = $fs.Read($b, 0, 2)
    $fs.Close()
    if ($b[0] -ne 0x4D -or $b[1] -ne 0x5A) { "BAD: $($_.FullName)" }
  }
```

输出为空才继续；有损坏就 `build.bat` 重打（PyInstaller 偶发崩溃 0xC0000005，脚本重试即可）。

## 启动器实现

`tools/launcher.cs`（C#，约 80 行），用 Windows 自带的 .NET Framework `csc.exe` 编译，
不需要 Visual Studio：

```bat
csc /target:winexe /win32icon:assets\app.ico /out:Playtime.exe       tools\launcher.cs
csc /define:ADMIN /target:winexe /win32icon:assets\app.ico /out:Playtime_admin.exe tools\launcher.cs
```

- 普通版：清单 `asInvoker`，用 **CreateProcess** 直启 `Playtime\Playtime.exe`。
  若用 ShellExecute，未签名 exe 会先弹「打开文件 - 安全警告」
- 管理员版：`UseShellExecute = true` + `Verb = "runas"`，弹一次 UAC
- 两者都把 `--data-dir <根>\userconfig` 放在参数最前，用户参数原样追加
- 找不到 `Playtime\` 时弹提示；UAC 点「否」静默退出

启动器没有 Win32 版本资源（写入 VERSIONINFO 需要 `rc.exe`，未安装 Windows SDK），
右键属性里公司 / 版本为空，属已知差异。

## 常见问题

### 双击提示「Microsoft Defender SmartScreen 阻止了无法识别的应用启动」

exe 未做代码签名，`Get-AuthenticodeSignature` 显示 `NotSigned`。处理方式：

1. 点「更多信息 → 仍要运行」，Windows 会为该文件记住这次选择
2. 长期方案是购买代码签名证书（EV 基本立即可用，OV 需积累下载量）

> 把文件夹加进 Windows 安全中心的「排除项」只对病毒扫描有效，对 SmartScreen 无效。

### 双击只弹 `Error: Failed to create parent directory structure.` / `Could not create temporary directory!`

**单文件版**（`--onefile`）在受限令牌下建不了临时目录：PyInstaller 6.11+ 的引导程序用
`CreateDirectoryW` + 安全描述符创建 `_MEIxxxx`，普通用户令牌下该调用被系统拒绝，
引导程序直接退出。用 `--debug all` 可看到日志停在
`LOADER: attempting to create temporary application directory ...`；
连一个 Hello World 单文件程序也同样失败，与项目内容无关。提权进程不受此限制。

对策：日常用目录版（`build.bat`），它不落地解压；需要单文件时用
`build.bat onefile`，其清单写入 `requireAdministrator`，启动会弹 UAC。

### 单文件版的代价

- 每次启动弹 UAC
- **开机自启动失效**：登录时 Run 项由资源管理器非提权拉起，被 `requireAdministrator` 拦下
- 常驻进程长期持有管理员令牌，风险面更大

### 批处理里的中文乱码

`.bat` 用系统默认编码（中文 Windows 为 GBK）保存，不要存成 UTF-8；`.py` 用 UTF-8。
`version_info.txt` 必须是 UTF-8（PyInstaller 按 UTF-8 读取）。

## 统计口径

| 指标 | 算法 |
| --- | --- |
| 单游戏总时长 | `baseline_seconds` + 全部会话秒数 |
| 本周时长 | 起始时间落在本周一 00:00 至当前时刻的会话 |
| 本月活跃（天） | 本月至今出现过会话的自然日数量（去重） |
| 最长单次 | 所有会话中单次秒数的最大值 |
| 总会话数 | 全部会话条数（不随范围切换） |
| 平均单次 | 当前范围时长 ÷ 该范围会话数 |
| 每日趋势 | 最近 30 天按天汇总 |

首次运行会注入 12 款示例数据（总时长 1,284.6 小时、最长单次 6.4 小时），
其中差额记在 `baseline_seconds` 里，用于对齐示例的总时长。
