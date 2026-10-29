"""Wave262: execute original Flind migration pytest cases with authenticated source
AST for credentials and command; isolate non-relevant PostHog app bootstrap.

This is NOT the full product Django runtime; parent modules are stubs and real
original ClickHouse credential methods are source-extracted.
"""
from __future__ import annotations

import ast
import dataclasses
import importlib.metadata
import importlib.util
import json
import logging
from pathlib import Path
import socket
import sys
from tempfile import TemporaryDirectory
from types import ModuleType
from enum import StrEnum
from typing import Mapping
from unittest.mock import MagicMock
import pytest

EXPECTED_VERSIONS = {
    "pytest": "9.1.1", "responses": "0.23.1",
    "django": "5.2.18", "infi-clickhouse-orm": "2.1.0.post20",
    "requests": "2.33.0",
}
for pkg, expected_version in EXPECTED_VERSIONS.items():
    if importlib.metadata.version(pkg) != expected_version:
        raise RuntimeError("Wave262 source-locked test runtime version mismatch: "+pkg)
direct = importlib.metadata.distribution("infi-clickhouse-orm").read_text("direct_url.json")
if not direct or json.loads(direct).get("vcs_info",{}).get("commit_id") != "4e3996becf66bf5c26580aff12a80425d9d56fe5":
    raise RuntimeError("Wave262 original pinned infi Git revision mismatch")

import os
SOURCE_ROOT = Path(os.environ.get(
    "FLIND_W262_SOURCE_ROOT", str(Path(__file__).resolve().parents[2])
)).resolve()
TEST_ROOT = SOURCE_ROOT / "posthog/management/commands/test"
if not SOURCE_ROOT.is_dir() or not TEST_ROOT.is_dir():
    raise RuntimeError("Flind source root and product test directory are required")
import subprocess
def sha(path: Path):
    return subprocess.check_output(["git","hash-object",str(path)],text=True).strip()
credential_source = SOURCE_ROOT / "posthog/clickhouse/client/connection.py"
command_source = SOURCE_ROOT / "posthog/management/commands/migrate_clickhouse.py"
product_tests = TEST_ROOT / "test_migrate_clickhouse.py"
expected = {
    credential_source: "586900ac49ea84eb1315dd7169a824b15cae1b0c",
    command_source: "7882dea334d98f7699d54b7f4ee2821eac82318e",
    product_tests: "dc5fa37ccda7c45757f48f73838099baca5b8dc0",
}
for path, digest in expected.items():
    if not path.is_file() or sha(path) != digest:
        raise RuntimeError("Wave262 source Git blob mismatch: " + str(path))

from django.conf import settings
if not settings.configured:
    settings.configure(TEST=True,E2E_TESTING=False,MULTINODE_CLICKHOUSE=False,
                       USE_I18N=False,SECRET_KEY="flind-wave262-owner-synthetic-only",
                       INSTALLED_APPS=[])

def pkg(name: str, path: Path | None = None) -> ModuleType:
    obj = ModuleType(name)
    if path is not None:
        obj.__path__ = [str(path)]
    sys.modules[name] = obj
    if "." in name:
        parent,child = name.rsplit(".",1)
        if parent in sys.modules:
            setattr(sys.modules[parent],child,obj)
    return obj

pkg("posthog",SOURCE_ROOT/"posthog")
pkg("posthog.clickhouse",SOURCE_ROOT/"posthog/clickhouse")
pkg("posthog.clickhouse.client",SOURCE_ROOT/"posthog/clickhouse/client")
conn = pkg("posthog.clickhouse.client.connection")
cfg = pkg("posthog.settings")
cfg.CLICKHOUSE_DATABASE = "flind_wave262_synthetic"
cfg.CLICKHOUSE_HTTP_URL = "http://127.0.0.1:19999/"
stores = pkg("posthog.settings.data_stores")
stores.CLICKHOUSE_MIGRATIONS_CLUSTER = "posthog_migrations"
pkg("posthog.management",SOURCE_ROOT/"posthog/management")
pkg("posthog.management.commands",SOURCE_ROOT/"posthog/management/commands")

source_tree = ast.parse(credential_source.read_text())
want = {"ClickHouseUser", "ClickHouseCredentials",
        "_registered_users","get_clickhouse_creds"}
selected = []
for node in source_tree.body:
    if getattr(node,"name",None) in want:
        if isinstance(node,ast.ClassDef) and node.name=="ClickHouseCredentials":
            node.decorator_list = [ast.Name(id="dataclass",ctx=ast.Load())]
        selected.append(node)
if {node.name for node in selected} != want:
    raise RuntimeError("Original credential AST subset is missing")
namespace = conn.__dict__
namespace.update({
    "StrEnum":StrEnum,
    "dataclass":dataclasses.dataclass,
    "field":dataclasses.field,
    "Path":Path,
    "Mapping":Mapping,
    "logging":logging,
    "_token_is_expired":lambda token:False,
    "__user_dict":None,
    "init_clickhouse_users":lambda : (_ for _ in ()).throw(RuntimeError("unconfigured real ClickHouse users forbidden")),
})
code=compile(ast.fix_missing_locations(ast.Module(body=selected,type_ignores=[])),
             str(credential_source),"exec")
exec(code,namespace)
conn.default_client = MagicMock()
import posthog.clickhouse.client as client_pkg
client_pkg.connection = conn

cmd_name = "posthog.management.commands.migrate_clickhouse"
spec=importlib.util.spec_from_file_location(cmd_name,command_source)
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot load original Flind migration management command")
command = importlib.util.module_from_spec(spec)
sys.modules[cmd_name]=command
spec.loader.exec_module(command)
import posthog.management.commands as management_pkg
management_pkg.migrate_clickhouse = command

# Allow no real network connections; responses intercept original mock HTTP.
original_connect = socket.socket.connect
def safe_connect(sock,address):
    if not isinstance(address,tuple) or address[0] not in ("127.0.0.1","::1"):
        raise RuntimeError("WAVE262_NON_LOOPBACK_NETWORK_REFUSED")
    return original_connect(sock,address)
socket.socket.connect = safe_connect

print("W262_ORIGINAL_SOURCE_AUTHENTICATED",sha(credential_source),
      sha(command_source),sha(product_tests),flush=True)
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
result=pytest.main(["-q","--noconftest","-o","addopts=",
                    "-o","python_files=test_*.py",
                    str(product_tests)])
print("W262_FIRST_PARTY_PRODUCT_CASE_EXIT",result,flush=True)
raise SystemExit(int(result))
