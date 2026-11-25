import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('check', Path(__file__).resolve().parents[1] / 'scripts' / 'check_lecture.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

GOOD = '''---
title: 任务与恢复
---
# 任务与恢复

> [!abstract] 核心观点
> 专注不意味着永不休息。

## 任务的连续性

讲者认为，持续投入并不要求完全不休息。工作期间可以适当休息，结束后再回到原来的任务。重要的是恢复工作状态，而不是机械增加坐在桌前的时间。

## 学习辅助

| 状态 | 做法 |
|---|---|
| 工作 | 聚焦任务 |
| 休息 | 主动恢复 |

```mermaid
flowchart LR
 A[工作] --> B[休息] --> C[恢复]
```

工作与休息交替，休息结束后恢复原任务。

- [ ] 记录需要恢复的任务状态。
'''
RAW = '\n'.join(f'（00:00:{i:02d}）就是那个我们要去做' for i in range(60))


class FormatTests(unittest.TestCase):
    def test_raw_rejected(self):
        self.assertEqual(check.inspect(RAW, RAW)['status'], 'FAIL')

    def test_disguised_raw_rejected(self):
        text = '---\ntitle: 任务\n---\n# 任务\n\n## 观点\n\n' + RAW
        self.assertIn('dense per-line timestamps: use thematic ranges', check.inspect(text, RAW)['errors'])

    def test_native_pass(self):
        self.assertEqual(check.inspect(GOOD, RAW)['status'], 'FORMAT_PASS')

    def test_external_embed_and_html(self):
        self.assertEqual(check.inspect(GOOD + '\n![[attachment.png]]\n<div>text</div>\n', RAW)['status'], 'FAIL')
        self.assertEqual(check.inspect(GOOD + '\n![图](https://example.com/a.png)\n', RAW)['status'], 'FAIL')

    def test_literal_code_not_html(self):
        self.assertEqual(check.inspect(GOOD + '\n```html\n<div>demo</div>\n```\n', RAW)['status'], 'FORMAT_PASS')

    def test_long_source_needs_review(self):
        bad = GOOD.replace('## 学习辅助','## 其他')
        report = check.inspect(bad, RAW*20)
        self.assertIn('long lecture needs a learning/review section', report['errors'])

    def test_unclosed_fence(self):
        self.assertIn('unclosed fenced block', check.inspect(GOOD + '\n```mermaid\n', RAW)['errors'])

    def test_raw_markers(self):
        for line in ['[00:01:02.125] 文字', '(00:01:02) 文字', '（00:01:02）文字']:
            self.assertEqual(check.strip_raw(line), '文字')


if __name__ == '__main__':
    unittest.main()
