# 视频学习助手 V2.0（候选版）

将本地视频、B站视频/合集或历史转录转为高质量忠实精编讲稿、短导读、综合报告与可选 EPUB。重点是学习效率，不是逐字转录。

## V2变化

- 可选接入固定版本的 audio-transcriber 中文ASR（本地 FunASR + 热词 + 说话人），保留原 faster-whisper GPU/CPU fallback 脚本。
- 使用主 Agent 的独立忠实精编与语义验收工作流；不是自动调用额外付费 LLM API。基于用户需求独立编写规则，不再分发 pinshu-transcript 的受限材料。
- 使用 bilibili-video-analysis-summary 双排序评论采样并按知识增量、论证、相关性筛选；非全量评论。
- 新增带片段ID、输入哈希、时间戳的长文本分块，以及覆盖对账脚本。
- 保留Markdown、系列EPUB批准门槛、本地源保护与在线临时媒体清理规则，清理延迟到质量验收之后。

## 使用

Python 3.10+（原后端）；可选 audio-transcriber 独立 Python 3.12 环境。安装原依赖：
```powershell
python -m pip install -r requirements.txt
```
B站需要 yt-dlp、ffmpeg。详细配置见 [上游适配](references/integrations.md)。不要直接安装整套上游插件；上游 checkout 需固定版本。默认使用主 SKILL.md 调度。

```powershell
# 原后端仍可使用
python scripts/transcribe.py "D:/video/lecture.mp4" --model large-v3 --out "D:/video/raw.txt"
# 历史稿可跳过ASR
python scripts/study_pipeline.py prepare "D:/video/raw.txt" "D:/video/chunks.json"
# Agent完成精编与ledger后检查覆盖
python scripts/study_pipeline.py audit "D:/video/chunks.json" "D:/video/ledger.json"
python -m unittest discover -s tests -v
```

输出 lecture/讲稿、导读和综合报告，保留原始转写和审计材料；评论按需。完整操作见 [SKILL.md](SKILL.md)。只在用户批准后运行原 md_to_epub.py。

## 验证与限制

本次候选版新增脚本已在离线环境进行3项单元测试：文本分块与覆盖门槛、两类JSON转写格式、双排序合并与低赞保留。尚未在真实 Windows/NVIDIA/FunASR、B站联网场景执行端到端验证；未测项不得称作已通过。评论上游仅附带部分子回复，不提供父评论ID。Agent语义质量仍需真实样例和独立验收，覆盖脚本并非准确性证明。

## 上游及许可证

仅上述三个项目；实际适配为外部固定版本 checkout 和本项目原创规则，不捆绑上游源码。见 [上游适配](references/integrations.md)。原脚本及原 requirements.txt 保持不变。
