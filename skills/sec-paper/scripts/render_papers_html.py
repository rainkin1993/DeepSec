#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Render DeepSec paper JSON into a self-contained HTML report (site-aligned UI).

Compatible with Python 2.7+ and Python 3.x (stdlib only).
"""
from __future__ import absolute_import, division, print_function

import argparse
import io
import json
import os
import re
import sys
from datetime import datetime

try:
    from html import escape as html_escape
except ImportError:
    from cgi import escape as html_escape  # Python 2

SKILL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DEFAULT_CSS = os.path.join(SKILL_ROOT, "assets", "paper-report.css")

MATURITY_SEVERITY = {
    "RESEARCH_PROPOSAL": "secondary",
    "RESEARCH_PROTOTYPE": "warning",
    "LAB_SIMULATION_EVALUATION": "info",
    "FORMAL_VERIFICATION": "info",
    "USER_STUDY": "info",
    "PILOT_VALIDATION": "success",
    "DEPLOYED_IN_PRODUCTION": "success",
    "LARGE_SCALE_EMPIRICAL": "success",
    "research": "secondary",
    "prototype": "warning",
    "production": "success",
}

SECTION_KEYS = (
    ("scenario_zh", u"场景"),
    ("problem_zh", u"问题"),
    ("existing_issues_zh", u"现有方法的局限"),
    ("approach_zh", u"新理念和思路"),
    ("validation_zh", u"验证结果"),
)

PY2 = sys.version_info[0] < 3


def _u(text):
    """Normalize to unicode (Py2) / str (Py3)."""
    if text is None:
        return u"" if PY2 else ""
    if PY2:
        if isinstance(text, str):
            return text.decode("utf-8", "replace")
        return unicode(text)  # noqa: F821
    return str(text)


def esc(text):
    if text is None:
        return ""
    return html_escape(_u(text), quote=True)


def read_text(path):
    if PY2:
        with io.open(path, "r", encoding="utf-8") as f:
            return f.read()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_text(path, content):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    if PY2:
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(_u(content))
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def load_papers(data):
    """Normalize input into (papers, total, query_hint)."""
    query = ""
    if isinstance(data, list):
        return data, len(data), query
    if not isinstance(data, dict):
        raise ValueError("JSON root must be object or array")

    query = _u(data.get("query") or data.get("keyword") or data.get("title") or "")
    papers = data.get("papers")
    if papers is None and "id" in data and "title" in data:
        papers = [data]
    if papers is None:
        raise ValueError("JSON must contain 'papers' array or a single Paper object")
    total = data.get("total", len(papers))
    return papers, total, query


def maturity_class(en):
    return MATURITY_SEVERITY.get(en or "", "info")


def render_structured_info(paper, show_english):
    info = paper.get("structured_info")
    if not info:
        return ""

    parts = ['<div class="structured-info">']

    maturity = info.get("maturity")
    if maturity:
        label = "Maturity" if show_english else u"成熟度"
        value = maturity.get("en" if show_english else "zh") or maturity.get("en") or ""
        sev = maturity_class(maturity.get("en"))
        parts.append(
            '<div class="info-item"><span class="info-label">{0}</span>'
            '<span class="info-tag tag-{1}">{2}</span></div>'.format(
                esc(label), sev, esc(value)
            )
        )

    scenarios = info.get("application_scenarios")
    if scenarios:
        label = "Application Scenarios" if show_english else u"应用场景"
        items = scenarios.get("en" if show_english else "zh") or scenarios.get("en") or []
        tags = "".join(
            '<span class="info-tag tag-info">{0}</span>'.format(esc(s)) for s in items
        )
        parts.append(
            '<div class="info-item"><span class="info-label">{0}</span>'
            '<div class="info-tags">{1}</div></div>'.format(esc(label), tags)
        )

    surfaces = info.get("attack_surfaces")
    if surfaces:
        label = "Attack Surfaces" if show_english else u"攻击面"
        items = surfaces.get("en" if show_english else "zh") or surfaces.get("en") or []
        tags = "".join(
            '<span class="info-tag tag-warning">{0}</span>'.format(esc(s)) for s in items
        )
        parts.append(
            '<div class="info-item"><span class="info-label">{0}</span>'
            '<div class="info-tags">{1}</div></div>'.format(esc(label), tags)
        )

    parts.append("</div>")
    return "".join(parts)


def render_chinese_abstract(ca):
    if isinstance(ca, dict):
        sections = []
        for key, label in SECTION_KEYS:
            val = ca.get(key)
            if val:
                sections.append(
                    '<div class="abstract-section"><strong>{0}：</strong>{1}</div>'.format(
                        esc(label), esc(val)
                    )
                )
        if sections:
            return (
                '<div class="abstract-text-content structured-abstract">{0}</div>'.format(
                    "".join(sections)
                )
            )
        return ""
    if ca:
        return '<div class="abstract-text-content">{0}</div>'.format(esc(ca))
    return ""


def render_abstract_content(paper, show_english):
    has_chinese = bool(paper.get("chinese_abstract") or paper.get("structured_info"))
    actually_en = (not has_chinese) or show_english

    parts = []
    if has_chinese:
        current = "EN" if actually_en else u"中文"
        switch_to = u"中文" if actually_en else "EN"
        pid = paper.get("id")
        parts.append(
            '<button type="button" class="language-toggle-btn" '
            'data-paper-id="{0}" title="切换到{1}">'
            "{2} / {3}</button>".format(
                esc(pid), esc(switch_to), esc(current), esc(switch_to)
            )
        )

    parts.append(render_structured_info(paper, actually_en))

    if actually_en and paper.get("abstract"):
        parts.append(
            '<div class="abstract-text-content">{0}</div>'.format(esc(paper["abstract"]))
        )
    elif not actually_en and paper.get("chinese_abstract"):
        parts.append(render_chinese_abstract(paper["chinese_abstract"]))
    elif paper.get("abstract"):
        parts.append(
            '<div class="abstract-text-content">{0}</div>'.format(esc(paper["abstract"]))
        )

    return "".join(parts)


def render_paper_card(paper, expand=True):
    pid = paper.get("id")
    title = paper.get("title") or "(untitled)"
    url = paper.get("url") or "#"
    authors = paper.get("authors")
    year = paper.get("year")
    conference = paper.get("conference")

    meta = []
    if authors:
        meta.append("<span>👤 {0}</span>".format(esc(authors)))
    if year is not None:
        meta.append("<span>📅 {0}</span>".format(esc(year)))
    if conference:
        meta.append("<span>📚 {0}</span>".format(esc(conference)))

    has_abs = bool(
        paper.get("abstract") or paper.get("chinese_abstract") or paper.get("structured_info")
    )
    display = "block" if expand else "none"
    icon = u"▲" if expand else u"▼"
    header_cls = "paper-abstract-header expanded" if expand else "paper-abstract-header"

    abstract_html = ""
    if has_abs:
        zh_body = render_abstract_content(paper, show_english=False)
        en_body = render_abstract_content(paper, show_english=True)
        abstract_html = """
            <div class="paper-abstract-container" data-paper-id="{pid}">
                <button type="button" class="{header_cls}" data-toggle-abstract>
                    <span class="abstract-text">摘要</span>
                    <span class="abstract-icon">{icon}</span>
                </button>
                <div class="paper-abstract-content" style="display: {display};" data-lang="zh">
                    <div class="lang-body" data-version="zh">{zh_body}</div>
                    <div class="lang-body" data-version="en" hidden>{en_body}</div>
                </div>
            </div>
        """.format(
            pid=esc(pid),
            header_cls=header_cls,
            icon=icon,
            display=display,
            zh_body=zh_body,
            en_body=en_body,
        )

    summary = ""
    if paper.get("chinese_summary"):
        summary = """
            <div class="paper-chinese-summary">
                <h4>📖 中文解读</h4>
                <p>{0}</p>
            </div>
        """.format(
            esc(paper["chinese_summary"])
        )

    return """
        <div class="paper-card" id="paper-{pid}">
            <div class="paper-title">
                <a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>
            </div>
            <div class="paper-meta">{meta}</div>
            {abstract_html}
            {summary}
        </div>
    """.format(
        pid=esc(pid),
        url=esc(url),
        title=esc(title),
        meta="".join(meta),
        abstract_html=abstract_html,
        summary=summary,
    )


CLIENT_JS = r"""
(function () {
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-toggle-abstract]');
    if (btn) {
      var container = btn.parentElement;
      var content = container.querySelector('.paper-abstract-content');
      var icon = btn.querySelector('.abstract-icon');
      if (content.style.display === 'none') {
        content.style.display = 'block';
        icon.textContent = '\u25b2';
        btn.classList.add('expanded');
      } else {
        content.style.display = 'none';
        icon.textContent = '\u25bc';
        btn.classList.remove('expanded');
      }
      return;
    }

    var langBtn = e.target.closest('.language-toggle-btn');
    if (langBtn) {
      e.stopPropagation();
      var box = langBtn.closest('.paper-abstract-content');
      if (!box) return;
      var next = box.getAttribute('data-lang') === 'zh' ? 'en' : 'zh';
      box.setAttribute('data-lang', next);
      box.querySelectorAll('.lang-body').forEach(function (el) {
        el.hidden = el.getAttribute('data-version') !== next;
      });
      box.querySelectorAll('.language-toggle-btn').forEach(function (b) {
        if (next === 'en') {
          b.textContent = 'EN / \u4e2d\u6587';
          b.title = '\u5207\u6362\u5230\u4e2d\u6587';
        } else {
          b.textContent = '\u4e2d\u6587 / EN';
          b.title = '\u5207\u6362\u5230EN';
        }
      });
    }
  });
})();
"""


def slugify(text):
    text = _u(text).strip().lower()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return (text[:60] or "papers")


def build_html(papers, total, title, query, css_text, expand_all=True):
    if total is None:
        total = len(papers)
    info = u"找到 {0} 篇论文，本页展示 {1} 篇".format(total, len(papers))
    if query:
        info = u"检索「{0}」：{1}".format(esc(query), info)

    cards = "\n".join(render_paper_card(p, expand=expand_all) for p in papers)
    if not papers:
        cards = (
            '<div class="empty-state"><h3>未找到相关论文</h3>'
            "<p>请尝试其他关键词</p></div>"
        )

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    return u"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <style>
{css_text}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>{title}</h1>
      <p class="subtitle">DeepSec 论文检索结果 · 生成于 {generated}</p>
    </header>
    <div class="results-info">{info}</div>
    <div class="papers-list">
{cards}
    </div>
    <footer class="site-footer">
      <p>样式对齐 <a href="http://deepsec.chat/" target="_blank" rel="noopener noreferrer">DeepSec</a> 论文卡片</p>
    </footer>
  </div>
  <script>
{js}
  </script>
</body>
</html>
""".format(
        title=esc(title),
        css_text=css_text,
        generated=esc(generated),
        info=info,
        cards=cards,
        js=CLIENT_JS,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render DeepSec papers JSON to HTML")
    parser.add_argument("input", help="Path to papers JSON (API response or {papers,total,query})")
    parser.add_argument("-o", "--output", help="Output HTML path")
    parser.add_argument("--title", default="", help="Report title")
    parser.add_argument("--css", default=DEFAULT_CSS, help="CSS file to inline")
    parser.add_argument("--collapse", action="store_true", help="Collapse abstracts by default")
    args = parser.parse_args(argv)

    in_path = os.path.abspath(args.input)
    raw = json.loads(read_text(in_path))
    papers, total, query = load_papers(raw)

    title = (args.title or "").strip()
    if not title:
        title = u"DeepSec：{0}".format(query) if query else u"DeepSec 论文检索结果"
    css_path = os.path.abspath(args.css)
    if not os.path.isfile(css_path):
        print("CSS not found: {0}".format(css_path), file=sys.stderr)
        return 1
    css_text = read_text(css_path)

    if args.output:
        out_path = os.path.abspath(args.output)
    else:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        name = slugify(query) if query else "papers"
        out_path = os.path.abspath(
            os.path.join(os.getcwd(), "deepsec-papers", "{0}-{1}.html".format(name, stamp))
        )

    html_doc = build_html(
        papers,
        total,
        title=title,
        query=query,
        css_text=css_text,
        expand_all=not args.collapse,
    )
    write_text(out_path, html_doc)
    print(os.path.abspath(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
