# Agent Skill Manager

A zero-dependency visual dashboard for managing your agent skills.

可视化面板，轻松管理电脑本地的 Agent Skills。

![Retro File Manager UI](https://img.shields.io/badge/UI-Retro_File_Manager-d8d0c4?style=flat-square) ![Python 3.6+](https://img.shields.io/badge/Python-3.6%2B-3776ab?style=flat-square) ![No Dependencies](https://img.shields.io/badge/Dependencies-None-5a8a4f?style=flat-square) ![License MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

## Features

- **Single file, zero dependencies** — Just Python, no `pip install` needed
- **Retro file manager UI** — Clean, nostalgic dashboard in your browser
- **Search & filter** — Find skills instantly by name or description
- **Category sidebar** — Browse by type: Dev, Product, Business, Team, Career, Tools, Thinking
- **Click to open** — Open any skill folder in Finder / Explorer / Files
- **Delete skills** — Remove unwanted skills directly from the UI
- **Bilingual** — English & Chinese UI, auto-detected from system locale
- **Cross-platform** — macOS, Linux, Windows

## Quick Start

### macOS / Linux

```bash
curl -O https://raw.githubusercontent.com/xinzechao/claude-skill-manager/main/app.py
python3 app.py
```

### Windows (PowerShell)

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/xinzechao/claude-skill-manager/main/app.py" -OutFile app.py
python app.py
```

That's it. Single file, your browser opens automatically.

> **Tip:** On some systems `python3` is called `python` — use whichever works for you.

### Other ways to install

<details>
<summary>Git clone (all platforms)</summary>

```bash
git clone https://github.com/xinzechao/claude-skill-manager.git
cd claude-skill-manager
python3 app.py        # macOS / Linux
python app.py         # Windows
```

</details>

<details>
<summary>Clone to a custom folder</summary>

```bash
# macOS / Linux
git clone https://github.com/xinzechao/claude-skill-manager.git ~/my-tools/skill-manager
python3 ~/my-tools/skill-manager/app.py

# Windows (PowerShell)
git clone https://github.com/xinzechao/claude-skill-manager.git $HOME\my-tools\skill-manager
python $HOME\my-tools\skill-manager\app.py
```

</details>

<details>
<summary>Download the file manually</summary>

It's a single file — you can also download `app.py` from the GitHub page and put it anywhere you like. Then run:

```bash
python3 /path/to/app.py       # macOS / Linux
python C:\path\to\app.py      # Windows
```

</details>

## Usage

```bash
python3 app.py                 # Start with defaults (auto language, auto port)
python3 app.py --port 9000     # Use a specific port
python3 app.py --lang en       # Force English UI
python3 app.py --lang zh       # Force Chinese UI
python3 app.py --no-open       # Don't auto-open browser
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `/` | Focus search box |
| `Esc` | Close dialogs |

## How It Works

The dashboard scans these directories for agent skills:

- `~/.claude/skills/` — Installed skills
- `~/.claude/commands/` — Custom commands

Each skill is a folder containing a `SKILL.md` file. The manager reads these to display skill metadata.

## Requirements

- Python 3.6+
- No external dependencies

## License

[MIT](LICENSE)
