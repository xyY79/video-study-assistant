#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 faster-whisper 把本机视频/音频转写成带时间戳的文本。

用法:
  python transcribe.py <视频文件或文件夹> [--out 输出] [--model small|medium|large-v3] [--lang zh]

输出: 每行 "[hh:mm:ss.mmm] 文本"，UTF-8。
默认模型 small（Systran/faster-whisper-small，本机已缓存），CPU int8。
"""
import argparse
import sys
from pathlib import Path

from faster_whisper import WhisperModel

VIDEO_EXTS = {
    ".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm",
    ".m4a", ".mp3", ".aac", ".wav", ".flac", ".m4s", ".ts",
}


def fmt_ts(sec: float) -> str:
    ms = max(0, int(round(sec * 1000)))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, mi = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{mi:03d}"


def transcribe_file(video: Path, out: Path, model_name: str, language: str, threads: int, vad: bool, prompt: str):
    print(f"[transcribe] loading model {model_name} ...", flush=True)
    model = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=threads)
    print(f"[transcribe] {video.name} -> {out.name}", flush=True)
    segments, _info = model.transcribe(
        str(video),
        language=language,
        beam_size=5,
        vad_filter=vad,
        initial_prompt=prompt,
    )
    count = 0
    with open(out, "w", encoding="utf-8") as f:
        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue
            f.write(f"[{fmt_ts(seg.start)}] {text}\n")
            count += 1
    print(f"[transcribe] done: {out.name} ({count} lines)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="视频/音频文件或包含视频的文件夹")
    ap.add_argument("--out", default=None, help="输出 txt；对文件夹输入时表示输出目录")
    ap.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large-v3"])
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--no-vad", action="store_true", help="关闭 VAD 过滤")
    ap.add_argument("--prompt", default="请使用简体中文输出。", help="initial_prompt，提示输出风格；传空字符串禁用")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"[transcribe] not found: {src}", file=sys.stderr)
        sys.exit(2)

    targets = sorted(p for p in src.iterdir() if p.suffix.lower() in VIDEO_EXTS) if src.is_dir() else [src]
    if not targets:
        print(f"[transcribe] no video files in {src}", file=sys.stderr)
        sys.exit(2)

    out_arg = Path(args.out) if args.out else None
    for t in targets:
        if out_arg is None:
            out = t.with_suffix(".txt")
        elif out_arg.suffix:
            out = out_arg
        else:
            out_arg.mkdir(parents=True, exist_ok=True)
            out = out_arg / (t.stem + ".txt")
        transcribe_file(t, out, args.model, args.lang, args.threads, not args.no_vad, args.prompt)


if __name__ == "__main__":
    main()
