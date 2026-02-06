#!/usr/bin/env python3
"""
Agent Skill Manager — A zero-dependency visual dashboard for managing agent skills.

Usage:
    python app.py                  # Auto-detect language, auto-find port
    python app.py --port 9000      # Use specific port
    python app.py --lang en        # Force English UI
    python app.py --lang zh        # Force Chinese UI
    python app.py --no-open        # Don't auto-open browser

Opens http://localhost:<port> in your browser automatically.
Press Ctrl+C to stop.
"""

import os
import sys
import json
import shutil
import socket
import locale
import webbrowser
import threading
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import subprocess

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

SCAN_DIRS = [
    (Path.home() / ".claude" / "skills", "skills"),
    (Path.home() / ".claude" / "commands", "commands"),
]

AGENTS_SKILLS_DIR = Path.home() / ".agents" / "skills"

# Module-level language setting (set once at startup)
_current_lang = "en"

# ──────────────────────────────────────────────
# i18n — Bilingual support
# ──────────────────────────────────────────────

KIND_ORDER = ["dev", "product", "business", "team", "career", "tools", "thinking", "other"]

KIND_LABELS = {
    "zh": {
        "dev": "开发", "product": "产品", "business": "商业", "team": "团队",
        "career": "职业", "tools": "工具", "thinking": "思维", "other": "其他",
    },
    "en": {
        "dev": "Dev", "product": "Product", "business": "Business", "team": "Team",
        "career": "Career", "tools": "Tools", "thinking": "Thinking", "other": "Other",
    },
}

UI_STRINGS = {
    "zh": {
        "allSkills": "全部技能",
        "categories": "分类",
        "deleteConfirm": "确定删除",
        "deleteText": "此操作不可撤销。技能文件夹将被永久删除。",
        "cancel": "取消",
        "delete": "删除",
        "deleting": "删除中...",
        "deleted": "技能已删除",
        "noMatch": "没有匹配的技能。",
        "items": "项",
        "kinds": "类",
        "ready": "就绪",
        "scanning": "扫描中...",
        "loading": "加载中...",
        "funText": "你关不掉我的！<br>我已经住在你的浏览器里了。",
        "funOk": "好吧",
        "openFailed": "打开失败",
        "loadFailed": "加载失败",
        "error": "错误",
    },
    "en": {
        "allSkills": "All Skills",
        "categories": "Categories",
        "deleteConfirm": "Delete",
        "deleteText": "This action cannot be undone. The skill folder will be permanently removed.",
        "cancel": "Cancel",
        "delete": "Delete",
        "deleting": "Deleting...",
        "deleted": "Skill deleted",
        "noMatch": "No skills match your search.",
        "items": "items",
        "kinds": "kinds",
        "ready": "Ready",
        "scanning": "Scanning...",
        "loading": "Loading...",
        "funText": "Nice try! You can't close me.<br>I live in your browser now.",
        "funOk": "OK, fine",
        "openFailed": "Failed to open",
        "loadFailed": "Failed to load",
        "error": "Error",
    },
}

# ──────────────────────────────────────────────
# Chinese descriptions — used when lang=zh
# ──────────────────────────────────────────────

