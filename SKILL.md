---
name: video-study-assistant
description: 将本地视频、音频、B站视频或合集、已有ASR转录稿转换为单文件高可读 Markdown-native 精编讲稿，适合 Obsidian 阅读、检索、复习及迁移。用户要求视频转文字、整理讲稿、课程精读、评论知识挖掘、学习笔记或微信读书 EPUB 时使用。
---

# 视频学习助手 V2.1（Markdown-native）

默认目标：交付可直接学习的完整课程文章，而非转录底稿或摘要。用户只给视频路径、链接或说“转文字”时，仍默认完成精编；只有明确要求仅逐字稿时才允许在原始转录阶段结束。默认每集仅交付一个自包含 UTF-8 Markdown 文件，不生成 HTML、CSS、JS、图片或其他阅读附件。原始媒体和既有底稿永不覆盖或删除；工作记录放在临时工作区或独立内部缓存，不作为用户的阅读交付物。

## 强制执行链

1. **SOURCE_READY**：核对输入、集号、源文件和实际存在的分P。已有 TXT/MD/JSON 底稿直接使用，禁止重复下载/ASR。在线视频先检查可靠人工字幕；没有则使用现有 yt-dlp/ffmpeg。中文优先尝试已验证的 audio-transcriber/FunASR（热词、可选说话人），失败如实记录并回退 scripts/transcribe.py，资源允许用 large-v3、资源不足用 small，保留 CUDA/CPU 自动策略。见 [上游适配](references/integrations.md)。原始转录不是讲稿。
2. **EDITED**：执行 scripts/study_pipeline.py prepare RAW CHUNKS.json；通读主题、逐块语义纠错、去口水话、合并碎句与冗余、按论证重构全文。必须阅读 [精编规范](references/refinement.md) 和 [Markdown-native 样式与示例](references/markdown-native.md)。保留全部有效观点、论证、案例、数字、限定与归属；不把摘要当正文。对长讲座每块保存语义去向 ledger，并做跨块合并与全文一致性检查。不得逐条时间戳输出。保留未能核实的关键内容并集中说明。
3. **ENHANCED**：在同一 Markdown 内完成 YAML 属性、标题、短导读、完整精编正文、必要对比表格/Callout/Mermaid（伴随文字解释）、学习辅助、来源/校勘。按内容决定组件，不机械凑数量。仅用户要求评论时，执行 scripts/study_pipeline.py comments BV OUTPUT.json --repo LOCAL_BILI_CHECKOUT；按 [评论价值筛选](references/comments.md) 处理热度与时间双样本，将有效评论与主讲内容分开写入同一文件，标明证据与采样限制；不可因评论不可用阻断正文。
4. **FORMAT_PASS**：必须实际运行 `python scripts/check_lecture.py FINAL.md --source RAW`，长篇分块还必须运行 `python scripts/study_pipeline.py audit CHUNKS.json LEDGER.json`。检查器读最终文件，不读 Agent 自报；不通过则修复再运行。不能用改标题、加导读或给原稿加标点来通过。脚本仅检查结构与覆盖，不证明语义忠实。
5. **SEMANTIC_REVIEWED**：独立审查上下文或子代理逐块对照底稿、正文、校勘，核对信息覆盖、逻辑、归属及可读性，发现问题返工。若无法完成独立审查或关键语义仍不确定，标明 PARTIAL，不能宣布 COMPLETE。音频不在时可交付文本精编，但注明未回听；未核实的细节不得伪造。
6. **COMPLETE**：只有最终文件已写入、格式检查通过、语义审查无重大遗漏及未解决关键歧义，才可宣布完成并提供文件。长任务逐集断点续做、必要时并行编辑，不得因为时长或 token 压力降级为底稿。未完成则报告进度和剩余项；不将 PARTIAL 当最终阅读稿。仅在质量验收后按原规则清理本次在线下载的媒体及临时产物，精确列出目标并确认归属；本地原始视频/音频和既有底稿不删。

## 交付及系列

- 单集：`讲稿-第N集-标题.md`。导读、全文、图表、复习与校勘均写在此文件；不要额外生成摘要、HTML、图像、JSON、审计报告供用户阅读。保留原始转录及必要的内部工作记录，不把内部文件塞进正文或交付列表。源文件和既有结果不得覆盖。
- 系列：逐集完成后按真实集号生成一份全集 Markdown（用户需要时），综合学习归纳可置于全集末尾；不重复嵌入 YAML，使用每集一个 H1、主题 H2/H3。若用户明确要求独立报告再另交付。
- 微信读书：仅整套系列验收完成并获得当前系列明确批准后，使用原 scripts/md_to_epub.py 转换；保留 Markdown 和 EPUB。Mermaid 在不渲染的阅读器中以文字解释为准；无需另制图片。未批准不得转换。
- 汇报使用的实际版本、输入、最终文件、检查结果、未核实项及可选评论范围；不能用 ASR 完成率替代精编完成率。
