"""Wave270: original Flind Command.migrate --plan/--check on real *synthetic* ClickHouse.

This subprocess may only access one parent-provided 127.0.0.1 HTTP port.
All ClickHouse migration SQL is PREVIEW ONLY, never applied.
"""
from __future__ import annotations
from contextlib import redirect_stdout
from io import StringIO
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch


def require(ok: bool, message: str):
    if not ok:
        raise RuntimeError("W270_FAIL_CLOSED: " + message)


def main():
    root=Path("/private/tmp/flind-wave269-native-plan")
    source=root/"source"
    require((root/".flind-wave269-owner").is_file(), "W269 source owner marker missing")
    require(source.is_dir(), "source not found")
    port=int(os.environ["FLIND_W270_HTTP_PORT"])
    db=os.environ["FLIND_W270_SYNTHETIC_DB"]
    require(1024 <= port <= 65535, "invalid port")
    require(db == "flind_wave270_synthetic", "invalid synthetic database")
    require(subprocess.check_output(
        ["git","-C",str(source),"rev-parse","HEAD:posthog/clickhouse/migrations"],text=True
    ).strip()=="23ea2f226e6be4f2caca554b6ef7cd769d61baa0", "migration tree drift")
    expected={
        "posthog/management/commands/migrate_clickhouse.py":"a3292548f7b3564ea265c232c3f9c43df933c410",
        "posthog/management/commands/test/test_migrate_clickhouse.py":"1100c2fe67cc82c72deb0c68b7afd87c7e080560",
    }
    for relative,blob in expected.items():
        require(subprocess.check_output(
            ["git","hash-object",str(source/relative)],text=True
        ).strip()==blob, "source modified: "+relative)
    signal.alarm(80)
    os.environ.clear()
    os.environ.update({
        "HOME":str(root),
        "TMPDIR":str(root),
        "PATH":"/usr/bin:/bin:/opt/homebrew/bin",
        "PYTHONDONTWRITEBYTECODE":"1",
        "DJANGO_SETTINGS_MODULE":"posthog.settings",
        "SECRET_KEY":"flind-wave270-synthetic-test",
        "DATABASE_URL":"postgresql://invalid@127.0.0.1:1/w270",
        "REDIS_URL":"redis://127.0.0.1:1/0",
        "CLICKHOUSE_HOST":"127.0.0.1",
        "CLICKHOUSE_PORT":"1",
        "CLICKHOUSE_HTTP_URL":f"http://127.0.0.1:{port}/",
        "KAFKA_HOSTS":"127.0.0.1:1",
        "SENTRY_DSN":"",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD":"1",
    })
    original_connect=socket.socket.connect
    original_connect_ex=socket.socket.connect_ex
    def strict_connect(sock,address):
        if not (isinstance(address,tuple) and len(address)>=2 and
                address[0]=="127.0.0.1" and address[1]==port):
            raise RuntimeError("W270_NON_SCRATCH_NETWORK_DENIED")
        return original_connect(sock,address)
    def strict_connect_ex(sock,address):
        if not (isinstance(address,tuple) and len(address)>=2 and
                address[0]=="127.0.0.1" and address[1]==port):
            raise RuntimeError("W270_NON_SCRATCH_NETWORK_DENIED")
        return original_connect_ex(sock,address)
    socket.socket.connect=strict_connect
    socket.socket.connect_ex=strict_connect_ex
    socket.create_connection=lambda address,timeout=None,source_address=None: (
        (_ for _ in ()).throw(RuntimeError("W270_CREATE_CONNECTION_DENIED"))
    )
    socket.socket.sendto=lambda *args,**kw: (_ for _ in ()).throw(
        RuntimeError("W270_DATAGRAM_DENIED")
    )
    os.chdir(root)
    sys.path.insert(0,str(source))
    import django
    django.setup()
    from posthog.management.commands import migrate_clickhouse as migration
    migration.CLICKHOUSE_DATABASE=db

    calls=[]
    def creds_for_migration(user):
        calls.append(user)
        return SimpleNamespace(user="default",read_password=lambda:"")
    unsafe=RuntimeError("W270_MUTATING_PRECREATE_FORBIDDEN")
    create_db=lambda *a,**kw: (_ for _ in ()).throw(unsafe)
    create_tracking=lambda *a,**kw: (_ for _ in ()).throw(unsafe)
    base={"upto":1,"plan":True,"check":False,"fake":False,"print_sql":False}
    def run(opts):
        buffer=StringIO()
        code=None
        with redirect_stdout(buffer):
            try:
                migration.Command().migrate(
                    f"http://127.0.0.1:{port}/",{**base,**opts})
            except SystemExit as e:
                code=e.code
        return code,buffer.getvalue()
    with (
        patch.object(migration,"get_clickhouse_creds",side_effect=creds_for_migration),
        patch.object(migration.Command,"_create_database_if_not_exists",side_effect=create_db),
        patch.object(migration.Command,"_create_migration_tracking_tables_if_not_exist",side_effect=create_tracking),
    ):
        zero,out0=run({"plan":True,"upto":0})
        require(zero is None and "up to date" in out0 and "Migration would get applied" not in out0,
                "real no-op plan failed")
        print("W270_REAL_INFI_READONLY_PLAN_ZERO_PASS",flush=True)
        one,out1=run({"plan":True,"upto":1,"print_sql":True})
        require(one is None and "Migration would get applied: 0001_initial" in out1
                and "CREATE DATABASE IF NOT EXISTS" in out1, "real SQL preview failed")
        print("W270_REAL_INFI_READONLY_PLAN_SQL_PASS",flush=True)
        check,out2=run({"plan":False,"check":True,"upto":1})
        require(check == 1 and "Migration would get applied: 0001_initial" in out2,
                "real read-only check expected nonzero")
        print("W270_REAL_INFI_READONLY_CHECK_PASS",flush=True)
    require(len(calls)==3, "credential fixture calls mismatch")
    print("W270_REAL_CLICKHOUSE_ORIGINAL_COMMAND_READONLY_PASS",flush=True)


if __name__=="__main__":
    main()