SKILL_DESCRIPTIONS_ZH = {
    # ── Cos 系列 ──
    "cos-archive": "Cos档案馆模式，回溯历史与检索过往",
    "cos-arena": "Cos竞技场模式，辩论与压力测试想法",
    "cos-garden": "Cos花园模式，发散思考与头脑风暴",
    "cos-memory": "Cos记忆管理，更新工作记忆与记录事件",
    "cos-mirror": "Cos镜室模式，自我反思与日终复盘",
    "cos-workshop": "Cos工坊模式，落地执行与产出成果",
    # ── AI / 技术 ──
    "ai-evals": "创建和运行AI评估，衡量LLM产品质量",
    "ai-product-strategy": "定义AI产品策略，决定何处应用AI",
    "building-with-llms": "构建LLM应用，编写提示词与系统设计",
    "vibe-coding": "使用AI辅助编程与代码生成",
    "evaluating-new-technology": "评估新兴技术与工具选型",
    # ── 开发工作流 ──
    "brainstorming": "创意发散与头脑风暴工具",
    "dispatching-parallel-agents": "分派并行子代理处理独立任务",
    "executing-plans": "按计划逐步执行实施任务",
    "finishing-a-development-branch": "完成开发分支的集成与合并",
    "receiving-code-review": "接收代码审查反馈并改进",
    "requesting-code-review": "发起代码审查与质量验证",
    "subagent-driven-development": "子代理驱动的并行开发模式",
    "systematic-debugging": "系统化调试与问题排查",
    "test-driven-development": "测试驱动开发流程",
    "using-git-worktrees": "Git工作树隔离开发环境",
    "using-superpowers": "技能发现与使用入口",
    "verification-before-completion": "完成前的验证与检查",
    "writing-plans": "编写多步骤实施计划",
    "writing-skills": "创建和编辑Agent技能文档",
    # ── 技能管理 ──
    "skill-creator": "创建新的Agent技能",
    "find-skills": "发现和安装Agent技能",
    # ── 产品管理 ──
    "analyzing-user-feedback": "综合分析用户反馈与NPS数据",
    "behavioral-product-design": "应用行为科学原理设计产品",
    "coaching-pms": "培养和辅导产品经理成长",
    "competitive-analysis": "竞争对手分析与市场定位",
    "conducting-user-interviews": "用户访谈与定性研究",
    "defining-product-vision": "定义产品愿景与战略方向",
    "designing-growth-loops": "设计和优化增长飞轮",
    "designing-surveys": "设计有效的调查问卷",
    "dogfooding": "推动团队内部试用自家产品",
    "measuring-product-market-fit": "评估产品市场契合度(PMF)",
    "planning-under-uncertainty": "不确定性环境下的产品规划",
    "positioning-messaging": "产品定位与市场传播策略",
    "pricing-strategy": "定价策略设计与优化",
    "prioritizing-roadmap": "产品路线图优先级排序",
    "problem-definition": "清晰定义问题，避免直接跳到方案",
    "product-idea-miner": "产品创意挖掘与评估",
    "product-led-sales": "产品驱动的销售增长模式",
    "product-operations": "产品运营体系搭建与扩展",
    "product-taste-intuition": "培养产品品味与设计直觉",
    "retention-engagement": "用户留存与活跃度优化",
    "scoping-cutting": "项目范围界定与功能裁剪",
    "setting-okrs-goals": "设定OKR目标与关键成果",
    "shipping-products": "加速产品交付与发布",
    "usability-testing": "可用性测试与用户测试",
    "user-onboarding": "用户引导与首次体验设计",
    "working-backwards": "亚马逊逆向工作法定义产品",
    "writing-prds": "编写产品需求文档(PRD)",
    "writing-specs-designs": "编写技术规格与设计文档",
    "writing-north-star-metrics": "定义北极星指标",
    # ── 商业与销售 ──
    "brand-storytelling": "品牌叙事与故事策略",
    "building-sales-team": "搭建和扩展销售团队",
    "community-building": "构建和发展产品社区",
    "content-marketing": "内容营销策略与SEO优化",
    "enterprise-sales": "企业级大客户销售策略",
    "founder-sales": "创始人早期销售与获客",
    "fundraising": "融资策略与投资人关系管理",
    "launch-marketing": "产品发布与上市营销策划",
    "marketplace-liquidity": "双边市场流动性与供需平衡",
    "media-relations": "媒体关系与新闻报道策略",
    "partnership-bd": "战略合作与商务拓展",
    "platform-strategy": "平台商业模式与生态策略",
    "sales-compensation": "销售薪酬与激励方案设计",
    "sales-qualification": "销售线索筛选与评估",
    "startup-ideation": "创业点子生成与验证",
    "startup-pivoting": "创业公司转型决策与执行",
    # ── 团队与管理 ──
    "building-team-culture": "建设和维护团队文化",
    "cross-functional-collaboration": "跨职能团队协作与沟通",
    "delegating-work": "有效委派工作与授权",
    "having-difficult-conversations": "处理困难对话与绩效反馈",
    "managing-up": "向上管理，与上级有效沟通",
    "onboarding-new-hires": "新员工入职引导方案",
    "organizational-design": "组织架构设计与优化",
    "organizational-transformation": "组织转型与现代产品实践",
    "post-mortems-retrospectives": "复盘总结与回顾会议",
    "running-decision-processes": "高效决策流程管理",
    "running-design-reviews": "设计评审与设计反馈",
    "running-effective-1-1s": "高效一对一会议",
    "running-effective-meetings": "高效会议管理与优化",
    "running-offsites": "团队外出研讨会策划",
    "stakeholder-alignment": "利益相关者对齐与达成共识",
    "team-rituals": "团队仪式与文化活动设计",
    # ── 职业发展 ──
    "building-a-promotion-case": "准备晋升材料与晋升谈话",
    "career-transitions": "职业转型与变动指导",
    "conducting-interviews": "设计有效的招聘面试流程",
    "energy-management": "精力管理与防止倦怠",
    "evaluating-candidates": "评估求职者与招聘决策",
    "evaluating-trade-offs": "权衡取舍与方案比较",
    "finding-mentors-sponsors": "寻找职业导师与赞助人",
    "giving-presentations": "制作演示文稿与演讲技巧",
    "managing-imposter-syndrome": "应对冒名顶替综合征",
    "managing-timelines": "项目时间线与截止日期管理",
    "negotiating-offers": "薪资谈判与工作机会协商",
    "personal-productivity": "个人效率与时间管理",
    "written-communication": "书面沟通与文档写作",
    "writing-job-descriptions": "编写有效的职位描述",
    # ── 工程 ──
    "design-engineering": "设计工程能力建设",
    "design-systems": "构建和扩展设计系统",
    "engineering-culture": "构建工程师文化与开发体验",
    "managing-tech-debt": "技术债务管理策略",
    "platform-infrastructure": "内部平台与技术基础设施建设",
    "systems-thinking": "系统思维与复杂问题分析",
    "technical-roadmaps": "技术路线图规划",
    # ── 可视化 / 工具 ──
    "excalidraw-diagram": "从文本生成Excalidraw手绘图表",
    "frontend-design": "高质量前端界面设计与实现",
    "hand-drawn-icons": "生成手绘风格SVG图标",
    "json-canvas": "创建和编辑JSON Canvas文件",
    "mermaid-visualizer": "将文本转化为Mermaid专业图表",
    "obsidian-bases": "创建和编辑Obsidian Bases视图",
    "obsidian-canvas-creator": "从文本生成Obsidian Canvas画布",
    "obsidian-markdown": "Obsidian风格Markdown文档编辑",
    "ppt-generator": "AI驱动的PPT演示文稿与视频生成",
    # ── 中文特色工具 ──
    "fr-insight": "上市公司财报解读与可视化分析",
    "expert-debate": "多位专家多视角辩论分析问题",
    "ielts-video-generator": "雅思口语教学视频自动生成",
    "wxarticle": "微信公众号文章转PDF工具",
    # ── 命令 ──
    "feishu-bot": "飞书机器人配置与集成",
}

# ──────────────────────────────────────────────
# Skill kind classification
# ──────────────────────────────────────────────

