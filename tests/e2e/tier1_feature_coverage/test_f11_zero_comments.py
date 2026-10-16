import unittest
import os
import io
import tokenize

class TestF11ZeroComments(unittest.TestCase):
    def setUp(self):
        self.tests_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def test_f11_no_hash_comments_in_test_files(self):
        violations = []
        for root, _, files in os.walk(self.tests_dir):
            for f in files:
                if f.endswith(".py"):
                    path = os.path.join(root, f)
                    with open(path, "r", encoding="utf-8", errors="replace") as fp:
                        for line_idx, line in enumerate(fp, 1):
                            s = line.strip()
                            if s.startswith("#"):
                                violations.append(f"{path}:{line_idx}: {s}")
        self.assertEqual(violations, [])

    def test_f11_no_triple_quote_docstrings_in_test_files(self):
        triple_d = chr(34) * 3
        triple_s = chr(39) * 3
        violations = []
        for root, _, files in os.walk(self.tests_dir):
            for f in files:
                if f.endswith(".py"):
                    path = os.path.join(root, f)
                    with open(path, "r", encoding="utf-8", errors="replace") as fp:
                        content = fp.read()
                        if triple_d in content or triple_s in content:
                            violations.append(path)
        self.assertEqual(violations, [])

    def test_f11_no_c_style_comments(self):
        c_line = chr(47) * 2
        c_open = chr(47) + chr(42)
        c_close = chr(42) + chr(47)
        violations = []
        for root, _, files in os.walk(self.tests_dir):
            for f in files:
                if f.endswith((".py", ".sh", ".js")):
                    path = os.path.join(root, f)
                    if os.path.basename(path) == "test_f11_zero_comments.py":
                        continue
                    with open(path, "r", encoding="utf-8", errors="replace") as fp:
                        for line_idx, line in enumerate(fp, 1):
                            s = line.strip()
                            if s.startswith(c_line) or s.startswith(c_open) or c_close in s:
                                violations.append(f"{path}:{line_idx}: {s}")
        self.assertEqual(violations, [])

    def test_f11_no_comments_in_test_runner(self):
        runner_path = os.path.join(self.tests_dir, "run_all_tests.sh")
        if os.path.exists(runner_path):
            with open(runner_path, "r", encoding="utf-8", errors="replace") as fp:
                for line_idx, line in enumerate(fp, 1):
                    s = line.strip()
                    if s.startswith("#") or s.startswith("//"):
                        self.fail(f"Comment found in runner {runner_path}:{line_idx}: {s}")

    def test_f11_ast_tokenize_comment_audit(self):
        violations = []
        for root, _, files in os.walk(self.tests_dir):
            for f in files:
                if f.endswith(".py"):
                    path = os.path.join(root, f)
                    with open(path, "rb") as fp:
                        tokens = tokenize.tokenize(fp.readline)
                        for tok in tokens:
                            if tok.type == tokenize.COMMENT:
                                violations.append(f"{path}:{tok.start[0]}: {tok.string}")
        self.assertEqual(violations, [])

if __name__ == "__main__":
    unittest.main()
