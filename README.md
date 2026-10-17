# Playtime · 游戏时长统计

Windows 桌面端游戏时长统计工具：把游戏的可执行文件登记进来，后台自动监听进程、
累计每次游玩时长，并按周 / 月 / 全部维度做统计。纯本地运行，不联网、不上传任何数据。

- 技术栈：Python 3.13 + PySide6（Qt Widgets），界面全部自绘，无 Web 组件
- 视觉：灰白亮色主题（背景 `#ECEEF2`）+ 半透明白色卡片 + 青/紫/蓝低透明度极光光晕，
  圆角 16/12/10/8，字体 Inter + JetBrains Mono + Noto Sans SC（随包携带）
- 发布包：`release\Playtime_x64\`（约 129 MB，解压即用，无需安装 Python），
  双击其中的 `Playtime.exe` 启动；同目录的 `Playtime_x64.zip` 用于分发

![游戏库](preview/01-游戏库.png)

---

## 功能

### 01 游戏库

- 顶部 KPI：**总游戏时长**、**本周时长**、**最长单次**、**本月活跃（天）**
- 游戏列表：封面色块（按名称哈希生成渐变色）+ 名称 / 总时长 / 本周 / 最近游玩 / 状态，
  按总时长倒序排列，支持按名称搜索（输入即过滤）
- 状态列显示「运行中 / 未运行」，运行中的游戏实时高亮
- 右侧「正在游玩」：当前游戏名、`HH:MM:SS` 实时计时（每秒刷新）、
  本周目标进度条（默认 40 小时，取自 `settings.week_goal_hours`）、
  「暂停记录 / 继续记录」「结束」两个按钮
- 右侧「本周时长分布」：周一至周日柱状图（单位：小时），高亮今天
- 右上「添加游戏」直接跳转到设置页的表单

### 02 统计分析

- 范围切换：**本周 / 本月 / 全部**（影响时长 KPI 与「平均单次」）
- KPI：本周（本月 / 累计）时长、总会话数、平均单次
- 「每日时长趋势」：最近 30 天每日时长柱状图，横轴标签按 `MM-DD` 抽样显示
- 「时长占比」：环形图 + 图例，取时长前 4 名游戏，其余合并为「其他」
- 右上「导出 CSV」：把全部会话记录导出为 CSV（UTF-8 BOM，Excel 可直接打开）

### 03 设置

- 「添加游戏」：游戏名称、可执行文件（可「浏览」选择 `.exe`）、进程名称。
  选择 exe 后自动从文件名填充进程名；名称留空时用 exe 文件名兜底
- 「监控设置」三个开关：**开机自启动**、**最小化到托盘**、**空闲自动暂停**
- 「数据管理」：导出 CSV、备份到本地（复制 `data.json`）、清空数据（清空前二次确认）
- 右上「保存更改」写回设置并立即生效（含写入 / 删除注册表自启动项）

![统计分析](preview/02-统计分析.png)
![设置](preview/03-设置.png)

---

## 进程监控怎么工作

监控是一个独立的后台线程（`QThread`，`app/monitor.py`），**每 3 秒**扫描一次系统进程：

1. 用 `CreateToolhelp32Snapshot` / `Process32NextW`（`ctypes` 直接调用 `kernel32`）
   枚举全部进程名，小写后与已登记游戏的 `process` 字段比对；
   快照失败或非 Windows 时退回 `psutil`。
2. 进程出现且此前不在计时 → 开启一次会话；进程消失 → 把会话写入 `data.json`
   （时长 < 5 秒的会话直接丢弃，避免误启动污染数据）。
3. 开启「空闲自动暂停」时，用 `GetLastInputInfo` 读取系统无操作秒数，
   超过 `idle_minutes`（默认 5 分钟）暂停累计，恢复输入后自动继续。
4. 主窗口每秒从监控线程读取当前累计秒数刷新「正在游玩」计时；
   退出应用时，仍未结束的会话会按当前累计时长落盘。

侧边栏底部常驻「监控运行中 · 已收录 N 款游戏」卡片；
状态栏左侧实时显示「正在追踪 N 个进程 / 等待游戏启动 / 未登记进程」。

### 窗口与托盘

- 无边框窗口（默认 1280×800，最小 1100×700），标题栏可拖动、双击最大化，
  自带最小化 / 最大化 / 关闭按钮
- 系统托盘图标：左键单击恢复窗口，右键菜单「显示窗口 / 退出」
- 开启「最小化到托盘」后，点关闭按钮只隐藏窗口并弹出提示，后台继续计时
- 自启动写入 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`（值名 `Playtime`），
  命令带 `--minimized` 参数，开机后直接静默驻留托盘

