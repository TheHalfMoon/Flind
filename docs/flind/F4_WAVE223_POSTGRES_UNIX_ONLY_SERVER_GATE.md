# Wave 223 — explicit PostgreSQL Unix-only server admission

## Why this guard matters

The original first-party isolated PostgreSQL migration qualifier (Wave173, used for real Wave222 apply/rollback) already required a marked disposable source and cluster, a Unix-socket connection, and an exact server data directory. **Connecting over a Unix socket does not prove the server itself has no TCP listeners.** The tool previously did not query the server's `listen_addresses` setting.

## Change

The qualifier now issues `SHOW listen_addresses` on the **same verified PostgreSQL session**, and rejects a nonempty response before planning or applying migrations. An empty setting is the explicit PostgreSQL configuration used by the Wave222 private cluster (`listen_addresses=''`). It adds `postgres_tcp_disabled_qualified` to the receipt, initially false; the flag becomes true only after all of the database, socket, read-only-session, data-directory and TCP-listener checks have passed.

The helper `server_has_no_tcp_listeners()` requires an exactly empty string. Even addresses limited to `localhost`, `127.0.0.1` or `::1` are rejected (as are `*`, `0.0.0.0`, combinations, whitespace and absent values). The intent is to prove *zero TCP listeners*, not merely no remotely exposed listeners. The existing allowed migration remains strictly `ai_training.0001_initial`, with one reversible `CreateModel` operation.

## Verification and limits

- Exact source patch was constructed from private main at `a5585565391734d7948f7e3a6b816e35eca7db09`, using unique text anchors and preserving existing source.
- Added first-party regression tests under `tools/flind/test_qualify_isolated_postgres_wave173.py` for every nonempty listener value and for failure receipts retaining `postgres_tcp_disabled_qualified=false`.
- The pure helper logic was separately exercised in a local isolated Python harness: two test methods passed (Unix-only allow and eight denied configurations). **This is not a full repository test run**. The device interface is at its monthly usage limit, so the existing full Wave173 suite and new live-postgres test **could not be rerun in this wave**; re-run on an authorized healthy environment before making a renewed Wave223 live-server claim.
- Wave222's previously executed real PostgreSQL 17.9 isolated script used `listen_addresses=''` and applied/rolled back one original migration successfully. That is **historic evidence** for Wave222, not newly reexecuted evidence for this Wave223 source change.

## Late-failure global socket restoration (2026-10-28)

An independent exact-source review identified a second, distinct safety issue
in the original Wave173 implementation: it replaces the process-global
`socket.socket.connect`, `socket.socket.connect_ex` and
`socket.create_connection` functions with a deny-TCP policy but did not
restore them if the source reader, Django registry or migration raised an
exception. This can poison a caller's subsequent network operations.

The Wave223 branch now snapshots all three originals before installing the
policy and restores them in the `execute()` `finally` block on every exit.
The network lockdown remains in force throughout the original PostgreSQL
qualifier. Added an isolated failure-injection regression test that forces
the original source reader's context entry to fail **after** installing the
socket policy, and asserts all three functions are restored and no
PostgreSQL/TCP or migration success is claimed.

**Execution boundary:** the new test and full original first-party
`unittest` suite have **not** been run against a complete private Flind
checkout in this wave; this source-backed fix is deliberately left in
Draft PR #258 pending independent executable qualification and a real
marked Unix-only PostgreSQL17.9 rerun. No live PostgreSQL/ClickHouse
connection was attempted.

## Wave 223 further hardening — server Unix-socket ownership and path disjointness

The additional original-source audit found that disabling PostgreSQL TCP listeners and connecting over an approved Unix socket did **not** prove that PostgreSQL was *only* bound to the approved socket directory. Likewise, the prior filesystem admission rejected source/data overlap but did not explicitly reject source/socket or data/socket overlap.

Before constructing Django's `MigrationExecutor`, the qualifier now issues
`SHOW unix_socket_directories` in the **same verified PostgreSQL session** and
requires that setting to equal the approved private `socket_dir` **exactly**.
It rejects empty, relative, alternative, comma-separated, duplicated and alias
settings. An additional receipt field
`postgres_socket_directory_qualified` starts **false** and becomes true only
after the complete PostgreSQL isolation admission succeeds. The path check
also requires the marked source, cluster data and socket directories to be
pairwise disjoint, including all ancestor/descendant relationships.