SKILL_KINDS = {
    # ── Dev ──
    "ai-evals": "dev",
    "building-with-llms": "dev",
    "design-engineering": "dev",
    "design-systems": "dev",
    "dispatching-parallel-agents": "dev",
    "engineering-culture": "dev",
    "executing-plans": "dev",
    "find-skills": "dev",
    "finishing-a-development-branch": "dev",
    "managing-tech-debt": "dev",
    "platform-infrastructure": "dev",
    "receiving-code-review": "dev",
    "requesting-code-review": "dev",
    "skill-creator": "dev",
    "subagent-driven-development": "dev",
    "systematic-debugging": "dev",
    "technical-roadmaps": "dev",
    "test-driven-development": "dev",
    "using-git-worktrees": "dev",
    "using-superpowers": "dev",
    "verification-before-completion": "dev",
    "vibe-coding": "dev",
    "writing-plans": "dev",
    "writing-skills": "dev",
    # ── Product ──
    "ai-product-strategy": "product",
    "analyzing-user-feedback": "product",
    "behavioral-product-design": "product",
    "coaching-pms": "product",
    "competitive-analysis": "product",
    "conducting-user-interviews": "product",
    "defining-product-vision": "product",
    "designing-growth-loops": "product",
    "designing-surveys": "product",
    "dogfooding": "product",
    "measuring-product-market-fit": "product",
    "planning-under-uncertainty": "product",
    "positioning-messaging": "product",
    "prioritizing-roadmap": "product",
    "problem-definition": "product",
    "product-idea-miner": "product",
    "product-led-sales": "product",
    "product-operations": "product",
    "product-taste-intuition": "product",
    "retention-engagement": "product",
    "scoping-cutting": "product",
    "setting-okrs-goals": "product",
    "shipping-products": "product",
    "usability-testing": "product",
    "user-onboarding": "product",
    "working-backwards": "product",
    "writing-prds": "product",
    "writing-specs-designs": "product",
    "writing-north-star-metrics": "product",
    # ── Business ──
    "brand-storytelling": "business",
    "building-sales-team": "business",
    "community-building": "business",
    "content-marketing": "business",
    "enterprise-sales": "business",
    "founder-sales": "business",
    "fundraising": "business",
    "launch-marketing": "business",
    "marketplace-liquidity": "business",
    "media-relations": "business",
    "partnership-bd": "business",
    "platform-strategy": "business",
    "pricing-strategy": "business",
    "sales-compensation": "business",
    "sales-qualification": "business",
    "startup-ideation": "business",
    "startup-pivoting": "business",
    # ── Team ──
    "building-team-culture": "team",
    "cross-functional-collaboration": "team",
    "delegating-work": "team",
    "having-difficult-conversations": "team",
    "managing-up": "team",
    "onboarding-new-hires": "team",
    "organizational-design": "team",
    "organizational-transformation": "team",
    "post-mortems-retrospectives": "team",
    "running-decision-processes": "team",
    "running-design-reviews": "team",
    "running-effective-1-1s": "team",
    "running-effective-meetings": "team",
    "running-offsites": "team",
    "stakeholder-alignment": "team",
    "team-rituals": "team",
    # ── Career ──
    "building-a-promotion-case": "career",
    "career-transitions": "career",
    "conducting-interviews": "career",
    "energy-management": "career",
    "evaluating-candidates": "career",
    "evaluating-new-technology": "career",
    "finding-mentors-sponsors": "career",
    "giving-presentations": "career",
    "managing-imposter-syndrome": "career",
    "managing-timelines": "career",
    "negotiating-offers": "career",
    "personal-productivity": "career",
    "written-communication": "career",
    "writing-job-descriptions": "career",
    # ── Tools ──
    "excalidraw-diagram": "tools",
    "frontend-design": "tools",
    "hand-drawn-icons": "tools",
    "json-canvas": "tools",
    "mermaid-visualizer": "tools",
    "obsidian-bases": "tools",
    "obsidian-canvas-creator": "tools",
    "obsidian-markdown": "tools",
    "ppt-generator": "tools",
    "fr-insight": "tools",
    "ielts-video-generator": "tools",
    "wxarticle": "tools",
    "feishu-bot": "tools",
    # ── Thinking ──
    "brainstorming": "thinking",
    "cos-archive": "thinking",
    "cos-arena": "thinking",
    "cos-garden": "thinking",
    "cos-memory": "thinking",
    "cos-mirror": "thinking",
    "cos-workshop": "thinking",
    "evaluating-trade-offs": "thinking",
    "expert-debate": "thinking",
    "systems-thinking": "thinking",
}

# ──────────────────────────────────────────────
# Utility functions
# ──────────────────────────────────────────────


def detect_language():
    """Detect system language — return 'zh' if Chinese, else 'en'."""
    try:
        lang = locale.getlocale()[0] or os.environ.get("LANG", "") or ""
    except Exception:
        lang = os.environ.get("LANG", "")
    return "zh" if lang.startswith("zh") else "en"


def find_available_port(start=8765, max_tries=10):
    """Find an available port starting from `start`."""
    for port in range(start, start + max_tries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", port))
                return port
        except OSError:
            continue
    return None


# ──────────────────────────────────────────────
# Skill scanning
# ──────────────────────────────────────────────


def scan_skills():
    """Scan all known directories for skills, return list of skill dicts."""
    skills = []
    seen_real_paths = set()

    for base_path, category in SCAN_DIRS:
        if not base_path.exists():
            continue
        _scan_dir(base_path, category, skills, seen_real_paths, depth=0)

    skills.sort(key=lambda s: s["name"].lower())
    return skills


def _scan_dir(base_path, category, skills, seen, depth):
    """Recursively scan a directory for SKILL.md files."""
    try:
        entries = sorted(base_path.iterdir())
    except PermissionError:
        return

    for item in entries:
        if not item.is_dir():
            continue

        skill_file = item / "SKILL.md"
        if skill_file.exists():
            try:
                real_path = str(item.resolve())
            except OSError:
                real_path = str(item)

            if real_path in seen:
                continue
            seen.add(real_path)

            try:
                content = skill_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                content = ""

            meta = _parse_frontmatter(content)
            try:
                stat = skill_file.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime(
                    "%Y-%m-%d %H:%M"
                )
            except Exception:
                mtime = "unknown"

            actual_category = category
            is_symlink = item.is_symlink()
            if is_symlink and AGENTS_SKILLS_DIR.exists():
                try:
                    if (real_path + os.sep).startswith(str(AGENTS_SKILLS_DIR.resolve()) + os.sep):
                        actual_category = "agent"
                except Exception:
                    pass

            # Use Chinese descriptions when lang=zh; otherwise use original
            skill_name = item.name
            if _current_lang == "zh" and skill_name in SKILL_DESCRIPTIONS_ZH:
                desc = SKILL_DESCRIPTIONS_ZH[skill_name]
            else:
                desc = meta.get("description", _extract_description(content))

            skills.append(
                {
                    "name": meta.get("name", skill_name),
                    "description": desc,
                    "kind": SKILL_KINDS.get(skill_name, "other"),
                    "path": str(item),
                    "shortPath": _short_path(str(item)),
                    "realPath": real_path,
                    "category": actual_category,
                    "modified": mtime,
                    "size": _format_size(_dir_size(item)),
                    "isSymlink": is_symlink,
                }
            )

        if depth < 2:
            nested = item / "skills"
            if nested.exists() and nested.is_dir():
                _scan_dir(nested, category, skills, seen, depth + 1)


def _parse_frontmatter(content):
    """Parse YAML-like frontmatter without external dependencies."""
    meta = {}
    if not content.startswith("---"):
        return meta
    end = content.find("---", 3)
    if end == -1:
        return meta

    current_key = None
    current_val = []

    for line in content[3:end].split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if ":" in stripped and not stripped.startswith("-"):
            if current_key and current_val:
                meta[current_key] = " ".join(current_val).strip()

            key, _, value = stripped.partition(":")
            current_key = key.strip()
            value = value.strip().strip('"').strip("'")
            current_val = [value] if value else []
        elif current_key:
            current_val.append(stripped)

    if current_key and current_val:
        meta[current_key] = " ".join(current_val).strip()

    return meta


def _extract_description(content):
    """Extract first meaningful line as description."""
    in_frontmatter = False
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        if stripped and not stripped.startswith("#"):
            return stripped[:300]
    return "No description available"


def _dir_size(path):
    """Get total byte size of a directory."""
    total = 0
    try:
        for f in Path(path).rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
    except Exception:
        pass
    return total


def _format_size(size):
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f}KB"
    else:
        return f"{size / 1024 / 1024:.1f}MB"