---

## 数据与统计口径

存储位置（原子写入：先写 `.tmp` 再 `os.replace`）：

- **便携优先**：启动器传入 `--data-dir <发布目录>\userconfig`，数据就写在那里面，
  整个文件夹拷走即可搬家；
- 程序目录不可写（例如放到 `Program Files`）时，自动回退到 `%LOCALAPPDATA%\Playtime\data.json`；
- 首次按新结构运行时，会把旧位置已有的 `data.json` 自动复制到 `userconfig\`，不会丢记录。
- 从源码直接运行（未打包）时忽略 `--data-dir`，仍用 `%LOCALAPPDATA%\Playtime\data.json`。

```jsonc
{
  "version": 1,
  "seeded": true,                     // 是否仍是最初注入的示例数据
  "settings": {
    "autostart": false,
    "minimize_to_tray": true,
    "idle_pause": true,
    "idle_minutes": 5,
    "week_goal_hours": 40
  },
  "games": [
    {
      "id": "…", "name": "赛博朋克 2077",
      "exe": "Cyberpunk2077.exe", "process": "Cyberpunk2077.exe",
      "cover": "",
      "baseline_seconds": 1234567,    // 历史累计基线（用于对齐示例总时长）
      "created_at": "…",
      "sessions": [
        { "id": "…", "start": "…", "end": "…", "seconds": 8640 }
      ]
    }
  ]
}
```

统计口径（`app/storage.py`）：

| 指标 | 算法 |
| --- | --- |
| 单游戏总时长 | `baseline_seconds` + 全部会话秒数 |
| 本周时长 | 起始时间落在本周一 00:00 至当前时刻之间的会话 |
| 本月活跃（天） | 本月至今出现过会话的自然日数量（去重） |
| 最长单次 | 所有会话中单次秒数的最大值 |
| 总会话数 | 全部会话条数（不随范围切换） |
| 平均单次 | 当前所选范围时长 ÷ 该范围会话数 |
| 每日趋势 | 最近 30 天，按天汇总全部游戏时长 |

**首次运行会注入 12 款游戏的示例数据**（总时长 1,284.6 小时、最长单次 6.4 小时，
与设计稿数值一致），方便直接看效果。想从零开始记录真实数据：
「设置 → 数据管理 → 清空数据」。

> 数据跟着程序目录走：换机器时把 `release\Playtime_x64\` 整个文件夹（或其中的
> `userconfig\`）复制过去即可。从源码直接运行（未打包）时，仍使用
> `%LOCALAPPDATA%\Playtime\data.json`，避免污染仓库目录。

---

## 从源码运行

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

已在 Python 3.13.14 + PySide6 6.12.0 下验证可正常导入与启动。
程序 **仅支持 Windows**：`winreg`、`user32.GetLastInputInfo` 等为 Windows 专属 API。

## 发布形态

发布包按 LunaTranslator 的方式组织：**根目录只放两个同款小启动器**，真正的程序在
同名子文件夹里，运行库、数据、许可各自独立成目录。

```
release/Playtime_x64/
├─ Playtime.exe          # 269 KB 启动器（免提权）
├─ Playtime_admin.exe    # 269 KB 启动器（请求管理员，弹一次 UAC）
├─ Playtime_debug.bat    # 调试启动：直接跑 Playtime\Playtime.exe 并显示退出码
├─ Playtime\             # 程序本体
│  ├─ Playtime.exe       #   PyInstaller 产物（真正的程序）
│  └─ files\             #   运行库：Qt / Python / 插件
├─ userconfig\           # 便携数据：data.json，跟着文件夹走
├─ LICENSES\             # Qt(LGPLv3) / 三款字体(OFL) 许可文本
├─ README.md
└─ 使用说明.txt
```

启动器做的事很简单：把 `--data-dir <发布目录>\userconfig` 和用户参数一起传给
`Playtime\Playtime.exe`，所以数据始终落在根目录的 `userconfig\`，程序本体却被收进子文件夹
——顶层看上去就是两个同图标、同体积的 exe（对应 LunaTranslator 的 411 KB 双启动器）。

`release/Playtime_x64.zip`（约 53 MB）是可直接分发的压缩包。
分发到别的机器时，注意 Windows 可能对未签名 exe 弹 SmartScreen（见「常见问题」）。

## 打包成 exe

```bash
.venv\Scripts\pyinstaller --version   # 需先装 pyinstaller（>=6.11）
build.bat            # 目录版：dist\Playtime\{Playtime.exe, files\}（默认，发布用）
build.bat onefile    # 单文件：dist\Playtime.exe（自动请求管理员权限，可选）
```

打包会排除 QtWebEngine / QtPdf / QtQuick / QtQml / QtCharts / QtMultimedia / QtNetwork
等未使用的 Qt 模块以压缩体积；字体通过 `--add-data "assets\fonts;assets\fonts"` 打进
`files\` 内；exe 的版本资源由 `version_info.txt` 提供（`--version-file`）；
`--contents-directory files` 让运行库全部落在 `files\`，顶层只留一个 exe。

`build.bat` 会自动挑选解释器：优先用项目内 `.venv\Scripts\python.exe`，否则用 PATH 上的
`python`；找不到 PyInstaller 时会直接提示安装命令。

| 产物 | 大小 | 权限 | 说明 |
| --- | --- | --- | --- |
| `dist\Playtime\`（`build.bat`） | 2 MB + 128 MB 运行库 | 普通用户 | **默认产物**，即发布包内容，不落地解压 |
| `dist\Playtime.exe`（`build.bat onefile`） | 约 54 MB | **管理员** | 可选，单个 exe 拿走就用；受临时目录限制（见下） |

发布包的组装：先 `build.bat` 得到 `dist\Playtime\`，把整个目录复制成
`release\Playtime_x64\Playtime\`，再 `tools\build_launchers.bat` 在根目录生成两个启动器，
最后补 `userconfig\`、`LICENSES\`、`使用说明.txt` 并压缩成 zip。

**打包后务必校验 DLL 完整性**：这台机器上曾出现「文件大小正确、内容全是 0」的写入损坏
（`qjpeg.dll` 等 Qt 插件被写成全零，程序报 `Shiboken: 不是有效的 Win32 应用程序`）。
构建后逐个检查 `files\` 下 `.dll`/`.pyd` 的前两字节是否为 `MZ`，有损坏就重打：

```powershell
Get-ChildItem dist\Playtime\files -Recurse -File -Include *.dll,*.pyd |
  ForEach-Object {
    $fs=[IO.File]::OpenRead($_.FullName); $b=New-Object byte[] 2; $null=$fs.Read($b,0,2); $fs.Close()
    if ($b[0] -ne 0x4D -or $b[1] -ne 0x5A) { "BAD: $($_.FullName)" }
  }
