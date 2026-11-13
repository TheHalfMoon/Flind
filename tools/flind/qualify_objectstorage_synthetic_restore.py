#!/usr/bin/env python3
"""Ephemeral synthetic S3 logical-export/restore smoke for local SeaweedFS only.

NEVER use this script for customer or production data recovery.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile


class GuardError(RuntimeError):
    pass


def require_runner_context(env: dict[str, str], cwd: Path | None = None) -> tuple[Path, Path, str]:
    cwd = (cwd or Path.cwd()).resolve()
    if env.get("GITHUB_ACTIONS") != "true":
        raise GuardError("ephemeral GitHub Actions runner is required")
    if env.get("FLIND_SYNTHETIC_S3_RESTORE") != "1":
        raise GuardError("explicit synthetic objectstore opt-in required")
    if env.get("DEBUG") != "1" or env.get("DATABASE_URL") != "postgres://posthog:posthog@localhost:5432/posthog":
        raise GuardError("unexpected development database context")
    if env.get("FLIND_S3_ENDPOINT") != "http://127.0.0.1:19000":
        raise GuardError("unexpected S3 endpoint; only local SeaweedFS allowed")
    workspace = Path(env.get("GITHUB_WORKSPACE") or "/missing/").resolve()
    if cwd != workspace or not (workspace / "docker-compose.dev.yml").is_file():
        raise GuardError("unexpected checked-out Flind workspace")
    evidence = Path(env.get("EVIDENCE") or "/missing/").resolve()
    if evidence != workspace / "flind-evidence":
        raise GuardError("evidence path must be runner-local")
    temporary = Path(env.get("RUNNER_TEMP") or "/missing/").resolve()
    if not temporary.is_dir() or temporary == workspace or temporary == Path("/"):
        raise GuardError("invalid ephemeral runner temp")
    run_id = env.get("GITHUB_RUN_ID", "")
    attempt = env.get("GITHUB_RUN_ATTEMPT", "")
    if not run_id.isdecimal() or not attempt.isdecimal() or len(run_id) > 20 or len(attempt) > 5:
        raise GuardError("GitHub run identity is required")
    return temporary, evidence, f"flind-ci-restore-{run_id}-{attempt}"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_equal(original: bytes, restored: bytes) -> None:
    if original != restored:
        raise AssertionError("synthetic S3 object bytes do not match exported data")


def run() -> None:
    temporary, evidence, bucket = require_runner_context(dict(os.environ))
    # boto3 is a pinned existing Flind runtime dependency; load it only
    # after all environmental guards have accepted the throwaway CI runner.
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError

    client = boto3.client(
        "s3",
        endpoint_url="http://127.0.0.1:19000",
        aws_access_key_id="object_storage_root_user",
        aws_secret_access_key="object_storage_root_password",
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                      connect_timeout=5, read_timeout=15, retries={"max_attempts": 1}),
    )
    names = [item["Name"] for item in client.list_buckets().get("Buckets", [])]
    if bucket in names:
        raise GuardError("synthetic recovery bucket already exists; refusing to modify it")

    scratch = Path(tempfile.mkdtemp(prefix="flind-objectstorage-", dir=temporary))
    created = False
    objects = {
        "tenant-101.bin": b"flind-synthetic-first\x00tenant" + bytes(range(0, 32)),
        "tenant-202.bin": b"flind-synthetic-second\xfftenant" + bytes(range(31, -1, -1)),
    }
    primary_errors: list[BaseException] = []
    try:
        client.create_bucket(Bucket=bucket)
        created = True
        for name, payload in objects.items():
            client.put_object(Bucket=bucket, Key=name, Body=payload, ContentType="application/octet-stream")
            live = client.get_object(Bucket=bucket, Key=name)["Body"].read()
            verify_equal(payload, live)
            (scratch / name).write_bytes(live)

        # The only deleted objects are in the synthetic bucket created by this
        # exact run. Exported runner-local files survive deletion.
        for name in objects:
            client.delete_object(Bucket=bucket, Key=name)
            try:
                client.head_object(Bucket=bucket, Key=name)
            except ClientError as exc:
                if str(exc.response.get("Error", {}).get("Code")) not in ("404", "NoSuchKey", "NotFound"):
                    raise
            else:
                raise AssertionError("synthetic object deletion negative control did not take effect")

        for name, original in objects.items():
            exported = (scratch / name).read_bytes()
            client.put_object(Bucket=bucket, Key=name, Body=exported, ContentType="application/octet-stream")
            verify_equal(original, client.get_object(Bucket=bucket, Key=name)["Body"].read())

        # Prove the SAME byte comparator rejects genuine S3 corruption.
        client.put_object(Bucket=bucket, Key="tenant-202.bin", Body=b"deliberate synthetic tampering")
        corrupted = client.get_object(Bucket=bucket, Key="tenant-202.bin")["Body"].read()
        if corrupted == objects["tenant-202.bin"]:
            raise AssertionError("S3 tamper negative control did not change object")
        try:
            verify_equal(objects["tenant-202.bin"], corrupted)
        except AssertionError:
            pass
        else:
            raise AssertionError("synthetic object comparator failed to detect tampering")

        restored = (scratch / "tenant-202.bin").read_bytes()
        client.put_object(Bucket=bucket, Key="tenant-202.bin", Body=restored)
        verify_equal(objects["tenant-202.bin"], client.get_object(Bucket=bucket, Key="tenant-202.bin")["Body"].read())

        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "objectstorage-restore-smoke.txt").write_text(
            "synthetic_objectstore_export_delete_restore=pass\n"
            "synthetic_tenants=2\n"
            "deleted_object_negative_control=pass\n"
            "tampered_object_negative_control=pass\n"
            "recovery_after_tamper=pass\n"
            f"archive_object_101_sha256={sha(objects['tenant-101.bin'])}\n"
            f"archive_object_202_sha256={sha(objects['tenant-202.bin'])}\n"
            "production_objectstorage_backup_qualified=false\n"
            "cross_service_restore_qualified=false\n",
            encoding="utf-8",
        )
        print((evidence / "objectstorage-restore-smoke.txt").read_text())
    except BaseException as exc:
        primary_errors.append(exc)
        raise
    finally:
        cleanup_errors: list[str] = []
        if created:
            try:
                for name in objects:
                    client.delete_object(Bucket=bucket, Key=name)
                client.delete_bucket(Bucket=bucket)
            except Exception as exc:
                cleanup_errors.append(type(exc).__name__)
        try:
            shutil.rmtree(scratch)
        except Exception as exc:
            cleanup_errors.append(type(exc).__name__)
        if cleanup_errors:
            if primary_errors:
                print("Flind S3 recovery: cleanup also failed: " + ",".join(cleanup_errors), file=sys.stderr)
            else:
                raise RuntimeError("Flind S3 recovery: synthetic bucket cleanup failed: " + ",".join(cleanup_errors))


if __name__ == "__main__":
    try:
        run()
    except (GuardError, AssertionError, RuntimeError) as exc:
        print(f"Flind S3 recovery: {exc}", file=sys.stderr)
        sys.exit(2)