The original first-party safety test module now includes **11 test methods**,
including exact server-socket configuration, positive marked private scratch
paths, source/socket and data/socket overlap, and failure receipts.
**These 11 first-party methods have not been run from the full Flind checkout**.

Independently executed in this session: **10/10 container-only pure-guard
smoke tests PASS with Python 3.13.5** and **10/10 PASS with `python -O`**.
The tests exercised owner-marked disposable directories under a synthetic
container-local `/private/tmp`, overlap, symlink, missing-marker, listener
and Unix-socket configuration negative cases. Their scope is an independently
reconstructed Python helper excerpt, not execution of the whole first-party
module, and there was **no PostgreSQL server or database connection**.
The existing earlier Wave222 PostgreSQL17.9 runtime had explicitly used
`listen_addresses=''` and a single private socket directory, but a **new
first-party live Wave223 execution still remains a strict merge gate**.

## Late-Django-error process state containment

A further first-party source review found that the qualifier restored patched
`socket.socket.connect`, `socket.socket.connect_ex` and
`socket.create_connection` on an exception, but did **not** restore its
`sys.path` inserts, the temporary `GitTrackedPythonFinder` appended to
`sys.meta_path`, or synthetic Django/PostgreSQL/Kafka/Redis/ClickHouse
environment overrides. These mutations could leak into another test or
library caller reusing the same Python process.

The qualifier now remembers the original import paths, temporarily overridden
environment variables (including unset-vs-set distinctions), and finder
object, and restores all of them in the **same `execute()` finally block**
that restores the socket API. Only the finder added by this call is removed
from `sys.meta_path`. The real PostgreSQL safety policy remains installed
for the entire time Django's migration executor runs.

Added a first-party failure-injection test that substitutes a synthetic
`django.setup()` raising `RuntimeError` **after** the finder has been
installed. The test asserts import paths, finder removal and synthetic
environment variables are restored, and that no PG migration or release
success flag is claimed. **This new test has not been run in a full original
Flind checkout**; the first-party test module now contains 12 methods.

Executed evidence this session: the existing ten pure-guard tests against the
previously verified exact source excerpt passed **10/10 normal and 10/10 with
`python -O`** in the isolated Python 3.13.5 sandbox. The new process-global
cleanup code was inspected against the *current* authenticated private PR
source and passed **16/16 structural checks**. These checks are not the new
first-party module's execution, and no database/Django runtime was started.

## Fail-closed Django connection finalization

A further original-source audit found the Django database connection was
closed only on successful completion, leaving it open when PostgreSQL
configuration admission, migrations or rollback raised an exception.
The qualifier now tracks the actual Django connection from its creation and
closes it in `finally`, **before restoring the deny-TCP socket policy**.
A secondary close exception is recorded as a blocker only when there is no
previous primary blocker. It never replaces the original refusal. An isolated
source-level first-party test was added to inject a rejected Django database
configuration and assert that `connection.close()` occurs while the Unix-only
socket policy is still installed. The original first-party module now contains
**13** test methods, and this newest test has **not** run from the complete
private Flind checkout.

Independent executable evidence against the copied *exact first-party*
`except/finally` source excerpt: Python 3.13.5 **5/5 PASS** ordinary and
**5/5 PASS under `python -O`**, plus `py_compile` PASS. Cases cover no
connection on primary error, successful close while the socket policy remains,
close error preserving the original refusal, close error without an earlier
blocker, successful close with no blocker, and restoration of synthetic
environment/import paths/socket API. The excerpt harness initially failed
because its fake `os` object lacked `environ`; correcting that test harness
produced the above pass results. **These are not full original module tests
or live PostgreSQL execution.**

## Regression test assertion swallowing correction

The mocked PostgreSQL `connection.close()` callback used to assert that the
Unix-socket-only process policy was still installed. That assertion was
vulnerable to a false positive because `execute()` intentionally catches
secondary exceptions raised by `connection.close()` while preserving the
original database-configuration refusal. The test now captures the socket
policy observation inside `close()` **without raising**, then checks the
observation **after** `execute()` returns. This ensures an incorrect
close-after-policy-removal implementation cannot silently pass the regression.