def _short_path(path):
    """Abbreviate home directory to ~ for display."""
    home = str(Path.home())
    if path.startswith(home):
        return "~" + path[len(home):]
    return path


def _open_folder(path):
    """Open a folder in the system file manager (cross-platform)."""
    if sys.platform == "darwin":
        subprocess.Popen(["open", path])
    elif sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.Popen(["xdg-open", path])


# ──────────────────────────────────────────────
# HTTP Server
# ──────────────────────────────────────────────


class SkillManagerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html()
        elif parsed.path == "/api/skills":
            self._send_json(scan_skills())
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/api/open":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
        except Exception:
            self._send_json({"error": "Invalid request body"}, 400)
            return

        target = body.get("path", "")
        if not target or not os.path.isdir(target):
            self._send_json({"error": "Path not found"}, 404)
            return

        try:
            _open_folder(target)
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_DELETE(self):
        if self.path != "/api/skills":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
        except Exception:
            self._send_json({"error": "Invalid request body"}, 400)
            return

        target = body.get("path", "")
        if not target:
            self._send_json({"error": "No path provided"}, 400)
            return

        try:
            resolved = str(Path(target).resolve())
        except Exception:
            self._send_json({"error": "Invalid path"}, 400)
            return

        allowed_dirs = [base for base, _ in SCAN_DIRS]
        if AGENTS_SKILLS_DIR.exists():
            allowed_dirs.append(AGENTS_SKILLS_DIR)

        allowed = any(
            (resolved + os.sep).startswith(str(d.resolve()) + os.sep)
            for d in allowed_dirs
            if d.exists()
        )

        if not allowed:
            self._send_json({"error": "Path not in allowed skill directories"}, 403)
            return

        if not os.path.exists(target):
            self._send_json({"error": "Path does not exist"}, 404)
            return

        try:
            if os.path.islink(target):
                os.unlink(target)
            else:
                shutil.rmtree(target)
            self._send_json({"success": True, "deleted": target})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _send_json(self, data, code=200):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self):
        lang_data = json.dumps({
            "ui": UI_STRINGS[_current_lang],
            "kinds": KIND_LABELS[_current_lang],
            "kindOrder": KIND_ORDER,
        }, ensure_ascii=False).replace("</", "<\\/")
        html = HTML_TEMPLATE.replace("__LANG_DATA__", lang_data)
        payload = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass


