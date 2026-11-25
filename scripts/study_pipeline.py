#!/usr/bin/env python3
"""Offline preparation/audit and optional pinned upstream adapters for V2."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

AUDIO_REV = "759c3c6db646817bf94490ce9f73e8c6865462dd"
BILI_REV = "75d3c8c31c9fc94a3cbaba9cf574681231a1b113"
AUDIO_SCRIPT = "plugins/audio-transcriber/skills/audio-transcribe/scripts/transcribe.py"
BILI_SCRIPT = "scripts/fetch_video.py"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False, indent=2)
        out.write("\n")


def pinned_script(repo, rev, script):
    repo = Path(repo).resolve()
    head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"], text=True).strip()
    if head != rev or dirty:
        raise ValueError("Upstream checkout must be clean and pinned to " + rev)
    path = repo / script
    if not path.is_file():
        raise ValueError("Missing upstream script: " + str(path))
    return path


def prepare(src, output, size=4000):
    if size < 256:
        raise ValueError("chunk size must be >=256")
    src = Path(src)
    text = src.read_text(encoding="utf-8-sig")
    rows = []
    if src.suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, list):
            for r in data:
                rows.append((str(r["text"]), r.get("start_ms"), r.get("end_ms"), r.get("speaker")))
        else:
            for r in (data.get("transcript") or {}).get("lines", []):
                rows.append((r["content"], round(r["from"] * 1000), round(r["to"] * 1000), None))
    else:
        for line in text.splitlines():
            m = re.match(r"^\s*[\[(（](\d+):(\d{2}):(\d{2})(?:\.(\d{1,3}))?[\])）]\s*(.*)$", line)
            if m:
                h, minute, sec, ms, body = m.groups()
                rows.append((body, ((int(h)*60+int(minute))*60+int(sec))*1000+int((ms or "0").ljust(3,"0")), None, None))
            else:
                rows.append((line, None, None, None))
    chunks, current, used, serial = [], [], 0, 0
    for body, start, end, speaker in rows:
        if not body.strip():
            continue
        for offset in range(0, len(body), size):
            piece = body[offset:offset+size]
            if current and used + len(piece) > size:
                chunks.append(current)
                current, used = [], 0
            serial += 1
            current.append(dict(id=f"S{serial:06}", text=piece, start_ms=start, end_ms=end, speaker=speaker))
            used += len(piece)
    if current:
        chunks.append(current)
    if not chunks:
        raise ValueError("No source text; do not create an empty lecture")
    write_json(output, dict(source=src.name, sha256=hashlib.sha256(src.read_bytes()).hexdigest(), segments=serial, chunks=[dict(id=f"C{i:04}", segments=c) for i,c in enumerate(chunks,1)]))


def audit(prepared, ledger):
    expected = {r["id"] for c in read_json(prepared)["chunks"] for r in c["segments"]}
    entries = read_json(ledger)
    seen, errors = set(), []
    for r in entries:
        key = r.get("id")
        if key not in expected or key in seen:
            errors.append(f"unexpected or duplicate ID: {key}")
        seen.add(key)
        if r.get("status") not in ("retained", "noise", "uncertain") or not str(r.get("detail") or "").strip():
            errors.append(f"missing status/detail: {key}")
    if expected-seen:
        errors.append("missing: " + ", ".join(sorted(expected-seen)))
    if errors:
        raise ValueError("; ".join(errors))
    return {"coverage": "PASS", "segments": len(expected), "uncertain": sum(r["status"]=="uncertain" for r in entries), "semantic_review": "required separately"}


def run_asr(args):
    script = pinned_script(args.repo, AUDIO_REV, AUDIO_SCRIPT)
    source = Path(args.source).resolve(strict=True)
    output = Path(args.output).resolve()
    if output.exists():
        raise FileExistsError(output)
    python = str(Path(args.python).resolve()) if args.python != sys.executable else sys.executable
    with tempfile.TemporaryDirectory() as temp:
        audio = Path(temp)/"audio.wav"
        raw = Path(temp)/"raw.json"
        subprocess.run(["ffmpeg","-nostdin","-v","error","-i",str(source),"-ar","16000","-ac","1","-sample_fmt","s16",str(audio)], check=True)
        cmd = [python,str(script),str(audio),"--lang","zh","--phase1-only","--skip-preprocess","--json-out",str(raw)]
        if args.hotwords:
            hotword_path = Path(args.hotwords)
            cmd += ["--hotwords", str(hotword_path.resolve()) if hotword_path.is_file() else args.hotwords]
        if args.speakers:
            cmd += ["--num-speakers", str(args.speakers)]
        if args.device:
            cmd += ["--device",args.device]
            if args.device == "cpu":
                cmd += ["--batch-size","60"]
        subprocess.run(cmd, cwd=temp, check=True)
        rows = read_json(raw)
        if not isinstance(rows,list) or not any(str(r.get("text") or "").strip() for r in rows):
            raise ValueError("Empty or invalid ASR output")
        write_json(output, rows)


def merge_comments(samples):
    merged, coverage = {}, []
    for lane, limit, data in samples:
        comments = data.get("comments") or []
        coverage.append(dict(sort=lane, requested_top=limit, returned_top=sum(not c.get("is_reply") for c in comments), returned_replies=sum(bool(c.get("is_reply")) for c in comments), reported_total=data.get("comments_total"), completeness="unverified"))
        for c in comments:
            rid = c.get("rpid")
            if rid is None:
                continue
            key = str(rid)
            if key not in merged:
                merged[key] = {k:c.get(k) for k in ("rpid","content","likes","rcount","is_reply","ctime","kind","pictures","emotes")}
                merged[key]["sorts"] = []
            if lane not in merged[key]["sorts"]:
                merged[key]["sorts"].append(lane)
    return {"coverage":coverage, "unique_comments":len(merged), "limits":"Sample only; upstream embeds up to three replies per parent and omits parent IDs. Image contents not examined.", "comments":list(merged.values())}


def run_comments(args):
    script = pinned_script(args.repo, BILI_REV, BILI_SCRIPT)
    if Path(args.output).exists():
        raise FileExistsError(args.output)
    if not re.fullmatch(r"BV[0-9A-Za-z]{10}",args.bvid):
        raise ValueError("Pass a resolved BV ID")
    samples, errors = [], []
    for lane, limit in (("hot",args.hot),("time",args.recent)):
        if limit <= 0:
            raise ValueError("Both sample budgets must be positive")
        with tempfile.TemporaryDirectory() as temp:
            try:
                subprocess.run([sys.executable,str(script),args.bvid,"--no-subtitle","--sort",lane,"--comments",str(limit),"--out",temp],cwd=temp,check=True)
                samples.append((lane,limit,read_json(Path(temp)/(args.bvid+".json"))))
            except (OSError, ValueError, subprocess.CalledProcessError) as exc:
                errors.append({"sort":lane,"error":type(exc).__name__})
                break  # do not keep requesting after a possible access restriction
    result = merge_comments(samples)
    result.update(bvid=args.bvid, errors=errors, status="sampled" if len(samples)==2 and all(c["returned_top"]>0 for c in result["coverage"]) else "partial_or_unavailable")
    write_json(args.output,result)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("prepare"); a.add_argument("source"); a.add_argument("output"); a.add_argument("--size",type=int,default=4000)
    a=sub.add_parser("audit"); a.add_argument("prepared"); a.add_argument("ledger")
    a=sub.add_parser("asr"); a.add_argument("source"); a.add_argument("output"); a.add_argument("--repo",required=True); a.add_argument("--python",default=sys.executable); a.add_argument("--hotwords"); a.add_argument("--speakers",type=int); a.add_argument("--device")
    a=sub.add_parser("comments"); a.add_argument("bvid"); a.add_argument("output"); a.add_argument("--repo",required=True); a.add_argument("--hot",type=int,default=120); a.add_argument("--recent",type=int,default=240)
    args=p.parse_args()
    if args.cmd=="prepare": prepare(args.source,args.output,args.size)
    elif args.cmd=="audit": print(json.dumps(audit(args.prepared,args.ledger),ensure_ascii=False))
    elif args.cmd=="asr": run_asr(args)
    else: run_comments(args)


if __name__=="__main__":
    main()
