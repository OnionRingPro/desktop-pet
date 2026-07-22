# Desktop Pet / 桌面桌宠

A lightweight, transparent desktop companion for **macOS**, built with Python and PySide6.  
基于 Python 与 PySide6 的 **macOS** 轻量级透明桌面伴侣。

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.11-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## English

### Features

- **Transparent pet window**: frameless, always-on-top, PNG sprite animations
- **Drag**: move the pet with left-click; plays `dragging` animation while dragging
- **Double-click**: random speech bubble (`chatting-frame.png`)
- **Right-click menu**
  - Animation states: idle / happy / drink / sleep / walk / dragging
  - Display size slider (80–280 px)
  - **Ask weather**: IP-based city detection + current weather
  - **Remember this**: open todo panel (task + comment)
  - **Today's todos**: read pending tasks aloud (task text only, no comments)
  - **Quit**
- **Automatic behavior**
  - After idling, randomly switch to **happy** or **drink**
  - Enter **sleep** after prolonged inactivity; wake on click/drag or when sleep timer ends, with a random wake-up line
  - Scheduled reminders (default every 45 minutes)
- **Right-edge hide**
  - Release with the cursor on the **right screen edge** → shrink to floating ball
  - Hover the ball → pet peeks out (`peep` image)
  - Click to restore the full pet
- **Persistent todos**: stored in the user home directory; works after packaging

### Requirements

- macOS (primary target)
- Python 3.12+
- Virtual environment recommended

### Quick start

```bash
git clone <repo-url>
cd desktop-pet

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python main.py
```

### Controls

| Action | Effect |
|--------|--------|
| Left-drag | Move pet |
| Double-click | Random dialogue |
| Right-click | Context menu |
| Release at right screen edge (cursor touching edge) | Hide as floating ball |
| Hover floating ball | Peek out |
| Click ball / peek | Restore pet |

### Configuration

Edit [`config/messages.json`](config/messages.json):

| Key | Description | Default |
|-----|-------------|---------|
| `double_click_messages` | Random lines on double-click | — |
| `wake_from_sleep_messages` | Random lines when waking from sleep | — |
| `mood_idle_seconds` | Idle duration before happy/drink | `45` |
| `mood_happy_seconds` | Happy state duration (seconds) | `12` |
| `mood_drink_seconds` | Drink state duration (seconds) | `10` |
| `sleep_inactivity_seconds` | Inactivity before sleep | `100` |
| `sleep_duration_seconds` | Sleep duration before auto wake | `100` |
| `reminder_minutes` | Reminder interval (minutes) | `45` |
| `pet_display_size` | Default display size (px) | `100` |
| `weather_city` | Fallback city if IP geolocation fails | `""` |

Restart the app after changing config.

### Assets

Place transparent PNGs in each folder (played in sorted filename order):

```
assets/
├── idle/           # required
├── happy/
├── drink/
├── sleep/
├── dragging/
├── walk/           # optional
├── peep/           # right-edge peek
├── floating_ball/  # floating ball icon
├── chatting-frame.png
└── fallback.png
```

### User data (todos)

Todos are stored outside the app bundle at:

```text
~/Library/Application Support/DesktopPet/todos.json
```

Same path for dev runs and packaged `.app`. Uninstalling the app does not remove this file.

### Build (macOS)

```bash
chmod +x build_mac.sh
./build_mac.sh
```

Output: `dist/DesktopPet.app`

> `assets/` and `config/` are bundled into the app; todo data stays in Application Support.

### Project layout

```
desktop-pet/
├── main.py                 # entry point
├── config/messages.json    # default config
├── assets/                 # images & animation frames
├── build_mac.sh            # PyInstaller build script
└── src/
    ├── pet_window.py       # main window, menu, interactions
    ├── animation_manager.py
    ├── pet_scheduler.py    # auto mood / sleep / reminders
    ├── speech_bubble.py    # speech bubble
    ├── edge_sphere.py      # right-edge floating ball & peep
    ├── weather_service.py  # weather lookup
    ├── todo_panel.py       # todo panel
    ├── todo_storage.py     # todo read/write
    ├── app_paths.py        # user data paths
    └── macos_window.py     # macOS window visibility
```

### License

[MIT License](LICENSE)

---

## 中文

### 功能

