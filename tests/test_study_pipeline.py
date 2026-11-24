import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("pipeline", Path(__file__).resolve().parents[1]/"scripts"/"study_pipeline.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class StudyTests(unittest.TestCase):
    def test_prepare_and_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            src=root/"raw.txt"; src.write_text("[00:00:01.250] " + "甲"*600 + "\n[00:00:03] 乙\n丙",encoding="utf-8")
            out=root/"chunks.json"; p.prepare(src,out,256)
            data=p.read_json(out); rows=[r for c in data["chunks"] for r in c["segments"]]
            self.assertEqual("".join(r["text"] for r in rows),"甲"*600+"乙丙")
            self.assertEqual(rows[0]["start_ms"],1250)
            self.assertEqual(rows[-1]["start_ms"],None)
            self.assertTrue(all(sum(len(r["text"]) for r in c["segments"])<=256 for c in data["chunks"]))
            ledger=root/"ledger.json"; entries=[dict(id=r["id"],status="retained",detail="section A") for r in rows]
            p.write_json(ledger,entries)
            self.assertEqual(p.audit(out,ledger)["coverage"],"PASS")
            ledger.unlink(); p.write_json(ledger,entries[:-1]); self.assertRaises(ValueError,p.audit,out,ledger)
            self.assertRaises(FileExistsError,p.prepare,src,out,256)

    def test_asr_and_subtitle_formats(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for i,data in enumerate(([dict(text="甲",start_ms=12,end_ms=34,speaker=1)],{"transcript":{"lines":[{"content":"甲","from":0.012,"to":0.034}]}})):
                src=root/f"{i}.json"; out=root/f"{i}-chunks.json"; p.write_json(src,data); p.prepare(src,out)
                self.assertEqual(p.read_json(out)["chunks"][0]["segments"][0]["end_ms"],34)

    def test_comments_merge(self):
        hot={"comments":[dict(rpid=1,content="hot",likes=99,location="private")]}
        time={"comments":[dict(rpid=1,content="hot",likes=99),dict(rpid=2,content="new",likes=0),dict(rpid=3,is_reply=True,content="reply")]}
        result=p.merge_comments([("hot",120,hot),("time",240,time)])
        self.assertEqual(result["unique_comments"],3)
        self.assertEqual(result["comments"][0]["sorts"],["hot","time"])
        self.assertNotIn("location",result["comments"][0])
        self.assertEqual(result["coverage"][1]["returned_replies"],1)
        self.assertEqual(result["comments"][1]["likes"],0)
        self.assertEqual(result["coverage"][0]["completeness"],"unverified")


if __name__=="__main__": unittest.main()
