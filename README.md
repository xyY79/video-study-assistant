# 视频学习助手

这是一个面向 Codex/ChatGPT Skills 的视频学习整理工具。它把本地课程、讲座或 B 站视频/合集转换成可通读的逐集讲稿，并进一步生成综合学习报告。

## 能做什么

- 本地视频或视频文件夹：语音转写、保留时间戳、整理成逐集 Markdown 讲稿。
- B 站视频或合集：解析分 P、下载、转写；按需抓取热评和评论区，形成“主讲人观点 + 评论区讨论”的综合报告。
- 系列完成后：在用户明确批准的前提下，把全集讲稿转换为可导入微信读书的 EPUB3。

本仓库中的 `SKILL.md` 是技能的工作流说明；`scripts/` 提供实际执行转写和 Markdown→EPUB 的 Python 脚本。

## 目录

```text
.
├── SKILL.md
├── agents/
│   └── openai.yaml
├── scripts/
│   ├── transcribe.py
│   └── md_to_epub.py
├── requirements.txt
└── .gitignore
```

## 安装依赖

建议使用 Python 3.10 或更高版本，并在虚拟环境中安装：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

如果要处理 B 站内容，还需要在系统中准备：

- `yt-dlp`
- `ffmpeg`

首次使用 `faster-whisper` 时，模型可能需要下载；之后可以复用本地模型缓存。

## 单独运行转写脚本

处理单个视频或音频：

```powershell
python scripts/transcribe.py "D:\videos\lecture.mp4" --out "D:\videos\lecture.txt"
```

处理一个文件夹中的视频：

```powershell
python scripts/transcribe.py "D:\videos\course" --out "D:\videos\course\transcripts"
```

默认使用中文、CPU `int8` 和 `small` 模型，并输出形如下面的带时间戳文本：

```text
[00:00:12.340] 这里是转写内容。
```

可以通过 `--model tiny|base|small|medium|large-v3` 选择模型，通过 `--lang` 指定语言。CPU 转写是长任务，视频较多时建议逐个顺序处理。

## Markdown 转 EPUB

准备好按集数合并的全集讲稿 Markdown 后：

```powershell
python scripts/md_to_epub.py "D:\course\课程-全集讲稿.md"
```

脚本按一级标题 `# ...` 分章，生成带可点击目录的 EPUB3。只有在整个系列讲稿完成并获得用户明确批准后，才应执行这一步。

## 作为 Codex Skill 使用

将本仓库作为技能目录安装或复制到 Codex 的 skills 目录后，技能会在用户提供以下内容时触发：

- 本地视频文件或视频文件夹，并要求转文字、整理讲稿或总结；
- B 站视频/合集链接，并要求下载、转写或生成观点报告；
- 要求把讲稿整理为适合学习、精读或研究的 Markdown 材料。

完整的入口规则、文件命名、清理策略和 EPUB 审批要求见 [`SKILL.md`](SKILL.md)。

## 重要说明

- 本地视频默认不删除。
- B 站在线内容处理完成后，默认删除本次下载的视频和临时文件，只保留文字交付物及评论区溯源文本。
- 删除前必须精确核对路径，不能使用宽泛的递归删除。
- 评论区内容只作为补充材料，不应自动视为事实或替代主讲内容。
- 本项目不包含任何视频、模型权重、下载缓存或用户个人材料。
