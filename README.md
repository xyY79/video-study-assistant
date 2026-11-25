# 视频学习助手 V2.1 — Markdown-native

将本地视频、音频、B站视频/合集或历史底稿重构为单文件高质量 Markdown 学习讲稿（Obsidian 原生）。默认完整精编，不以 ASR 底稿或简单摘要作为最终交付。

## V2.1 更新

- 六层原生 Markdown：YAML、导读、完整文章、表格/Callout/Mermaid、复习辅助、校勘。无 HTML/CSS/JS、图片附件或社区插件依赖。
- `SOURCE_READY → EDITED → ENHANCED → FORMAT_PASS → SEMANTIC_REVIEWED → COMPLETE`，缺任一必需阶段不得宣布完成；原始材料仅为中间产物，用户默认只收到一个阅读 Markdown。
- `check_lecture.py` 读取实际最终 Markdown，检测底稿直出、时间戳堆积、缺标点/章节、机械碎行、长段、外部依赖与 HTML。结构检查不是语义验收；需逐块对账及独立复核。
- 修复历史 Markdown 底稿全角/半角圆括号时间戳；保留 V2 的分块/覆盖审计、可选 FunASR 与热词、原 Whisper GPU/CPU 路径、评论双排序采样与 EPUB。
- 原创小型示例和回归用例随仓库发布；用户课程原文不公开。

## 使用

先按 [SKILL.md](SKILL.md) 执行。已存在底稿直接精编，不重复转写。上游依赖按 [integrations.md](references/integrations.md) 配置；原后端依赖 `python -m pip install -r requirements.txt`。Python 3.10+，可选上游 ASR 独立 Python 3.12。所有命令从项目根目录运行。

```powershell
python scripts/study_pipeline.py prepare "D:/video/raw.md" "D:/work/chunks.json"
# Agent 完成语义编辑、原生排版及 ledger 后
python scripts/study_pipeline.py audit "D:/work/chunks.json" "D:/work/ledger.json"
python scripts/check_lecture.py "D:/video/lecture.md" --source "D:/video/raw.md"
python -m unittest discover -s tests -v
```

原始转录、语义对账是工作材料；最终默认单个 Markdown。上游许可证与固定提交见 integrations.md。评论仅按需并注明样本限制。系列 EPUB 仍需用户明确批准；不保证所有 EPUB 阅读器渲染 Mermaid/Callout，文本解释保留。Windows GPU、联网 B站采集仍需本机验证；格式测试不代表任意新讲座已完成语义审核。
