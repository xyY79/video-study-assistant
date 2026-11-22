#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 faster-whisper 把本机视频/音频转写成带时间戳的文本。

用法:
  python transcribe.py <视频文件或文件夹> [--out 输出]
      [--model small|medium|large-v3] [--lang zh]
      [--device auto|cuda|cpu] [--compute-type auto|float16|int8|float32]

输出: 每行 "[hh:mm:ss.mmm] 文本"，UTF-8。
默认模型 small；默认自动优先尝试 CUDA + float16，失败后回退 CPU int8。
"""
import argparse
import os
import sys
from pathlib import Path


def register_cuda_dll_dirs() -> None:
    """Register pip-bundled CUDA DLL directories on Windows when present."""
    if not hasattr(os, "add_dll_directory"):
        return
    candidates = []
    for entry in sys.path:
        if not entry:
            continue
        root = Path(entry)
        candidates.extend(root.glob("nvidia/*/bin"))
    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        candidates.append(Path(cuda_path) / "bin")
    for directory in candidates:
        if directory.is_dir():
            try:
                os.add_dll_directory(str(directory))
            except OSError:
                pass


register_cuda_dll_dirs()

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


def load_model(
    model_name: str,
    device: str,
    compute_type: str,
    gpu_index: int,
    threads: int,
    allow_gpu_fallback: bool,
):
    """Load one reusable model and report the selected runtime."""
    if device not in {"auto", "cuda", "cpu"}:
        raise ValueError(f"unsupported device: {device}")

    if device in {"auto", "cuda"}:
        cuda_type = "float16" if compute_type == "auto" else compute_type
        try:
            model = WhisperModel(
                model_name,
                device="cuda",
                device_index=gpu_index,
                compute_type=cuda_type,
            )
            print(
                f"[transcribe] runtime: CUDA GPU {gpu_index}, {cuda_type}",
                flush=True,
            )
            return model
        except Exception as exc:
            if device == "cuda" and not allow_gpu_fallback:
                raise RuntimeError(
                    "CUDA 初始化失败；可移除 --device cuda 使用自动回退，"
                    f"或检查 NVIDIA 驱动/CUDA 运行库。原始错误：{exc}"
                ) from exc
            print(
                f"[transcribe] CUDA unavailable ({exc}); falling back to CPU int8",
                file=sys.stderr,
                flush=True,
            )

    cpu_type = "int8" if compute_type == "auto" else compute_type
    model = WhisperModel(
        model_name,
        device="cpu",
        compute_type=cpu_type,
        cpu_threads=threads,
    )
    print(
        f"[transcribe] runtime: CPU, {cpu_type}, threads={threads}",
        flush=True,
    )
    return model


def transcribe_file(
    video: Path,
    out: Path,
    model,
    language: str,
    vad: bool,
    prompt: str,
):
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
    ap.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cuda", "cpu"],
        help="运行设备；auto 优先 CUDA，失败后回退 CPU",
    )
    ap.add_argument(
        "--compute-type",
        default="auto",
        choices=["auto", "float16", "int8", "float32"],
        help="计算类型；auto 为 CUDA=float16、CPU=int8",
    )
    ap.add_argument("--gpu-index", type=int, default=0, help="CUDA GPU 编号")
    ap.add_argument(
        "--no-gpu-fallback",
        action="store_true",
        help="CUDA 初始化失败时直接报错，不回退到 CPU",
    )
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

    print(f"[transcribe] loading model {args.model} ...", flush=True)
    model = load_model(
        args.model,
        args.device,
        args.compute_type,
        args.gpu_index,
        args.threads,
        not args.no_gpu_fallback,
    )

    out_arg = Path(args.out) if args.out else None
    for t in targets:
        if out_arg is None:
            out = t.with_suffix(".txt")
        elif out_arg.suffix:
            out = out_arg
        else:
            out_arg.mkdir(parents=True, exist_ok=True)
            out = out_arg / (t.stem + ".txt")
        transcribe_file(t, out, model, args.lang, not args.no_vad, args.prompt)


if __name__ == "__main__":
    main()