```

> **为什么保留一个需要管理员权限的单文件版**：PyInstaller 6.11+ 的单文件引导程序会用
> `CreateDirectoryW` + 安全描述符在临时目录建 `_MEIxxxx`，在受限（普通用户）令牌下该调用
> 被系统拒绝，导致启动即失败（详见「常见问题」）。提权令牌不受此限制，所以单文件版的清单
> 里写入 `requireAdministrator`。目录版没有解压步骤，完全不受影响，是日常使用的首选。

## 重新生成预览图

`_render.py` 用 Qt 的 offscreen 平台渲染三个界面到 `preview\`，不需要打开窗口：

```bash
.venv\Scripts\python _render.py
```

注意：它构造的是真实主窗口，读取的是本机 `data.json`，因此预览图内容会跟着当前数据变化。

---

## 目录结构

```
playtime/
├─ main.py                # 入口：无边框主窗口、导航、托盘、开机自启、--minimized
├─ build.bat              # PyInstaller 打包脚本（默认目录版，可 onefile）
├─ version_info.txt       # exe 版本资源（公司 / 产品 / 版本号）
├─ _render.py             # offscreen 渲染三个界面到 preview/
├─ tools/
│  ├─ launcher.cs         # 启动器源码（编译出普通 / 提权两个 exe）
│  └─ build_launchers.bat # 用系统自带 csc 编译，无需 VS
├─ requirements.txt
├─ README.md
├─ app/
│  ├─ theme.py            # 设计令牌：配色 / 圆角 / 间距 / 尺寸 / 字体 / 全局样式表
│  ├─ icons.py            # 24×24 网格描边图标（QPainterPath 自绘）
│  ├─ charts.py           # 极光背景、柱状图、环形图、进度条、状态点
│  ├─ widgets.py          # 卡片、KPI、导航项、开关、窗口按钮、设置行
│  ├─ shell.py            # 标题栏、侧边栏、状态栏
│  ├─ screens.py          # 三个界面：游戏库 / 统计分析 / 设置
│  ├─ storage.py          # JSON 读写、统计计算、CSV 导出、示例数据
│  └─ monitor.py          # 进程监控线程、Toolhelp32 枚举、空闲检测
├─ assets/
│  ├─ app.ico             # 应用图标
│  └─ fonts/              # Inter、JetBrains Mono、Noto Sans SC（中文）
├─ preview/               # 三个界面的渲染预览图
├─ dist/Playtime/          # 目录版构建产物（免提权，files/ 为运行库）
├─ release/
│  ├─ Playtime_x64/       # 发布包
│  │  ├─ Playtime.exe         # 269 KB 启动器（免提权）
│  │  ├─ Playtime_admin.exe   # 269 KB 启动器（请求管理员）
│  │  ├─ Playtime_debug.bat   # 调试启动器
│  │  ├─ Playtime/            # 程序本体
│  │  │  ├─ Playtime.exe      #   PyInstaller 产物
│  │  │  └─ files/            #   运行库（Qt / Python / 插件）
│  │  ├─ userconfig/      #   便携数据 data.json 放这里
│  │  ├─ LICENSES/        #   LGPLv3 + OFL 许可文本
│  │  └─ 使用说明.txt
│  └─ Playtime_x64.zip    # 可直接分发的压缩包（约 53 MB）
└─ __pycache__/、app/__pycache__/   # 运行缓存，可随时删除
```

## 已知限制

- **游戏只能新增，不能在界面里编辑或删除单款游戏**；目前唯一的清理方式是「清空数据」。
- 「本周目标 40 小时」和「空闲 5 分钟」在界面上是固定文案，
  实际取值来自 `data.json` 的 `week_goal_hours` / `idle_minutes`，只能手改 JSON。
- 「每日时长趋势」固定显示最近 30 天，不随本周 / 本月 / 全部切换；
  切换范围只影响时长 KPI 与「平均单次」。「总会话数」始终是累计值。
- 监控按**进程名**匹配，不支持通配或启动器链路
  （例如通过 Steam / Epic 启动、进程名与 exe 名不一致的游戏，需要手工填对进程名）。
- 同一时刻只会展示一个「正在游玩」游戏；多个游戏同时运行时，计时卡片显示其中之一。
- 「结束」按钮只结束当前会话：若进程仍在运行，下一轮扫描（3 秒内）会重新开始计时。
- 程序被强制结束或直接关机时，进行中的会话可能来不及落盘（最多丢失一次未结束的会话）。
- 单文件版（`build.bat onefile` 生成）需要管理员权限（见「常见问题」），与「开机自启动」冲突；
  要开机自启请用目录版。

## 常见问题

### Windows 11 双击 exe 提示「Microsoft Defender SmartScreen 阻止了无法识别的应用启动」

这是打包产物缺少数字签名导致的，**不是文件损坏**：

- `release\Playtime_x64\Playtime.exe` 由 PyInstaller 生成，
  `Get-AuthenticodeSignature` 显示 `NotSigned`；当前产物已写入版本资源
  （`Playtime 游戏时长统计 / 1.0.0`），但没有可信发布者签名，SmartScreen 仍按
  「无法识别的应用」处理；
- 换个路径、重新打包或换台机器都会重新判定（本例中从 C 盘移动到 E 盘后触发了提示）。

两种处理方式，任选其一：

1. 在拦截对话框点「更多信息 → 仍要运行」，Windows 会为该文件记住这次选择
   （之后换路径或重新打包仍可能再问一次）；
2. 长期方案：给 exe 做代码签名（EV 证书基本立即可用，OV 证书需要先积累下载量）。

> 也可以用命令行拉起程序绕过这项检查，例如
> `powershell -c "Start-Process 'Playtime.exe'"`（在发布包目录内执行）。

> 把文件夹加入 Windows 安全中心的「排除项」只对病毒扫描有效，**对 SmartScreen 无效**；
> 关闭「应用和文件检查」能去掉弹窗，但会降低整机防护，不建议。

### 双击后只弹一个标题为 Error 的框：`Failed to create parent directory structure.` / `Could not create temporary directory!`

这是**单文件版**（`--onefile`）启动时解压失败，不是代码问题。已定位到具体机制：

- PyInstaller 6.11+ 的单文件引导程序用 `CreateDirectoryW` + 安全描述符在临时目录建
  `_MEIxxxx`；在普通用户（受限）令牌下这个调用被系统拒绝，引导程序直接退出；
- `--debug all` 的日志停在
  `LOADER: attempting to create temporary application directory ...` 之后；
- 用同一个 PyInstaller 打一个 Hello World 单文件程序，**同样失败**，与项目内容无关；
- 提权进程不受该限制——这就是「以管理员身份运行能打开」的原因。

对应措施：

1. 需要单文件时用 `build.bat onefile` 重新打包：它的清单里写入 `requireAdministrator`，
   双击 → UAC 点「是」即可运行；
2. 不想每次提权，就用目录版 `release\Playtime_x64\Playtime.exe`（无解压步骤，普通权限即可）；
   需要管理员权限的单个操作，用同目录的 `Playtime_admin.exe`；
3. 换一台没有该限制的机器，或用其它打包工具，`--onefile` 仍可照常工作。

### 发布包里那两个 exe 是干什么的

对应 LunaTranslator 的 `LunaTranslator.exe` + `LunaTranslator_admin.exe`：**两个都是启动器**，
真正程序在 `Playtime\` 子文件夹里。

- 每个约 269 KB，C# 编写，和主程序共用 `assets\app.ico` 图标，所以看着是一对；
- 普通版清单为 `asInvoker`，用 CreateProcess 直启 `Playtime\Playtime.exe`，
  不经过外壳，因此**不会弹「打开文件 - 安全警告」**；
- 管理员版以 `Verb="runas"` 走外壳提权，启动时弹一次 UAC；
- 两者都把 `--data-dir <发布目录>\userconfig` 放在参数最前面，用户参数原样追加
  （例如 `Playtime_admin.exe --minimized`），所以数据始终在根目录的 `userconfig\`；
- 找不到 `Playtime\` 时弹提示；UAC 点「否」时静默退出，不留下错误弹窗。

编译方式（无需 Visual Studio，只用系统自带的 .NET Framework 编译器）：

```bash
tools\build_launchers.bat        # 一次编出两个 exe，/win32icon:assets\app.ico
tools\launcher.cs                # 源码，约 80 行，/#if ADMIN 区分提权版
```

启动器没有 Win32 版本资源（`csc` 需要 `rc.exe` 才能写入 VERSIONINFO，本机未装 Windows SDK），
所以右键属性里公司/版本为空；`Playtime\Playtime.exe` 的版本信息不受影响。

### 单文件版为什么要管理员权限，有什么代价

单文件版提权是上面那条系统限制的**规避手段**，不是程序功能需要——枚举进程
（Toolhelp32）、读写 `%LOCALAPPDATA%\Playtime\data.json`、写 `HKCU` 自启动项，
普通用户权限都够。代价是：

- 每次启动都弹 UAC；
- **开机自启动会失效**：登录时 Run 项由资源管理器以非提权方式拉起，遇到
  `requireAdministrator` 会被 UAC 拦下，无法静默启动——需要自启动时请改用目录版；
- 常驻后台的进程长期持有管理员令牌，加载字体、Qt 插件时的风险面更大；
- 受限账户或关闭 UAC 的环境可能直接起不来。

日常使用建议：直接双击 `release\Playtime_x64\Playtime.exe`（免提权）；
只在需要「单个 exe 拿走就用」时，才用 `build.bat onefile` 生成的单文件版并接受一次 UAC。

## 依赖

- `PySide6>=6.6`（运行必需）
- `pyinstaller>=6.0`（仅打包需要）
- `psutil>=5.9`（仅非 Windows 平台的进程枚举兜底，Windows 上走原生 Toolhelp32，不使用）
