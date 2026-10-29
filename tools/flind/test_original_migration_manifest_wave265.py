"""Wave265: verify original migration manifest and bounded selection without DB access."""
from __future__ import annotations
import ast
import importlib
from collections import Counter
from pathlib import Path
import pkgutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "posthog/clickhouse/migrations"
COMMAND = ROOT / "posthog/management/commands/migrate_clickhouse.py"
TREE_SHA = "23ea2f226e6be4f2caca554b6ef7cd769d61baa0"
COMMAND_SHA = "a3292548f7b3564ea265c232c3f9c43df933c410"
KNOWN_DUPLICATES = {29: 2, 50: 2, 54: 2, 55: 3, 64: 3, 72: 2, 73: 2, 83: 2}

def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()

def migration_files():
    return sorted(p for p in MIGRATIONS.glob("*.py")
                  if p.name[:4].isdigit() and p.name[4:5] == "_")

def original_selection(names, upto, applied=()):
    tree = ast.parse(COMMAND.read_text())
    command = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Command")
    method = next(n for n in command.body if isinstance(n, ast.FunctionDef) and n.name == "get_migrations")
    cls = ast.ClassDef(name="IsolatedCommand", bases=[], keywords=[], body=[method], decorator_list=[])
    code = compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])), str(COMMAND), "exec")
    modules = {name: SimpleNamespace(operations=[]) for name in names}
    scope = {"MIGRATIONS_PACKAGE_NAME": "original_names_only",
             "import_submodules": lambda package: modules}
    exec(code, scope)
    command = scope["IsolatedCommand"]()
    command.get_applied_migrations = lambda db: set(applied)
    return [name for name, _ in command.get_migrations(object(), upto)]

def assigns_ops(nodes):
    for n in nodes:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "operations" for t in n.targets):
            return True
        if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id == "operations":
            return True
    return False

class OriginalManifestTests(unittest.TestCase):
    def test_committed_sources_match_exact_checkout(self):
        self.assertEqual(git("rev-parse", "HEAD:posthog/clickhouse/migrations"), TREE_SHA)
        self.assertEqual(git("hash-object", str(COMMAND)), COMMAND_SHA)
        entries = git("ls-tree", "-r", "HEAD", "--", "posthog/clickhouse/migrations").splitlines()
        self.assertEqual(len(entries), 355)
        for row in entries:
            header, path = row.split("\t", 1)
            if path.endswith((".py", ".sql", ".txt")):
                self.assertEqual(git("hash-object", str(ROOT / path)), header.split()[2], path)

    def test_346_files_tip_duplicate_numbering(self):
        files = migration_files()
        self.assertEqual(len(files), 346)
        self.assertEqual(files[-1].stem, "0359_logs_ingest_to_apm")
        self.assertEqual((MIGRATIONS / "max_migration.txt").read_text().strip(), files[-1].stem)
        counts = Counter(int(p.name[:4]) for p in files)
        self.assertEqual({k: v for k, v in counts.items() if v > 1}, KNOWN_DUPLICATES)

    def test_all_sources_syntax_and_operations_definition(self):
        conditional = []
        for p in migration_files():
            tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
            if assigns_ops(tree.body):
                continue
            branches = [n for n in tree.body if isinstance(n, ast.If)
                        and assigns_ops(n.body) and assigns_ops(n.orelse)]
            self.assertTrue(branches, "No operations in " + p.name)
            conditional.append(p.name)
        self.assertEqual(conditional, ["0249_property_values_kafka_named_collection.py"])

    def test_unusual_historical_migration_module_name_is_importable(self):
        name = "0067_event_kafka_debug_table copy"
        self.assertIn(name, [module for _, module, _ in pkgutil.iter_modules([str(MIGRATIONS)])])
        with tempfile.TemporaryDirectory(prefix="flind_wave265_synthetic_") as tmp:
            package = Path(tmp) / "flind_wave265_fixture"
            package.mkdir()
            (package / "__init__.py").write_text("")
            (package / (name + ".py")).write_text("operations = []\n")
            sys.path.insert(0, tmp)
            try:
                result = importlib.import_module("flind_wave265_fixture." + name)
                self.assertEqual(result.operations, [])
            finally:
                sys.path.remove(tmp)
                for key in list(sys.modules):
                    if key.startswith("flind_wave265_fixture"):
                        del sys.modules[key]

    def test_actual_filenames_select_upto_inclusive(self):
        names = [p.stem for p in migration_files()]
        for upto in (0, 1, 4, 5, 29, 50, 55, 64, 83, 88, 265, 337, 359, 99999):
            with self.subTest(upto=upto):
                expected = [name for name in names if int(name[:4]) <= upto]
                self.assertEqual(original_selection(names, upto), expected)

    def test_applied_names_are_not_replanned(self):
        names = [p.stem for p in migration_files()]
        applied = set(names[:18] + names[24:39])
        expected = [n for n in names if int(n[:4]) <= 55 and n not in applied]
        self.assertEqual(original_selection(names, 55, applied), expected)

if __name__ == "__main__":
    unittest.main()