The separate isolated Python 3.13.5 excerpt harness was corrected the same
way. Executed the unchanged 10 pure guard excerpts plus 5
original-`except/finally` excerpts as one local suite:
**15/15 PASS in Python**, **15/15 PASS with `python -O`**, compilation
PASS. The harness uses synthetic filesystem, in-memory fake environment
and fake connection; **no original full 13-method test module, PostgreSQL
server, migrations or real network service was executed**.

## Caller SIGALRM preservation

The existing qualifier installed a process-wide `signal.alarm(150)`, then
unconditionally called `signal.alarm(0)` in `finally`. Consequently, even
a failed scratch-path admission (before installing Flind's own timer)
could cancel the calling application's existing timer. A successful
installation also silently overwrote any previously active alarm.

Wave223 now remembers the return value of the first
`signal.alarm(150)`, which is the caller's previous remaining seconds.
If it is nonzero, the original qualifier **fails closed before importing
Django, invoking Git, or modifying synthetic service environment**.
In `finally`, the qualifier restores that earlier alarm value. If the
scratch-path admission fails before any alarm call, it does **not touch**
the caller's alarm at all. When there was no original timer, the
qualifier disarms only its own timer in `finally`.

The first-party unit suite now has **15 methods** (up from 13), including
a preexisting alarm refusal with exact mocked calls `[150, 47]` and
a bad scratch-path refusal that must not call `signal.alarm`. Existing
fake alarm mocks on the late-Django error path now explicitly return zero,
representing a process with no preexisting timer.

**Executed scope:** the exact first-party alarm admission and restoration
source statements were copied into a small synthetic Python test harness
and executed as five source-excerpt cases: **5/5 PASS** with Python 3.13.5,
**5/5 PASS** under `python -O`, and `py_compile` PASS. The five cases
cover early scratch-path refusal, a caller alarm and fail-closed refusal,
success with Flind-only timer, late failure with Flind-only timer, and
an exception thrown by the alarm API. This is NOT execution of the full
15-method original first-party module, a complete source checkout, or a
real PostgreSQL service.

## Combined isolated guard suite and original full-test blocker

After the SIGALRM fix, all three **isolated excerpt-level test modules**
were executed together in Python 3.13.5: 10 source-derived path/socket/listener
tests, 5 verbatim first-party `except/finally` cleanup tests, and 5
SIGALRM admission/restoration source-excerpt tests. **20/20 PASS** in ordinary
Python, **20/20 PASS** under `python -O`, and all three test modules compiled.
The preexisting original late source-reader failure first-party test now
also asserts the actual mocked alarm call sequence `[150, 0]`.

This is exactly **40 successful executions of isolated source-excerpt
tests**, not 40 first-party tests from the original Flind checkout. The PR
contains **15 original first-party unittest methods** but those methods have
not been run from a complete private Flind checkout in this environment.
There is no authenticated host-local PostgreSQL17.9 service available for
re-applying and rolling back the one approved migration with these stricter
server, socket, environment, timer and cleanup guards. Consequently this
PR must stay **Draft/unmerged**; its `release_qualified` flag remains
false and complete PG/CH migrations and Kafka/Rust/Node/ClickHouse tests
remain outstanding.

## Nonempty migration-plan qualification

The earlier source set `migration_plan_qualified` equal to
`migration_graph_qualified`. This could report a qualified plan when
Django's migration graph exists but `MigrationExecutor.migration_plan()`
returns **zero pending migrations** (for example, a database whose
migrations are already recorded). The receipt now requires all three:
a qualified graph, at least one leaf target, and a nonempty plan. The
new first-party unit method checks five true/false combinations, bringing
the first-party module to **16 test methods**.

**Executed in this run:** a separate container-local Python3.13.5
source-excerpt test for this exact helper passed **5/5 normal** and
**5/5 under `python -O`**. The existing synthetic excerpt suites
(10 safety guard, 5 cleanup, 5 alarm) were rerun alongside it, yielding
**25/25 normal** and **25/25 optimized**. The full original 16-method
first-party module and real owned PostgreSQL 17.9 service have NOT been
executed, so PR #258 remains Draft and must not be merged yet.

## PostgreSQL 17.9+ (major 17) source and connected-server version gate

Before this change, the scratch ownership check accepted any existing
`PG_VERSION` file, and Django's connected PostgreSQL session was not
checked for the exact PostgreSQL major version. A PostgreSQL 16 or 18
cluster with matching scratch markers and socket names could therefore
be treated as the intended original PostgreSQL 17.9 qualification host.

The pre-connection filesystem check now requires the owned PG data
directory's `PG_VERSION` contents to be `17`. After the socket-only,
TCP-disabled, read-only session is established, the same verified cursor
queries `SHOW server_version_num` and admits only integer versions
`170009 <= server_version_num < 180000`. This qualifies PostgreSQL
17.9 and later patch releases of the **17 major line**, but not 17.8,
16.x or 18.x. It is a version gate, not a claim of 17.9's live use.
The report's `postgres_version_qualified` is false by default and
becomes true only after the complete server check. The CLI requires
this flag even for read-only migration-plan qualification.

Two first-party regression assertions were added: a new unit test for
accepted/rejected numerical versions, and a negative scratch
`PG_VERSION=18` case. The existing CLI test fixtures now require the
new field as well; the source/test module contains **21** original
first-party unit-test methods. The complete original 21-method module
and live isolated PostgreSQL server have not been executed here.

In this isolated model container, the copied exact small server-version
predicate and 12 boundary cases were independently executed:
**12/12 PASS in Python 3.13.5** and **12/12 PASS under `python -O`**;
`py_compile` PASS. Separately, **12/12 source-structure assertions**
passed on the authenticated original PR implementation/test module,
including first-party CLI required fields, query-before-MigrationExecutor
ordering, negative PG_VERSION test and fail-closed receipt. This
qualifies only these source-level properties and not actual original
migration execution, database connectivity or release readiness.

## Canonical Django database connection settings — blocker fixed

An audit of the genuine first-party Flind source
`posthog/settings/data_stores.py` (merged main Git blob
`2185b49cbfea11ff51d847adce79b35500ad3c2d`) confirmed its
`dj_database_url.config(default=DATABASE_URL, conn_max_age=0)`
builds a database configuration with top-level `HOST` and `PORT`
fields, as does the original `postgres_config()` helper. The previous
Wave223 qualifier incorrectly checked
`connection.settings_dict["OPTIONS"]["host"]` and
`connection.settings_dict["OPTIONS"]["port"]` as if those options
must exist. Valid isolated connections could therefore be rejected as
`unexpected_django_postgres_config`, even with matching Unix socket,
correct PostgreSQL server settings, and synthetic database identity.

The new `django_config_matches_private_postgres()` helper requires
the canonical top-level `NAME`, `HOST` and `PORT` to match the
approved synthetic database, exact owned Unix-socket directory and
private service port. It also rejects explicit conflicting `host`
or `port` entries inside `OPTIONS` (because connection options may
override the top-level settings). Missing `OPTIONS` and unrelated
safe `OPTIONS` fields are admitted; malformed types fail closed.
The existing real session-level database, Unix-only socket, zero-TCP,
server-directory and PostgreSQL-version checks are preserved.

Two first-party regression methods were added to the original
`tools/flind/test_qualify_isolated_postgres_wave173.py` module,
which now has **23 methods**, including positive canonical Django
settings and twelve negative/foreign overrides. They are **not**
counted as having passed in the full original private checkout.

**Executed test evidence:** in the model's separate local Python 3.13.5
container, the new pure predicate was copied from the exact authenticated
private GitHub source and tested with 18 explicit cases:
**18/18 PASS** in ordinary Python and **18/18 PASS under real
`python -O`**; Python compilation PASS. Both successful canonical
top-level settings and hostile/malformed overrides were covered.
This is **36 isolated predicate executions**, not complete original
23-method first-party test execution or a live PostgreSQL run.
The PR remains **Draft/unmerged** until real owned isolated PG17.9+
(matching major17) apply+rollback and actual first-party suites pass.

## Missing-module diagnostics for failed live Django qualification

On an actual, fully owner-isolated Mac PostgreSQL 17.9 cluster, the first
attempt to run the **real original** CLI with `--apply-rollback` refused
before Django registry initialization and produced `blocker:
ModuleNotFoundError`. The first-party qualifier intentionally suppresses
arbitrary exception messages to avoid leaking credentials or paths, but
the absence of the missing Python module **name** prevented identifying
the precise package required by the restored lightweight Django environment.

The first-party `execute()` exception handler now adds
`missing_python_module` to a blocked receipt **only** when the exception
is `ModuleNotFoundError` and its `name` is a bounded Python module
identifier matching `[A-Za-z_][A-Za-z0-9_.]{0,127}`. Arbitrary exception
messages and tracebacks are **never** copied into the receipt, and path-like,
oversized or newline-bearing names are not reported. Existing fail-closed
`blocker` and migration/release flags remain unchanged. This is a
diagnostic, not permission to run migrations without proof.

An additional original first-party test injects a synthetic missing
module before any Git, Django or DB operation and covers five name
cases: a valid dotted module, a path/token-like invalid name, an
oversized name, a newline, and a missing name. It also checks that
arbitrary exception text is never included. The branch now contains
**26 original first-party unittest methods**.

**Actually executed** this new original first-party test against exact
GitHub file blobs copied to a temporary scratch folder on the user's
Windows machine, with `git hash-object` equality verified for both
the original qualifier and its unittest source. Python **3.14.7 normal:
1/1 PASS**; Python **3.14.7 with `-O`: 1/1 PASS**. The 25 prior
original first-party test methods passed **25/25 normal and 25/25
optimized** on the complete Mac Flind checkout at older immutable commit
`81871191e2509c895b3ebaa84080cf1eaa188705`. The newly updated
**full 26-method module has not yet been rerun in full on Mac**.

The Mac's Desktop Commander agent is temporarily offline even though
the machine responds on the local network. The new, strictly private
test cluster `/private/tmp/flind-wave223-live-pg-20261029-001` may
still be running; only its own exact marker-owned instance may be
stopped with `pg_ctl -D .../data -m fast -w stop` after Mac access
returns. No shared PostgreSQL, PgBouncer, other project or customer
database may be used. The original live apply/rollback has **not**
passed and remains the hard PR-merge and project-release gate.

## Release boundary

No full PostgreSQL or ClickHouse original migrations have been applied and no joined Kafka → Rust → Node → ClickHouse production E2E has passed. Windows disk and WSL I/O remain blocked. Flind repository remains PRIVATE, Actions disabled, no publication/deployment/paid services. The release gate remains **NO-GO**.

## Wave223 — fail-closed CLI receipt and empty-plan refusal (2026-10-28)

Exact current first-party source review exposed a second-order false PASS: the
new nonempty-plan helper could correctly set `migration_plan_qualified=false`,
yet `execute()` would return without a blocker and the original CLI would
print `PASS` and exit **0** because it checked only `blocker` (and the
optional rollback flag). The same CLI could treat other missing qualification
fields as success if an incomplete report was returned.

The branch now raises `ValueError("no_pending_original_migration_plan")`
immediately when the actual Django leaf-target plan is empty, before any
apply/rollback operation. As an independent fail-closed boundary, the CLI
requires **six exact boolean `True` receipts** (Django registry, graph,
read-only PostgreSQL connection, no TCP listeners, approved Unix-socket
directory, and nonempty pending plan), no blocker, plus exact boolean
`True` rollback receipt when `--apply-rollback` is requested. Its
human-readable PASS/BLOCKED output and exit status now use the **same**
predicate; a missing, false, or string-valued proof cannot pass.

Two new **original first-party unittest methods** were committed to the
branch for the missing-proof matrix and the apply/rollback CLI decision,
bringing the original module to **18 test methods**. These two new methods
and the complete original module have **NOT** been run in a full private
Flind checkout.

**Executed separately in a model-container-only Python 3.13.5 harness:**
four tests of the copied exact new CLI function excerpt, covering all six
missing/false/nonboolean proof fields (including JSON output), explicit
blocker, successful complete non-apply receipt, and rollback-required
false/missing/string/true outcomes. **4/4 PASS ordinary Python, 4/4 PASS
with `python -O`, `py_compile` PASS.** These are **eight excerpt-test
executions**, not original first-party module execution, a real Django
migration graph, or a live PostgreSQL migration. Seven source assertions
against the authenticated GitHub branch files passed; original source Git
blob `db3a0d68cdbafcb3610844208feaac8087e42a17`, test Git blob
`ae5310d3e000e37c3d18dcfb02db614bef5b43e2`.

**Do not merge #258 yet.** The original 18-method test module and owner-marked
private Unix-only PG17.9 single-migration apply+rollback remain unexecuted
on the current source. Full PG/CH schemas and native joined Kafka/Rust/Node/
ClickHouse E2E are still unqualified; Flind remains PRIVATE, Actions off,
NO-GO for release, and no shared services or paid tooling were used.

## Wave223 — immutable Git source-ref binding (2026-10-28)

A further exact-source review found a time-of-check/time-of-use risk:
the original qualifier resolved the requested Git ref to a 40-character
commit SHA, but then used the **symbolic** `git_ref` for
`index_tracked_python`, `GitBlobBatchReader` and
`GitTrackedPythonFinder`. A branch moved between `rev-parse`,
`ls-tree` and `cat-file` could mix migration paths or imports from
different commits while the receipt reported the first commit.

The Draft branch now passes the verified **immutable `sha`** to all
three first-party Git readers, and retains the resolved value in
`source_commit`. A new original unittest
`test_all_git_source_readers_use_resolved_commit_not_moving_ref`
uses a synthetic moving branch, mocks the first-party reader boundaries,
and requires each to receive the same resolved commit. The original
first-party test file now contains **19 unittest methods**.

**Verified scope:** authenticated GitHub source and test blobs were
re-fetched after the commits; all three exact immutable-ref call sites
and the new regression method are present. This is a **source review and
structural check only**. The 19-method original test module has **not**
been executed on a full private Flind checkout. No live owned PostgreSQL
server or migration was run for this change. Existing Wave222 evidence
used older source and cannot qualify this stricter Wave223 branch.

The PR remains **Draft, unmerged, NO-GO** until the original module,
marked private Unix-only PostgreSQL 17.9 apply+rollback and downstream
original PG/CH and Kafka/Rust/Node/ClickHouse tests are genuinely run.
No other project data, shared database, paid tooling, Actions, deployment
or publication was touched.

## Wave223 — executable Git index assignment (2026-10-28)

**Original source defect identified and corrected on Draft #258.** The
immutable-source-ref fix accidentally wrote two literal `\\n` escape
sequences into a Python **comment**, instead of real line separators.
That comment swallowed the executable
`tracked = index_tracked_python(root, sha)` assignment. On the next
`graph_source_ready(root, tracked)` access the qualifier would raise
`NameError`, so no source graph or live migration could qualify. This is
not merely cosmetic: the previously documented three Git-reader SHA
call sites included one assignment that was not executable.

The exact source line was split into three real Python lines, preserving
the immutable resolved commit argument. An original first-party
`test_resolved_git_index_is_executable_ast_not_commented_out` now checks
the **Python AST** for an actual assignment to `tracked` from
`index_tracked_python(root, sha)`, not a misleading source substring.
The original test module now contains **20 unittest methods**, still
**NOT executed in full** on a complete private Flind checkout.

**Narrow independent reproduction only:** three model-container
Python 3.13.5 tests verify the literal-comment version has no executable
AST assignment and raises `NameError`, whereas the corrected excerpt
has the executable assignment. **3/3 PASS normal Python and 3/3 PASS
with `python -O`; py_compile PASS.** These are six **excerpt-fixture**
executions, not the original first-party module or a live PostgreSQL
test. The original branch files were changed using GitHub content-SHA
checks; the full original suite, owner-marked Unix-only PostgreSQL 17.9
apply/rollback and native E2E remain outstanding.

**Do not merge #258** or claim PG/full-migration/release qualification
based on this fix alone. Flind stays PRIVATE, Actions disabled, no
publish/deploy/release, no paid services or shared/other-project DB
access, release **NO-GO**.

## Wave223 — apply AND rollback receipt required (2026-10-28)

An exact-source review found a fail-open CLI receipt predicate: when
`--apply-rollback` was requested, `main()` required the rollback proof
but did **not** require `one_first_party_apply_qualified is True`. A
synthetic report with all six Django/PG/plan gates true, apply=false and
rollback=true incorrectly returned exit 0 / PASS. This was reproduced in
an isolated Python 3.13.5 predicate harness before changing the source.

The Draft PR now requires **both** exact-boolean apply and rollback
receipts when `--apply-rollback` is requested. The existing original
first-party CLI regression was expanded to reject rollback-only proof
before accepting both proofs. The original test module still contains
**20 unittest methods, not executed as a complete first-party module**.

**Actually executed:** six narrowly reconstructed predicate tests in a
model-container Python 3.13.5 harness, **6/6 normal and 6/6 under real
`python -O`**, `py_compile` PASS. These are 12 synthetic predicate
executions, **not** a complete original first-party test run, a native
Django/PostgreSQL service, or any real migration apply/rollback.

**Hard gate unchanged:** do not merge #258 until the full original test
module and current-source owner-marked Unix-only PostgreSQL17.9 genuine
apply+rollback pass. Full original PG/CH migrations and joined native
Kafka→Rust→Node→durable ClickHouse E2E remain unqualified; release NO-GO.
Flind remains PRIVATE, Actions disabled, no publishing, deployment,
paid services, shared DB access, or other-project mutation.

Additional executable check: copied the **exact current first-party `main()` CLI
function body** into an isolated Python 3.13.5 test harness, mocking only
`execute()` so no database could be contacted. Eight focused cases cover
rollback-only, apply-only, both proofs, absent apply proof, plan-only,
non-boolean apply proof, blocker and one missing PG gate. **8/8 PASS
ordinary and 8/8 PASS `python -O`, py_compile PASS.** The initial
harness used an invalid dotted mock target due to its hyphenated local
folder; after correcting the harness mock to patch the function globals,
both suites passed. These 16 additional executions are **exact CLI
excerpt tests**, still not the complete original 20-method module or
any native PostgreSQL migration.

## Pinned original smoke migration source — apply/rollback write gate

A source integrity gap remained after freezing all Git readers to one
resolved commit: Django's standard import path can prefer physically staged
migration Python over the fallback `GitTrackedPythonFinder`. A modified
on-disk `CreateModel` could therefore satisfy the structural selector
while no longer matching the Git object for the approved original migration.

Before **any** `SET default_transaction_read_only = off` or migration
application, `--apply-rollback` now requires the **exact original**
`products/ai_training/backend/migrations/0001_initial.py` file to match
both its immutable commit's `GitBlobBatchReader` bytes and the independently
approved original Git blob SHA-1
`e74ad4a9036c4118bddb3aff89f9a923b4b964ba`.
Git's actual blob object framing (`blob <byte-count>\\0<contents>`)
is used for the SHA-1 check. Symlinked file/ancestor, missing source,
unavailable Git blob, edited Git blob and edited staged file fail closed.
The new `smoke_migration_source_qualified` receipt defaults to false and
must be exactly true for `--apply-rollback` CLI PASS, in addition to
actual apply **and** rollback receipts. Read-only plan mode does not
pretend this scoped write-source pin qualifies all migrations.

**First-party code status:** two new original test methods were added to
`tools/flind/test_qualify_isolated_postgres_wave173.py`; current branch
contains **25 methods**. These 25 methods have **not** been run as a
complete original module in a private Flind checkout.

**Executed in the model's isolated Python 3.13.5 container:** eight
standalone tests of the copied exact short first-party pin predicate
and the independently authenticated **original migration's complete
1,801-byte source**. Its locally calculated Git blob identity matched
the GitHub-authenticated blob above. The eight tests cover exact source
admission, Git-source drift, staged-source drift, file symlink, symlink
ancestor, missing file and unavailable Git blob: **8/8 PASS** under
ordinary Python and **8/8 PASS** under real `python -O`;
`py_compile` PASS. These are **16 isolated predicate executions**,
**not** execution of the original 25-method module, native Django,
PostgreSQL 17.9 or a live migration.

**Remaining hard gates:** full original first-party test module on a
complete private checkout, and genuinely owner-marked Unix-only PostgreSQL
17.9+ major17 real single original migration apply+rollback on the
exact current source with no residual tables/records. Keep PR #258
Draft/unmerged, release NO-GO. Do not touch shared Mac PG/PgBouncer,
Zyara or any other project's/customer DB, publish or deploy.

