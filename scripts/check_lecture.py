#!/usr/bin/env python3
"""Validate the actual Markdown deliverable. Structural checks only, not semantic QA."""
import argparse
import json
import re
import sys
from pathlib import Path

TS = re.compile(r'^\s*(?:[-*]\s+)?(?:\[\d+:\d{2}(?::\d{2})?(?:\.\d{1,3})?\]|\(\d+:\d{2}(?::\d{2})?(?:\.\d{1,3})?\)|（\d+:\d{2}(?::\d{2})?(?:\.\d{1,3})?）)\s*')
CJK = re.compile(r'[\u3400-\u9fff]')
PUNCT = re.compile(r'[。！？；，、：]')
HTML = re.compile(r'<\s*/?\s*(?:[A-Za-z][\w:-]*)(?:\s[^<>]*|\s*)/?>|<!--', re.I)
IMAGE = re.compile(r'!\[[^\]]*\]\s*(?:\([^\n]*\)|\[[^\]]*\])|!\[\[[^\]]+\]\]')
FENCE = re.compile(r'^\s*(`{3,}|~{3,})(.*)$')
HEADING = re.compile(r'^(#{1,6})\s+(.+)')


def cjk_count(text):
    return len(CJK.findall(text))


def strip_raw(text):
    return ''.join(TS.sub('', line) for line in text.splitlines())


def inspect(text, source=None):
    errors, warnings = [], []
    lines = text.lstrip('\ufeff').splitlines()
    if not lines or lines[0] != '---':
        errors.append('missing YAML frontmatter')
    else:
        try:
            end = lines.index('---', 1)
            if not any(re.match(r'^title:\s*\S', line) for line in lines[1:end]):
                errors.append('frontmatter missing title')
            lines = lines[end+1:]
        except ValueError:
            errors.append('unclosed YAML frontmatter')
    visible, prose, headings, paragraphs = [], [], [], []
    fence = None
    paragraph = []
    mermaid, callouts, tables, timestamp_rows = 0, 0, 0, 0

    def flush():
        if paragraph:
            paragraphs.append(' '.join(paragraph))
            paragraph.clear()

    for line in lines:
        m = FENCE.match(line)
        if fence:
            if m and m[1][0] == fence[0] and len(m[1]) >= len(fence) and not m[2].strip():
                fence = None
            continue
        if m:
            flush()
            fence = m[1]
            lang = m[2].strip().lower().split()[0] if m[2].strip() else ''
            mermaid += lang == 'mermaid'
            if lang in {'html', 'css', 'javascript', 'js', 'dataview', 'dataviewjs'}:
                # Code examples from the lecture are allowed as text, but executable plugin blocks are not.
                if lang in {'dataview', 'dataviewjs'}:
                    errors.append('plugin-dependent code block')
            continue
        visible.append(line)
        if TS.match(line):
            timestamp_rows += 1
        h = HEADING.match(line)
        if h:
            headings.append((len(h[1]), h[2]))
        callouts += bool(re.match(r'^\s*>\s*\[!\w+\]', line))
        tables += bool(re.match(r'^\s*\|.*\|\s*$', line))
        if not line.strip() or re.match(r'^\s*(?:#|>|\||[-*+]\s|\d+[.)]\s|---\s*$|\*原视频)', line):
            flush()
            continue
        prose.append(line.strip())
        paragraph.append(line.strip())
    flush()
    if fence:
        errors.append('unclosed fenced block')
    visible_text = '\n'.join(visible)
    if HTML.search(visible_text):
        errors.append('raw HTML is not allowed')
    if IMAGE.search(visible_text):
        errors.append('image/attachment embed is not allowed')
    if re.search(r'\]\(\s*(?:javascript:|data:)', visible_text, re.I):
        errors.append('executable or embedded-data link')
    h1 = sum(level == 1 for level, _ in headings)
    h2 = sum(level == 2 for level, _ in headings)
    if h1 != 1:
        errors.append('expected exactly one H1 for a single lecture')
    body = '\n'.join(prose)
    nch = cjk_count(body)
    source_nch = cjk_count(strip_raw(source)) if source is not None else 0
    # A long source must not be represented by a single undifferentiated wall of text.
    long_form = max(nch, source_nch) >= 4000
    if long_form and h2 < 2:
        errors.append('long lecture needs multiple thematic H2 sections')
    if long_form and not re.search(r'^\s*>\s*\[!abstract\]', visible_text, re.M | re.I):
        errors.append('long lecture needs a short abstract callout')
    if long_form and not re.search(r'^#{2,3}\s+.*(?:复习|自测|主动回忆|学习辅助|学习清单|行动清单)', visible_text, re.M):
        errors.append('long lecture needs a learning/review section')
    if nch < 60 and source_nch >= 200:
        errors.append('too little article prose for the supplied source')
    if nch >= 150 and len(PUNCT.findall(body)) / nch < 0.012:
        errors.append('Chinese prose lacks punctuation')
    short = sum(0 < cjk_count(line) <= 18 and not PUNCT.search(line) for line in prose)
    if len(prose) >= 20 and short / len(prose) > 0.45:
        errors.append('too many mechanical short fragments')
    if timestamp_rows > max(3, h2):
        errors.append('dense per-line timestamps: use thematic ranges')
    longest = max((cjk_count(p) for p in paragraphs), default=0)
    if longest > 700:
        errors.append('paragraph exceeds 700 Chinese characters')
    if longest > 300:
        warnings.append('long paragraph: review readability')
    if source is not None:
        normalized = lambda s: ''.join(CJK.findall(strip_raw(s)))
        a, b = normalized(source), normalized(visible_text)
        if a and a == b and len(a) >= 100:
            errors.append('deliverable repeats the raw source without editing')
        if source_nch >= 4000 and nch < source_nch * 0.20:
            warnings.append('very short prose relative to source: review for summary-only output; ratio is not a fidelity criterion')
    if mermaid and not prose:
        errors.append('diagram must have a human-readable text explanation')
    return {'status': 'FAIL' if errors else 'FORMAT_PASS', 'errors': errors, 'warnings': warnings,
            'metrics': {'h1': h1, 'h2': h2, 'prose_cjk': nch, 'source_cjk': source_nch,
                        'timestamp_rows': timestamp_rows, 'short_fragments': short, 'prose_lines': len(prose),
                        'max_paragraph_cjk': longest, 'callouts': callouts, 'mermaid': mermaid,
                        'table_rows': tables}, 'semantic_review': 'required separately'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('lecture', type=Path)
    p.add_argument('--source', type=Path, required=True)
    args = p.parse_args()
    report = inspect(args.lecture.read_text(encoding='utf-8-sig'), args.source.read_text(encoding='utf-8-sig'))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report['status'] == 'FAIL' else 0


if __name__ == '__main__':
    sys.exit(main())
