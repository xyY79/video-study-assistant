# V2 上游适配与安装（Windows）

本项目不捆绑三个上游的源码，不自动下载、安装或执行未经审查的脚本。先审查所固定版本的源码和许可证，再在用户指定目录建立独立 checkout。只有需要的后端才配置。所有命令从本项目根目录运行，路径改为真实路径。

## 1. audio-transcriber（MIT）

来源：https://github.com/zxkane/audio-transcriber
固定提交：759c3c6db646817bf94490ce9f73e8c6865462dd
用途：可选本地中文 ASR（FunASR SeACo-Paraformer）、热词、标点与说话人分离。只运行 phase1，不启用上游云端LLM；主Agent执行本项目精编。保留原 faster-whisper 后端。上游报告要求 Python 3.12；其 setup_env.sh 针对 Unix，不能在 Windows 直接照搬。按其安装说明审查依赖，独立虚拟环境安装与本机匹配的 PyTorch/torchaudio，再配置 funasr、modelscope、boto3、scikit-learn、soundfile；检查 ffmpeg、torch.cuda.is_available()、ASR模型可加载。若需长音频聚类优化，先审查上游 patch_clustering.py，禁止无审查修改环境。未验证成功使用V1.1后端并记录。不要下载可选MiMo大模型。

```powershell
git clone https://github.com/zxkane/audio-transcriber.git D:/video-upstream/audio-transcriber
git -C D:/video-upstream/audio-transcriber checkout --detach 759c3c6db646817bf94490ce9f73e8c6865462dd
python scripts/study_pipeline.py asr "D:/video/lecture.mp4" "D:/video/raw.json" --repo "D:/video-upstream/audio-transcriber" --python "D:/video-upstream/asr-venv/Scripts/python.exe" --hotwords "CFD RANS OpenFOAM"
```

需要时传 --speakers 2 或 --device cuda:0 / cpu。--python 需指向已安装依赖的解释器绝对路径。FFmpeg 位于PATH。ASR本身可能下载模型，须获得网络/资源授权。没有安装上游时直接使用原 scripts/transcribe.py，建议 --model large-v3（资源允许）或 small。

## 2. bilibili-video-analysis-summary（MIT）

来源：https://github.com/DavidLearning1023/bilibili-video-analysis-summary
固定提交：75d3c8c31c9fc94a3cbaba9cf574681231a1b113
用途：复用 scripts/fetch_video.py 的公开评论接口；按热度和时间两个独立样本采集去重。不需要上游MCP或其HTML/PDF模块。不复制评论图片或个人资料字段。只在用户要求评论时执行，尊重平台访问条件、限速与访问限制，失败停止或报告，不绕过访问控制。不请求或记录账号密码、Cookie；上游可能读取本机已有B站配置，先核查配置并获得授权，默认不配置登录。上游可能在分页错误后静默返回部分结果，所以完整性始终未确认。

```powershell
git clone https://github.com/DavidLearning1023/bilibili-video-analysis-summary.git D:/video-upstream/bili-analysis
git -C D:/video-upstream/bili-analysis checkout --detach 75d3c8c31c9fc94a3cbaba9cf574681231a1b113
python scripts/study_pipeline.py comments BV1xxxxxxxxx "D:/video/comments_raw.json" --repo "D:/video-upstream/bili-analysis" --hot 120 --recent 240
```

示例BV须替换。上游抓取脚本支持 --comments 0 --page N 单独检查字幕，按授权情况使用；字幕质量不可靠则转写。评论采样不是全量；如果需要完全楼中楼，目前不支持。两个样本均不可用时保留主讲稿并报告失败。

## 3. pinshu-transcript（内部使用许可）

来源：https://github.com/zhongjjm-design/pinshu-skills/tree/main/pinshu-transcript
核查提交：3381f9093eca7e5a9be7eaf546923c5ccc127338
许可证：https://github.com/zhongjjm-design/pinshu-skills/blob/3381f9093eca7e5a9be7eaf546923c5ccc127338/LICENSE

仅以其功能作为需求参照；公开仓库不分发其源码、修改稿或专属模板。用户如需要在个人设备使用原版，可自行按许可证另行安装，仅供许可范围内使用；不得上传其内容到本公开仓库。V2主流程独立使用本项目编写的 refinement.md，不依赖该Skill的自动触发。

## 离线准备与审计

```powershell
python scripts/study_pipeline.py prepare "D:/video/raw.json" "D:/video/chunks.json"
python scripts/study_pipeline.py audit "D:/video/chunks.json" "D:/video/ledger.json"
python -m unittest discover -s tests -v
```

prepare 支持 V1 时间戳 TXT、无时间戳 TXT、上游 audio-transcriber 原始数组及 fetch_video.py 字幕 JSON；audit 仅检查每个片段的状态和覆盖，不提供自动语义判定。输出均拒绝覆盖已有文件；重做时选择新文件名。禁止在未授权情况下把私有音视频发送给第三方服务。