# ──────────────────────────────────────────────
# HTML Template — Retro File Manager
# ──────────────────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Skill Manager</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --chrome: #d8d0c4;
  --chrome-hi: #ece4d8;
  --chrome-lo: #b0a898;
  --chrome-grad: linear-gradient(180deg, #e8e0d4, #d8d0c4);
  --btn-grad: linear-gradient(180deg, #efe7db, #ddd5c9);
  --btn-border-hi: #ece4d8;
  --btn-border-lo: #b0a898;
  --content: #faf7f2;
  --sidebar: #f0ebe3;
  --selected: #c8ddc0;
  --selected-text: #2a4a25;
  --green: #5a8a4f;
  --hover: #eae5dd;
  --even: rgba(0,0,0,0.018);
  --border: #c8c0b4;
  --border-lt: #e0d8cc;
  --text: #2d2d2d;
  --text2: #666;
  --text3: #999;
  --danger: #c04030;
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  --mono: "SF Mono", Menlo, Consolas, monospace;
}
body {
  font-family: var(--font);
  background: #a89b8c;
  background-image: radial-gradient(circle, rgba(0,0,0,0.05) 0.5px, transparent 0.5px);
  background-size: 6px 6px;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  color: var(--text);
  line-height: 1.4;
}

/* --- Window --- */
.win {
  width: 98%; max-width: 1440px; height: 92vh;
  background: var(--chrome);
  border-radius: 10px 10px 4px 4px;
  box-shadow: 0 0 0 1px rgba(0,0,0,0.08), 0 12px 48px rgba(0,0,0,0.28),
    inset 0 1px 0 rgba(255,255,255,0.4);
  display: flex; flex-direction: column; overflow: hidden;
  animation: winOpen 0.35s cubic-bezier(0.16,1,0.3,1);
}
.win.maxi { width:100%; height:100vh; max-width:none; border-radius:0; }
.win.shaded .toolbar, .win.shaded .body, .win.shaded .status { display:none; }
.win.shaded { height:auto; }
@keyframes winOpen {
  from { opacity:0; transform:scale(0.94) translateY(12px); }
  to { opacity:1; transform:scale(1) translateY(0); }
}

/* --- Title Bar --- */
.titlebar {
  height: 40px; flex-shrink: 0;
  background: var(--chrome-grad);
  background-image: repeating-linear-gradient(0deg,transparent,transparent 1px,rgba(255,255,255,0.22) 1px,rgba(255,255,255,0.22) 2px);
  border-bottom: 1px solid var(--chrome-lo);
  display: flex; align-items: center; padding: 0 14px;
  position: relative; cursor: default; user-select: none;
}
.tls { display:flex; gap:8px; z-index:2; }
.tl {
  width:13px; height:13px; border-radius:50%;
  border: 0.5px solid rgba(0,0,0,0.12);
  cursor:pointer; position:relative;
  transition: filter 0.12s, transform 0.12s;
}
.tl:hover { filter:brightness(1.08); transform:scale(1.15); }
.tl:active { filter:brightness(0.9); transform:scale(0.92); }
.tl-c { background:#ff5f57; } .tl-m { background:#febc2e; } .tl-x { background:#28c840; }
.titlebar:hover .tl-c::after { content:'\00d7'; }
.titlebar:hover .tl-m::after { content:'\2212'; }
.titlebar:hover .tl-x::after { content:'+'; }
.tl::after {
  position:absolute; inset:0; display:flex; align-items:center;
  justify-content:center; font-size:10px; font-weight:800;
  color:rgba(0,0,0,0.35); line-height:1;
}
.tb-title {
  position:absolute; left:50%; transform:translateX(-50%);
  font-size:13px; font-weight:700; color:#444; letter-spacing:-0.2px;
}

/* --- Toolbar --- */
.toolbar {
  display:flex; align-items:center; padding:5px 10px; gap:6px;
  background: linear-gradient(180deg, #e0d8cc, var(--chrome));
  border-bottom:1px solid var(--chrome-lo); flex-shrink:0;
}
.tb-btn {
  padding:4px 10px;
  background: var(--btn-grad);
  border:1px solid; border-color: var(--btn-border-hi) var(--btn-border-lo) var(--btn-border-lo) var(--btn-border-hi);
  border-radius:4px; font-size:14px; cursor:pointer; color:#555;
  transition:all 0.08s; line-height:1.2;
}
.tb-btn:hover { background:linear-gradient(180deg,#f5ede1,#e5ddd1); }
.tb-btn:active { background:linear-gradient(180deg,#d5cdc1,#ddd5c9); border-color:var(--btn-border-lo) var(--btn-border-hi) var(--btn-border-hi) var(--btn-border-lo); }
.tb-btn.loading .tb-spin { display:inline-block; animation:spin 0.7s linear infinite; }
@keyframes spin { to{transform:rotate(360deg)} }
.tb-sep { width:1px; height:22px; background:var(--chrome-lo); margin:0 4px; opacity:0.5; }
.tb-search { flex:1; max-width:300px; position:relative; }
.tb-search input {
  width:100%; padding:5px 8px 5px 28px;
  background:var(--content);
  border:1px solid; border-color:var(--btn-border-lo) var(--border-lt) var(--border-lt) var(--btn-border-lo);
  border-radius:4px; font:13px var(--font); color:var(--text); outline:none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.tb-search input::placeholder { color:#bbb; }
.tb-search input:focus {
  border-color:var(--green);
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.08), 0 0 0 2px rgba(90,138,79,0.15);
}
.tb-sicon { position:absolute; left:8px; top:50%; transform:translateY(-50%); font-size:13px; color:#bbb; pointer-events:none; }
.tb-search input:focus ~ .tb-sicon { color:var(--green); }
.tb-sort { position:relative; }
.tb-sort select {
  padding:5px 24px 5px 8px;
  background:var(--btn-grad);
  border:1px solid; border-color:var(--btn-border-hi) var(--btn-border-lo) var(--btn-border-lo) var(--btn-border-hi);
  border-radius:4px; font:12px var(--font); color:#555; cursor:pointer; appearance:none; outline:none;
}
.tb-sort::after { content:'\25be'; position:absolute; right:8px; top:50%; transform:translateY(-50%); font-size:11px; color:#999; pointer-events:none; }

/* --- Body (sidebar + table) --- */
.body { flex:1; display:flex; overflow:hidden; }

/* --- Sidebar --- */
.sidebar { width:184px; background:var(--sidebar); border-right:1px solid var(--border); padding:8px 0; overflow-y:auto; flex-shrink:0; }
.sb-hd { padding:4px 14px 8px; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.8px; color:#aaa; }
.sb-i {
  display:flex; align-items:center; justify-content:space-between;
  padding:6px 14px; font-size:13px; color:#555; cursor:pointer;
  transition:background 0.1s; user-select:none;
}
.sb-i:hover { background:#e8e0d8; }
.sb-i.on { background:var(--selected); color:var(--selected-text); font-weight:600; }
.sb-i.on:hover { background:#bdd4b5; }
.sb-ic { margin-right:8px; font-size:15px; flex-shrink:0; }
.sb-lb { flex:1; }
.sb-ct { font-size:11px; color:#aaa; background:rgba(0,0,0,0.05); padding:1px 8px; border-radius:8px; }
.sb-i.on .sb-ct { background:rgba(0,0,0,0.08); color:#4a7040; }

/* --- Table --- */
.tbl-wrap { flex:1; overflow:auto; background:var(--content); }
table { width:100%; border-collapse:collapse; }
thead { position:sticky; top:0; z-index:10; }
th {
  background:linear-gradient(180deg,#f0e8dc,#e0d8cc);
  border-bottom:1px solid var(--border); border-right:1px solid var(--border-lt);
  padding:6px 10px; text-align:left; font-size:11px; font-weight:700;
  color:#888; text-transform:uppercase; letter-spacing:0.4px;
  cursor:pointer; user-select:none; white-space:nowrap; transition:background 0.12s;
}
th:hover { background:linear-gradient(180deg,#f5ede1,#e5ddd1); color:#666; }
th:last-child { border-right:none; }
th.sorted { color:#555; }
th .arr { font-size:9px; margin-left:3px; opacity:0.35; }
th.sorted .arr { opacity:1; color:var(--green); }
td {
  padding:5px 10px; font-size:13px; border-bottom:1px solid #ede8e0;
  color:var(--text); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:0;
}
.ci { width:32px; text-align:center; overflow:visible; }
.cn { width:180px; } .cc { width:100px; } .cd { } .cp { width:200px; }
.cm { width:100px; } .cs { width:55px; text-align:right; } .ca { width:36px; text-align:center; }
tr:nth-child(even) td { background:var(--even); }
tr:hover td { background:var(--hover); cursor:pointer; }
tr.sel td { background:var(--selected) !important; }
.n { font-weight:600; }
.badge { display:inline-block; padding:1px 8px; border-radius:4px; font-size:11px; font-weight:600; }
.b-dev { background:#e0e8f8; color:#3050a0; }
.b-prod { background:#dff0df; color:#3a7a3a; }
.b-biz { background:#f5ecd0; color:#8a7020; }
.b-team { background:#d8f0f0; color:#207070; }
.b-career { background:#e8e4f8; color:#5a50b0; }
.b-tool { background:#fce8d8; color:#a06020; }
.b-think { background:#f8e0f0; color:#a04080; }
.b-other { background:#eee; color:#888; }
.desc { color:var(--text2); font-size:12px; }
.path { font:11px var(--mono); color:var(--text3); }
.date { font-size:12px; color:var(--text3); }
.sz { font:12px var(--mono); color:var(--text3); }
.lk { font:9px var(--mono); padding:0 4px; background:#eee; border-radius:3px; color:#aaa; margin-left:4px; vertical-align:middle; }
.dx {
  opacity:0; padding:2px 6px; background:transparent;
  border:1px solid transparent; border-radius:3px;
  color:#ccc; cursor:pointer; font-size:15px; line-height:1; transition:all 0.1s;
}
tr:hover .dx { opacity:1; color:#bbb; }
.dx:hover { color:var(--danger); background:rgba(192,64,48,0.06); border-color:rgba(192,64,48,0.12); }
.doc { vertical-align:middle; }

/* --- Status --- */
.status {
  display:flex; align-items:center; justify-content:space-between;
  padding:3px 14px; height:26px; flex-shrink:0;
  background:linear-gradient(180deg,#e0d8cc,var(--chrome));
  border-top:1px solid var(--border); font-size:12px; color:var(--text2);
}
.st-l { display:flex; gap:14px; } .st-r { display:flex; align-items:center; gap:6px; }
.st-p { font-size:14px; }

/* --- Alert --- */
.ov { display:none; position:fixed; inset:0; z-index:1000; background:rgba(0,0,0,0.3); align-items:center; justify-content:center; }
.ov.on { display:flex; }
.al {
  background:var(--chrome-hi);
  border:2px solid; border-color:#f0e8dc #908878 #908878 #f0e8dc;
  border-radius:10px; padding:24px 28px; max-width:420px; width:90%;
  box-shadow:0 8px 32px rgba(0,0,0,0.35);
  animation:alIn 0.2s cubic-bezier(0.34,1.56,0.64,1);
}
@keyframes alIn { from{opacity:0;transform:scale(0.85)} to{opacity:1;transform:scale(1)} }
.al-ic { font-size:36px; margin-bottom:12px; }
.al-t { font-size:14px; font-weight:700; color:#333; margin-bottom:6px; }
.al-tx { font-size:13px; color:#666; line-height:1.5; margin-bottom:8px; }
.al-p {
  font:11px var(--mono); background:var(--content);
  border:1px solid; border-color:var(--btn-border-lo) var(--border-lt) var(--border-lt) var(--btn-border-lo);
  padding:6px 10px; border-radius:4px; word-break:break-all;
  color:var(--danger); margin-bottom:18px; line-height:1.5;
}
.al-ac { display:flex; justify-content:flex-end; gap:8px; }
.al-btn {
  padding:6px 22px; background:var(--btn-grad);
  border:1px solid; border-color:var(--btn-border-hi) var(--btn-border-lo) var(--btn-border-lo) var(--btn-border-hi);
  border-radius:5px; font:13px var(--font); cursor:pointer; color:#444; transition:all 0.1s;
}
.al-btn:hover { background:linear-gradient(180deg,#f5ede1,#e5ddd1); }
.al-btn:active { border-color:var(--btn-border-lo) var(--btn-border-hi) var(--btn-border-hi) var(--btn-border-lo); }
.al-del {
  background:linear-gradient(180deg,#e06a5a,#c04a3e);
  border-color:#f0a098 #903838 #903838 #f0a098;
  color:#fff; font-weight:700;
}
.al-del:hover { background:linear-gradient(180deg,#e87a6a,#d05548); }
.al-del:disabled { opacity:0.5; pointer-events:none; }

/* --- Fun alert --- */
.fun { text-align:center; padding:20px 24px; }
.fun-e { font-size:48px; margin-bottom:12px; }
.fun-t { font-size:14px; color:#555; margin-bottom:16px; line-height:1.6; }

/* --- Toast --- */
.toast-r { position:fixed; top:20px; right:20px; z-index:2000; display:flex; flex-direction:column; gap:6px; }
.toast {
  padding:8px 16px; background:var(--chrome-hi);
  border:1px solid; border-color:#f0e8dc var(--btn-border-lo) var(--btn-border-lo) #f0e8dc;
  border-radius:6px; font:13px var(--font); color:#333;
  box-shadow:0 4px 16px rgba(0,0,0,0.2);
  animation:tIn 0.3s ease;
}
.toast-ok { border-left:3px solid var(--green); }
.toast-err { border-left:3px solid var(--danger); }
@keyframes tIn { from{opacity:0;transform:translateX(20px)} to{opacity:1;transform:translateX(0)} }

.empty { padding:60px 20px; text-align:center; color:#bbb; font-size:14px; display:none; }

@media(max-width:768px) {
  body{padding:0} .win{width:100%;height:100vh;border-radius:0}
  .sidebar{width:130px} .cp,.cd{display:none} .dx{opacity:1}
}
</style>
</head>
<body>

<div class="win" id="win">
  <!-- Title Bar -->
  <div class="titlebar">
    <div class="tls">
      <span class="tl tl-c" onclick="funClose()"></span>
      <span class="tl tl-m" onclick="toggleShade()"></span>
      <span class="tl tl-x" onclick="toggleMaxi()"></span>
    </div>
    <span class="tb-title">Skill Manager</span>
  </div>

  <!-- Toolbar -->
  <div class="toolbar">
    <button class="tb-btn" title="Refresh" onclick="doRefresh()" id="rbtn"><span class="tb-spin">&#8635;</span></button>
    <div class="tb-sep"></div>
    <div class="tb-search">
      <input type="text" id="si" placeholder="Search..." oninput="apply()">
      <span class="tb-sicon">&#128269;</span>
    </div>
    <div class="tb-sep"></div>
    <div class="tb-sort">
      <select id="ss" onchange="sortChange()">
        <option value="name">Sort: Name</option>
        <option value="kind">Sort: Kind</option>
        <option value="modified">Sort: Date</option>
        <option value="size">Sort: Size</option>
      </select>
    </div>
  </div>

  <!-- Body -->
  <div class="body">
    <div class="sidebar" id="sb"></div>
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th class="ci"></th>
          <th class="cn" onclick="doSort('name')">Name <span class="arr">&#9650;</span></th>
          <th class="cc" onclick="doSort('kind')">Kind <span class="arr">&#9650;</span></th>
          <th class="cd" onclick="doSort('description')">Description <span class="arr">&#9650;</span></th>
          <th class="cp">Path</th>
          <th class="cm" onclick="doSort('modified')">Modified <span class="arr">&#9650;</span></th>
          <th class="cs" onclick="doSort('size')">Size <span class="arr">&#9650;</span></th>
          <th class="ca"></th>
        </tr></thead>
        <tbody id="tb"></tbody>
      </table>
      <div class="empty" id="emp"></div>
    </div>
  </div>

  <!-- Status -->
  <div class="status">
    <div class="st-l"><span id="sCount">-</span><span id="sCats"></span></div>
    <div class="st-r"><span class="st-p" id="sPlant">&#127793;</span><span id="sState">...</span></div>
  </div>
</div>

<!-- Delete Alert -->
<div class="ov" id="delOv">
  <div class="al">
    <div class="al-ic">&#9888;&#65039;</div>
    <div class="al-t" id="alTitle"></div>
    <div class="al-tx" id="alText"></div>
    <div class="al-p" id="alPath"></div>
    <div class="al-ac">
      <button class="al-btn" onclick="closeAl()" id="alCancel"></button>
      <button class="al-btn al-del" id="alBtn" onclick="doDel()"></button>
    </div>
  </div>
</div>

<!-- Fun Alert -->
<div class="ov" id="funOv">
  <div class="al fun">
    <div class="fun-e">&#128579;</div>
    <div class="fun-t" id="funText"></div>
    <div class="al-ac" style="justify-content:center">
      <button class="al-btn" onclick="$('funOv').classList.remove('on')" id="funBtn"></button>
    </div>
  </div>
</div>

<div class="toast-r" id="tr"></div>

<script>
const L = __LANG_DATA__;
const $=id=>document.getElementById(id);
let all=[], folder='all', sCol='name', sDir='asc', selIdx=-1, pendDel=null;
const si=$('si');

async function api(){ const r=await fetch('/api/skills'); if(!r.ok)throw new Error('fail'); return r.json(); }
async function apiDel(p){ return (await fetch('/api/skills',{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:p})})).json(); }

function esc(s){ const e=document.createElement('span'); e.textContent=s; return e.innerHTML.replace(/'/g,"&#39;").replace(/"/g,"&quot;"); }
function bk(k){ const m={dev:'b-dev',product:'b-prod',business:'b-biz',team:'b-team',career:'b-career',tools:'b-tool',thinking:'b-think'}; return m[k]||'b-other'; }

function pe(n){ return n<20?'\u{1F331}':n<80?'\u{1F33F}':n<150?'\u{1F333}':'\u{1F3D4}'; }
function ps(s){ const m=s.match(/([\d.]+)\s*(B|KB|MB)/i); if(!m)return 0; const n=parseFloat(m[1]); return m[2]==='KB'?n*1024:m[2]==='MB'?n*1048576:n; }
function sd(d){ try{ return d.split(' ')[0]; }catch{return d;} }

function sortList(l){
  return [...l].sort((a,b)=>{
    let va,vb;
    if(sCol==='size'){va=ps(a.size);vb=ps(b.size);}
    else if(sCol==='kind'){va=(a.kind||'').toLowerCase();vb=(b.kind||'').toLowerCase();}
    else{va=(a[sCol]||'').toLowerCase();vb=(b[sCol]||'').toLowerCase();}
    if(va<vb)return sDir==='asc'?-1:1; if(va>vb)return sDir==='asc'?1:-1; return 0;
  });
}
function doSort(c){ if(sCol===c)sDir=sDir==='asc'?'desc':'asc'; else{sCol=c;sDir='asc';} $('ss').value=c; apply(); }
function sortChange(){ sCol=$('ss').value; sDir='asc'; apply(); }

function renderSb(){
  const kinds={}; all.forEach(s=>{kinds[s.kind]=(kinds[s.kind]||0)+1;});
  let h=`<div class="sb-i${folder==='all'?' on':''}" onclick="setF('all')"><span class="sb-ic">\u{1F4C1}</span><span class="sb-lb">${esc(L.ui.allSkills)}</span><span class="sb-ct">${all.length}</span></div>`;
  h+=`<div class="sb-hd">${esc(L.ui.categories)}</div>`;
  L.kindOrder.forEach(k=>{if(!kinds[k])return; const lb=L.kinds[k]||k; h+=`<div class="sb-i${folder===k?' on':''}" onclick="setF('${k}')"><span class="sb-ic badge ${bk(k)}" style="font-size:10px;padding:0 5px;margin-right:6px">${esc(lb)}</span><span class="sb-lb"></span><span class="sb-ct">${kinds[k]}</span></div>`;});
  $('sb').innerHTML=h;
}

function renderTbl(list){
  document.querySelectorAll('th').forEach(th=>{th.classList.remove('sorted');const a=th.querySelector('.arr');if(a)a.innerHTML='\u25B2';});
  const colMap={name:'cn',kind:'cc',description:'cd',modified:'cm',size:'cs'};
  const ath=document.querySelector('th.'+colMap[sCol]);
  if(ath){ath.classList.add('sorted');const a=ath.querySelector('.arr');if(a)a.innerHTML=sDir==='asc'?'\u25B2':'\u25BC';}
  const emp=$('emp');
  if(!list.length){$('tb').innerHTML='';emp.style.display='block';return;}
  emp.style.display='none';
  $('tb').innerHTML=list.map((s,i)=>`<tr onclick="openDir('${esc(s.path)}')" class="${i===selIdx?'sel':''}">
<td class="ci"><svg class="doc" width="16" height="20" viewBox="0 0 16 20"><path d="M1 1h9l5 5v13H1V1z" fill="#faf7f2" stroke="#bbb" stroke-width=".8"/><path d="M10 1v5h5" fill="none" stroke="#bbb" stroke-width=".8"/><line x1="4" y1="10" x2="12" y2="10" stroke="#ddd" stroke-width=".6"/><line x1="4" y1="13" x2="10" y2="13" stroke="#ddd" stroke-width=".6"/></svg></td>
<td class="cn"><span class="n">${esc(s.name)}</span>${s.isSymlink?'<span class="lk">link</span>':''}</td>
<td class="cc"><span class="badge ${bk(s.kind)}">${esc(L.kinds[s.kind]||s.kind)}</span></td>
<td class="cd"><span class="desc" title="${esc(s.description)}">${esc(s.description)}</span></td>
<td class="cp"><span class="path" title="${esc(s.path)}">${esc(s.shortPath)}</span></td>
<td class="cm"><span class="date">${esc(sd(s.modified))}</span></td>
<td class="cs"><span class="sz">${esc(s.size)}</span></td>
<td class="ca"><button class="dx" onclick="event.stopPropagation();reqDel('${esc(s.path)}','${esc(s.name)}')">\u00d7</button></td>
</tr>`).join('');
}

function renderSt(list){
  const kinds={}; all.forEach(s=>{kinds[s.kind]=true;});
  $('sCount').textContent=list.length+' '+L.ui.items;
  $('sCats').textContent=Object.keys(kinds).length+' '+L.ui.kinds;
  $('sPlant').textContent=pe(all.length);
  $('sState').textContent=L.ui.ready;
}

function setF(f){folder=f;selIdx=-1;apply();}
function apply(){
  const q=si.value.toLowerCase();
  let l=all;
  if(folder!=='all')l=l.filter(s=>s.kind===folder);
  if(q)l=l.filter(s=>s.name.toLowerCase().includes(q)||s.description.toLowerCase().includes(q));
  l=sortList(l);
  renderSb(); renderTbl(l); renderSt(l);
}

function reqDel(p,n){pendDel=p;$('alTitle').textContent=L.ui.deleteConfirm+' "'+n+'"?';$('alPath').textContent=p;$('delOv').classList.add('on');}
function closeAl(){$('delOv').classList.remove('on');pendDel=null;}
async function doDel(){
  if(!pendDel)return;
  const b=$('alBtn');b.textContent=L.ui.deleting;b.disabled=true;
  try{
    const r=await apiDel(pendDel);
    if(r.success){toast(L.ui.deleted,'ok');closeAl();selIdx=-1;await doRefresh();}
    else toast(L.ui.error+': '+r.error,'err');
  }catch(e){toast(L.ui.error+': '+e.message,'err');}
  finally{b.textContent=L.ui.delete;b.disabled=false;}
}

async function openDir(p){
  try{const r=await fetch('/api/open',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:p})});
  const d=await r.json();if(!d.success)toast(L.ui.openFailed,'err');}
  catch(e){toast(L.ui.error+': '+e.message,'err');}
}
function funClose(){$('funOv').classList.add('on');}
function toggleShade(){$('win').classList.toggle('shaded');}
function toggleMaxi(){$('win').classList.toggle('maxi');}

function toast(m,t){
  const e=document.createElement('div');e.className='toast toast-'+t;e.textContent=m;
  $('tr').appendChild(e);
  setTimeout(()=>{e.style.opacity='0';e.style.transition='opacity 0.3s'},2500);
  setTimeout(()=>e.remove(),2800);
}

document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){closeAl();$('funOv').classList.remove('on');}
  if(e.key==='/'&&document.activeElement!==si){e.preventDefault();si.focus();}
});
$('delOv').addEventListener('click',function(e){if(e.target===this)closeAl();});
$('funOv').addEventListener('click',function(e){if(e.target===this)this.classList.remove('on');});

function initUI(){
  $('alText').textContent=L.ui.deleteText;
  $('alCancel').textContent=L.ui.cancel;
  $('alBtn').textContent=L.ui.delete;
  $('funText').innerHTML=L.ui.funText;
  $('funBtn').textContent=L.ui.funOk;
  $('emp').textContent=L.ui.noMatch;
  $('sState').textContent=L.ui.loading;
}

async function doRefresh(){
  const b=$('rbtn');b.classList.add('loading');$('sState').textContent=L.ui.scanning;
  try{all=await api();apply();}
  catch(e){toast(L.ui.loadFailed,'err');$('sState').textContent=L.ui.error;}
  finally{b.classList.remove('loading');}
}

initUI();
doRefresh();
</script>
</body>
</html>
"""

# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Claude Skill Manager")
    parser.add_argument("--port", type=int, default=None, help="Port to listen on (default: auto)")
    parser.add_argument("--lang", choices=["zh", "en"], default=None, help="UI language (default: auto-detect)")
    parser.add_argument("--no-open", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    # Language
    _current_lang = args.lang or detect_language()

    # Port
    if args.port:
        port = args.port
    else:
        port = find_available_port()
        if port is None:
            print("Error: No available port found (tried 8765-8774).")
            sys.exit(1)

    try:
        server = HTTPServer(("localhost", port), SkillManagerHandler)
    except OSError as e:
        print(f"Error: Cannot start on port {port} — {e}")
        print("Try: python app.py --port <other-port>")
        sys.exit(1)

    url = f"http://localhost:{port}"
    print(f"Skill Manager running at {url}")
    print(f"Language: {_current_lang}")
    print("Press Ctrl+C to stop.\n")

    if not args.no_open:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
