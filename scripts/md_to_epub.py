#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「系列全集讲稿」Markdown 转成微信读书可用的 EPUB3。

用法：
    python md_to_epub.py <输入.md> [--out <输出.epub>]

约定：
    - `# 一级标题` 作为章节边界：第一个一级标题及其后内容视为「前言」
      （自动过滤 markdown 自带目录行），此后每个 `# 第N集 ...` 单独成章。
    - 章节正文按 Markdown 渲染，保留 `##` 小节、引用块、分隔线、表格等。
    - 输出 EPUB3，带 nav.xhtml 可点击目录 + toc.ncx。
"""

import argparse
import html
import re
import sys
from pathlib import Path

try:
    import markdown
    from ebooklib import epub
except ImportError as exc:
    sys.exit(
        f"缺少依赖({exc.name or exc})，请先安装："
        "python -m pip install ebooklib markdown"
    )


CSS = """\
body { font-family: serif; line-height: 1.7; margin: 5%; }
h1 { font-size: 1.5em; }
h2 { font-size: 1.2em; }
blockquote { color: #555; border-left: 3px solid #ccc; margin-left: 0; padding-left: 1em; }
hr { border: none; border-top: 1px solid #ccc; margin: 1.5em 0; }
table { border-collapse: collapse; }
td, th { border: 1px solid #999; padding: 0.4em 0.8em; }
"""


def split_chapters(md_text: str) -> list[tuple[str, str]]:
    """按 `# ` 一级标题切分，返回 [(标题, 正文markdown), ...]。"""
    h1_re = re.compile(r"^#\s+(.+?)\s*$")
    toc_re = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s*\[.*?\]\(#.*?\)\s*$")
    chapters: list[tuple[str, str]] = []
    cur_title: str | None = None
    cur_lines: list[str] = []

    for line in md_text.splitlines():
        m = h1_re.match(line)
        if m:
            if cur_title is not None:
                chapters.append((cur_title, "\n".join(cur_lines)))
            cur_title = m.group(1).strip()
            cur_lines = []
        else:
            cur_lines.append(line)
    if cur_title is not None:
        chapters.append((cur_title, "\n".join(cur_lines)))

    # 前言章：过滤掉 markdown 自带目录行；若为空则跳过。
    if chapters:
        pre_title, pre_body = chapters[0]
        cleaned = [ln for ln in pre_body.splitlines() if not toc_re.match(ln)]
        pre_body = "\n".join(cleaned).strip()
        if pre_body:
            chapters[0] = (pre_title, pre_body)
        else:
            chapters.pop(0)
    return chapters


def build_epub(book_title: str, chapters: list[tuple[str, str]], out_path: Path) -> None:
    book = epub.EpubBook()
    book.set_identifier(f"md2epub-{abs(hash(book_title))}")
    book.set_title(book_title)
    book.set_language("zh-CN")

    css_item = epub.EpubItem(
        uid="style",
        file_name="style.css",
        media_type="text/css",
        content=CSS.encode("utf-8"),
    )
    book.add_item(css_item)

    md = markdown.Markdown(
        extensions=["extra", "sane_lists", "tables", "fenced_code", "nl2br"],
        output_format="html5",
    )
    items = []
    for idx, (title, body) in enumerate(chapters, start=1):
        body_html = md.convert(body)
        md.reset()
        chapter = epub.EpubHtml(
            title=title,
            file_name=f"p{idx:02d}.xhtml",
            lang="zh-CN",
        )
        chapter.content = f"<h1>{html.escape(title)}</h1>" + body_html
        chapter.add_item(css_item)
        book.add_item(chapter)
        items.append(chapter)

    book.toc = list(items)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + items
    epub.write_epub(str(out_path), book)


def main() -> None:
    parser = argparse.ArgumentParser(description="Markdown 系列讲稿 → 微信读书 EPUB")
    parser.add_argument("src", type=Path, help="合并好的全集讲稿 Markdown 文件")
    parser.add_argument("--out", type=Path, default=None, help="输出 epub 路径（默认同目录同名）")
    args = parser.parse_args()

    src: Path = args.src
    if not src.is_file():
        sys.exit(f"找不到输入文件：{src}")
    out = args.out or src.with_suffix(".epub")

    md_text = src.read_text(encoding="utf-8")
    chapters = split_chapters(md_text)
    if not chapters:
        sys.exit(f"未在 {src.name} 中找到任何 `# 一级标题`，无法分章。")

    # 书名优先取一号标题，否则用文件名。
    book_title = src.stem
    if md_text.strip().startswith("# "):
        first = md_text.strip().splitlines()[0].lstrip("# ").strip()
        if first:
            book_title = first

    build_epub(book_title, chapters, out)
    print(f"已生成：{out}（{out.stat().st_size} 字节，{len(chapters)} 章）")


if __name__ == "__main__":
    main()