- **透明桌宠窗口**：无边框、置顶，支持 PNG 序列帧动画
- **拖动**：左键按住拖动；拖动时有 `dragging` 动画
- **双击**：随机显示对话气泡（`chatting-frame.png` 对话框）
- **右键菜单**
  - 切换动画状态：待机 / 开心 / 喝水 / 睡觉 / 行走 / 拖动
  - 调整显示大小（80–280 px）
  - **问天气**：自动 IP 定位城市，查询当前天气
  - **帮我记一下**：打开待办面板（待办 + 备注）
  - **今日待办**：气泡朗读未完成条目（不含备注）
  - **退出**
- **自动行为**
  - 待机一段时间后，随机进入「开心」或「喝水」
  - 长时间无互动进入「睡觉」；点击/拖动或睡够时间后醒来，并随机说一句唤醒台词
  - 定时提醒（默认 45 分钟随机一句对话）
- **右边缘隐藏**
  - 拖动时鼠标贴到屏幕**右边缘**松手 → 缩为悬浮球
  - 鼠标移到悬浮球上 → 桌宠探头（`peep` 动画）
  - 点击恢复为正常桌宠
- **数据持久化**：待办保存在用户目录，打包后同样有效

### 环境要求

- macOS（主要开发与测试平台）
- Python 3.12+
- 建议使用虚拟环境

### 快速开始

```bash
git clone <repo-url>
cd desktop-pet

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python main.py
```

### 操作说明

| 操作 | 效果 |
|------|------|
| 左键拖动 | 移动桌宠 |
| 左键双击 | 随机对话 |
| 右键 | 打开菜单 |
| 拖到屏幕右缘（鼠标贴边）松手 | 隐藏为悬浮球 |
| 悬浮球上 hover | 探头 |
| 点击悬浮球 / 探头 | 恢复桌宠 |

### 配置文件

编辑 [`config/messages.json`](config/messages.json)：

| 字段 | 说明 | 默认 |
|------|------|------|
| `double_click_messages` | 双击随机对话列表 | — |
| `wake_from_sleep_messages` | 从睡觉醒来时的随机台词 | — |
| `mood_idle_seconds` | 待机多久后随机开心/喝水 | `45` |
| `mood_happy_seconds` | 「开心」持续秒数 | `12` |
| `mood_drink_seconds` | 「喝水」持续秒数 | `10` |
| `sleep_inactivity_seconds` | 无互动多久后睡觉 | `100` |
| `sleep_duration_seconds` | 睡觉多久后自动醒来 | `100` |
| `reminder_minutes` | 定时提醒间隔（分钟） | `45` |
| `pet_display_size` | 默认显示大小（px） | `100` |
| `weather_city` | 天气备用城市（IP 定位失败时用） | `""` |

修改配置后需**重启**桌宠生效。

### 资源文件

将透明背景 PNG 放入对应文件夹（按文件名排序播放）：

```
assets/
├── idle/           # 待机（必需，至少一帧）
├── happy/          # 开心
├── drink/          # 喝水
├── sleep/          # 睡觉
├── dragging/       # 拖动
├── walk/           # 行走（可选，有素材才显示菜单项）
├── peep/           # 右边缘探头
├── floating_ball/  # 悬浮球图标
├── chatting-frame.png
└── fallback.png    # 无动画时的备用图
```

### 用户数据（待办）

待办**不**写在 app 包内，而是保存在：

```text
~/Library/Application Support/DesktopPet/todos.json
```

开发模式与打包后的 `.app` 共用同一路径，卸载应用不会自动删除该文件。

### 打包（macOS）

```bash
chmod +x build_mac.sh
./build_mac.sh
```

产物：`dist/DesktopPet.app`

> `assets/` 与 `config/` 会打入 app；待办数据仍在 Application Support。

### 项目结构

```
desktop-pet/
├── main.py                 # 入口
├── config/messages.json    # 默认配置
├── assets/                 # 图片与动画帧
├── build_mac.sh            # PyInstaller 打包脚本
└── src/
    ├── pet_window.py       # 主窗口、菜单、交互
    ├── animation_manager.py
    ├── pet_scheduler.py    # 自动心情 / 睡觉 / 提醒
    ├── speech_bubble.py    # 对话气泡
    ├── edge_sphere.py      # 右边缘悬浮球 & peep
    ├── weather_service.py  # 天气查询
    ├── todo_panel.py       # 待办面板
    ├── todo_storage.py     # 待办读写
    ├── app_paths.py        # 用户数据路径
    └── macos_window.py     # macOS 窗口可见性
```

### 许可证

[MIT License](LICENSE)
