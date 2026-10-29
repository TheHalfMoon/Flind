"""Bounded owner-only REAL ClickHouse25.12 Keeper+one-node migrations metadata prerequisite."""
from __future__ import annotations
import hashlib,json,os,pathlib,shutil,signal,socket,subprocess,time
from http.client import HTTPConnection
from xml.sax.saxutils import escape
ROOT=pathlib.Path('/private/tmp')
CHECKOUT=ROOT/'flind-wave249-deps-source'
ORIGINAL=CHECKOUT/'posthog/management/commands/migrate_clickhouse.py'
ASSET=ROOT/'flind-wave188-ch2512-durable/clickhouse-original-compressed-aarch64'
SCRATCH=ROOT/'flind-wave260-infi-migration'
MARKER='FLIND_WAVE260_OWNER_ONLY_REAL_INFI_MIGRATION_V1\n'
EXPECTED_SHA='e5be46727e773893b5786aaa3d28f5661a30179fe65e19096d8eb7d41a554fd6'
DB='flind_wave260_synthetic'
CLUSTER='posthog_migrations'
FLOOR=int(15.5*1024**3)
REPORT={'phase':'wave260_real_private_one_node_keeper_and_infi_synthetic_migration',
 'source_git_sha':'6e5da8f24fb04312ea1dd7778811ca1b21339fd9',
 'first_party_tracking_ddl_executed':False,'real_keeper_version_supported':False,
 'one_node_cluster_qualified':False,'replicated_tracking_table_qualified':False,
 'distributed_tracking_table_qualified':False,'infi_migration_runner_executed':False,'real_infi_synthetic_migration_applied':False,
 'real_infi_migration_repeat_noop':False,
 'full_original_migrations_executed':False,'multinode_replication_qualified':False,
 'release_qualified':False}
children=[]
def free_space():
 return shutil.disk_usage(ROOT).free
def port():
 with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
  s.bind(('127.0.0.1',0));return s.getsockname()[1]
def write(path,data):path.write_text(data);path.chmod(0o600)
def xml_path(path):return escape(str(path))
def http_sql(port_num,statement):
 if type(port_num) is not int or port_num<1024 or port_num>65535 or not statement.isascii() or len(statement)>2000:raise ValueError('unsafe_or_nonloopback_query')
 conn=HTTPConnection('127.0.0.1',port_num,timeout=11)
 try:
  conn.request('POST','/?wait_end_of_query=1',statement.encode('ascii'),
       headers={'Content-Type':'text/plain'})
  rsp=conn.getresponse()
  body=rsp.read(5000).decode('utf-8','replace')
  if rsp.status!=200:raise RuntimeError('clickhouse_ddl_http_'+str(rsp.status)+'_'+body[:350].replace('\n',' '))
  return body.strip()
 finally:conn.close()
def start(cmd,name,env):
 log=(SCRATCH/(name+'.log')).open('wb')
 try:
  proc=subprocess.Popen(cmd,cwd=SCRATCH,stdin=subprocess.DEVNULL,stdout=log,
       stderr=subprocess.STDOUT,start_new_session=True,env=env)
 finally:log.close()
 children.append((name,proc))
 return proc
def stop_all():
 for name,p in children:
  if p.poll() is None:
   try:os.killpg(p.pid,signal.SIGTERM)
   except ProcessLookupError:pass
 for name,p in children:
  try:p.wait(timeout=7)
  except subprocess.TimeoutExpired:
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   p.wait(timeout=7)
def keeper_ready(port_num):
 try:
  with socket.create_connection(('127.0.0.1',port_num),timeout=1) as s:
   s.settimeout(1);s.sendall(b'ruok');reply=s.recv(128)
   return b'imok' in reply
 except (OSError,TimeoutError):return False

def run():
 if SCRATCH.parent!=ROOT or SCRATCH.exists() or SCRATCH.is_symlink():raise RuntimeError('unapproved_owner_scratch_path')
 if not CHECKOUT.is_dir() or not ORIGINAL.is_file():raise RuntimeError('missing_authenticated_source')
 if subprocess.check_output(['git','-C',str(CHECKOUT),'rev-parse','HEAD'],text=True).strip()!=REPORT['source_git_sha']:raise RuntimeError('unexpected_source_commit')
 if free_space()<19*1024**3:raise RuntimeError('insufficient_19GiB_preflight')
 if not ASSET.is_file() or ASSET.is_symlink() or ASSET.stat().st_uid!=os.getuid() or ASSET.stat().st_size!=123762120:raise RuntimeError('unapproved_compressed_official_clickhouse_asset')
 if (ASSET.parent/'.flind-wave188-owner').read_text()!='FLIND_WAVE188_CLICKHOUSE_SUPPORTED_DURABLE_V1\n':raise RuntimeError('unowned_source_asset')
 if ASSET.stat().st_nlink!=1:raise RuntimeError('mutable_hardlink_to_compressed_binary_refused')
 with ASSET.open('rb') as f:
  if hashlib.file_digest(f,'sha256').hexdigest()!=EXPECTED_SHA:raise RuntimeError('official_compressed_clickhouse_sha256_mismatch')
 source=ORIGINAL.read_text()
 expected_git_blob='aa993e44eb204f118392a1e0a483fcfa2e201566'
 actual_git_blob=subprocess.check_output(['git','-C',str(CHECKOUT),'hash-object',str(ORIGINAL)],text=True).strip()
 if actual_git_blob!=expected_git_blob:raise RuntimeError('first_party_migrate_clickhouse_source_blob_changed')
 for exact in ("CREATE DATABASE IF NOT EXISTS {database} ON CLUSTER {cluster}",
    "CREATE TABLE IF NOT EXISTS {database}.infi_clickhouse_orm_migrations",
    "ENGINE = ReplicatedMergeTree(", "'/clickhouse/prod/tables/noshard/{{database}}/{{table}}'",
    "ENGINE = Distributed({cluster}, {database}, infi_clickhouse_orm_migrations, rand())"):
  if exact not in source:raise RuntimeError('original_first_party_migration_tracking_ddl_drift')
 SCRATCH.mkdir(mode=0o700);write(SCRATCH/'.flind-owner-only',MARKER)
 exe=SCRATCH/'clickhouse-25.12-official'
 shutil.copyfile(ASSET,exe);exe.chmod(0o700)
 # Official decompression is triggered once; strict resource reserve applies.
 v=subprocess.run([str(exe),'--version'],capture_output=True,timeout=40,check=False)
 if v.returncode!=0 or b'25.12.7.21' not in v.stdout:raise RuntimeError('unsupported_running_clickhouse')
 REPORT['real_keeper_version_supported']=True
 if free_space()<FLOOR+1024**3:raise RuntimeError('post_unpack_disk_reserve')
 zk_port,raft_port,sql_port,http_port,interserver_port=map(lambda _:port(),range(5))
 if len({zk_port,raft_port,sql_port,http_port,interserver_port})<5:raise RuntimeError('port_collision')
 for folder in ('data','tmp','user_files','format_schemas','logs','keeper','keeper/log','keeper/snapshots'):
  (SCRATCH/folder).mkdir(parents=True,exist_ok=True)
 keeper_config=SCRATCH/'keeper.xml'
 write(keeper_config,f"""<clickhouse>
 <logger><level>warning</level><console>1</console></logger>
 <listen_host>127.0.0.1</listen_host>
 <keeper_server>
  <tcp_port>{zk_port}</tcp_port>
  <server_id>1</server_id>
  <log_storage_path>{xml_path(SCRATCH/'keeper/log')}</log_storage_path>
  <snapshot_storage_path>{xml_path(SCRATCH/'keeper/snapshots')}</snapshot_storage_path>
  <coordination_settings><operation_timeout_ms>8000</operation_timeout_ms><session_timeout_ms>12000</session_timeout_ms></coordination_settings>
  <raft_configuration><server><id>1</id><hostname>127.0.0.1</hostname><port>{raft_port}</port></server></raft_configuration>
 </keeper_server>
 <four_letter_word_white_list>ruok,stat</four_letter_word_white_list>
 </clickhouse>""")
 users=SCRATCH/'users.xml'
 write(users,"<clickhouse><profiles><default><max_memory_usage>134217728</max_memory_usage></default></profiles><users><default><password></password><networks><ip>127.0.0.1</ip></networks><profile>default</profile><quota>default</quota></default></users><quotas><default/></quotas></clickhouse>")
 serverconf=SCRATCH/'config.xml'
 write(serverconf,f"""<clickhouse>
 <logger><level>warning</level><console>1</console></logger>
 <listen_host>127.0.0.1</listen_host><http_port>{http_port}</http_port><tcp_port>{sql_port}</tcp_port><interserver_http_port>{interserver_port}</interserver_http_port><interserver_http_host>127.0.0.1</interserver_http_host>
 <path>{xml_path(SCRATCH/'data')}/</path><tmp_path>{xml_path(SCRATCH/'tmp')}/</tmp_path>
 <user_files_path>{xml_path(SCRATCH/'user_files')}/</user_files_path>
 <format_schema_path>{xml_path(SCRATCH/'format_schemas')}/</format_schema_path>
 <users_config>{xml_path(users)}</users_config>
 <max_server_memory_usage>805306368</max_server_memory_usage>
 <background_pool_size>16</background_pool_size><background_schedule_pool_size>2</background_schedule_pool_size>
 <remote_servers><{CLUSTER}><shard><replica><host>127.0.0.1</host><port>{sql_port}</port></replica></shard></{CLUSTER}></remote_servers>
 <macros><shard>01</shard><replica>replica01</replica></macros>
 <zookeeper><node><host>127.0.0.1</host><port>{zk_port}</port></node></zookeeper>
 <distributed_ddl><path>/clickhouse/task_queue/ddl</path></distributed_ddl>
 </clickhouse>""")
 env={**os.environ,'HOME':str(SCRATCH),'TMPDIR':str(SCRATCH),'GIT_TERMINAL_PROMPT':'0'}
 keeper=start([str(exe),'keeper',f'--config-file={keeper_config}'],'keeper',env)
 deadline=time.monotonic()+24
 while time.monotonic()<deadline:
  if keeper.poll() is not None:raise RuntimeError('keeper_exited_before_ready')
  if keeper_ready(zk_port):break
  if free_space()<FLOOR:raise RuntimeError('disk_floor')
  time.sleep(.4)
 else:raise RuntimeError('keeper_readiness_timeout')
 server=start([str(exe),'server',f'--config-file={serverconf}'],'clickhouse_server',env)
 deadline=time.monotonic()+32
 while time.monotonic()<deadline:
  if server.poll() is not None:raise RuntimeError('clickhouse_server_exited_before_ready')
  try:
   if http_sql(http_port,'SELECT 1')=='1':break
  except (RuntimeError,OSError,TimeoutError):pass
  if free_space()<FLOOR:raise RuntimeError('disk_floor')
  time.sleep(.5)
 else:raise RuntimeError('clickhouse_server_readiness_timeout')
 if http_sql(http_port,'SELECT version()')!='25.12.7.21':raise RuntimeError('running_version_not_supported')
 if http_sql(http_port,f"SELECT count() FROM system.clusters WHERE cluster='{CLUSTER}'")!='1':
  raise RuntimeError('source_defined_cluster_not_single_node')
 REPORT['one_node_cluster_qualified']=True
 # The three DDLs below are the exact first-party migration tracking SQL
 # templates rendered with this isolated scratch DB and cluster name.
 http_sql(http_port,f'CREATE DATABASE IF NOT EXISTS {DB} ON CLUSTER {CLUSTER}')
 sql1=f"""CREATE TABLE IF NOT EXISTS {DB}.infi_clickhouse_orm_migrations
 ON CLUSTER {CLUSTER} (package_name String,module_name String,applied Date)
 ENGINE = ReplicatedMergeTree(
 '/clickhouse/prod/tables/noshard/{{database}}/{{table}}',
 '{{replica}}-{{shard}}')
 PARTITION BY toYYYYMM(applied)
 ORDER BY (package_name,module_name)
 SETTINGS index_granularity = 8192"""
 http_sql(http_port,sql1)
 REPORT['replicated_tracking_table_qualified']=True
 sql2=f"""CREATE TABLE IF NOT EXISTS {DB}.infi_clickhouse_orm_migrations_distributed
 ON CLUSTER {CLUSTER} (package_name String,module_name String,applied Date)
 ENGINE = Distributed({CLUSTER}, {DB}, infi_clickhouse_orm_migrations, rand())"""
 http_sql(http_port,sql2)
 actual=http_sql(http_port,f"SELECT engine FROM system.tables WHERE database='{DB}' ORDER BY name FORMAT TSVRaw")
 if actual.splitlines()!=['ReplicatedMergeTree','Distributed']:
  # Sorted by names 'infi...migrations' then '...distributed'
  if sorted(actual.splitlines())!=['Distributed','ReplicatedMergeTree']:raise RuntimeError('wrong_engine_kind')
 REPORT['distributed_tracking_table_qualified']=True
 replicas=''
 deadline=time.monotonic()+28
 while time.monotonic()<deadline:
  if free_space()<FLOOR:raise RuntimeError('disk_floor_during_replica_poll')
  replicas=http_sql(http_port,f"SELECT is_readonly,is_session_expired,replica_name FROM system.replicas WHERE database='{DB}' FORMAT TSVRaw")
  if replicas=='0\t0\treplica01-01':break
  time.sleep(.6)
 if replicas!='0\t0\treplica01-01':
  details=http_sql(http_port,f"SELECT is_leader,is_readonly,is_session_expired,total_replicas,active_replicas,replica_path,zookeeper_exception FROM system.replicas WHERE database='{DB}' FORMAT TSVRaw")
  REPORT['replica_diagnostics']=details[:300]
  try:
   http_sql(http_port,f"INSERT INTO {DB}.infi_clickhouse_orm_migrations (package_name,module_name,applied) VALUES ('flind_wave259','synthetic_probe','2026-10-29')")
   REPORT['synthetic_tracking_row_write']=True
  except Exception as e:REPORT['synthetic_tracking_row_write']=False;REPORT['synthetic_write_error']=str(e)[:300]
  try:
   zk=http_sql(http_port,"SELECT name,host,port,is_expired FROM system.zookeeper_connection FORMAT TSVRaw")
   REPORT['zookeeper_connection']=zk[:200]
  except Exception as e:REPORT['zookeeper_connection_error']=str(e)[:200]
  raise RuntimeError('replication_not_healthy_'+replicas[:70])
 sqlread=http_sql(http_port,f"SELECT count() FROM {DB}.infi_clickhouse_orm_migrations_distributed")
 if sqlread!='0':raise RuntimeError('distributed_initial_readback_not_empty')
 http_sql(http_port,f"INSERT INTO {DB}.infi_clickhouse_orm_migrations (package_name,module_name,applied) VALUES ('flind_wave260_synthetic_probe','safe_owner_only_probe','2026-10-29')")
 readback=http_sql(http_port,f"SELECT package_name,module_name,applied FROM {DB}.infi_clickhouse_orm_migrations_distributed FORMAT TSVRaw")
 if readback!='flind_wave260_synthetic_probe\tsafe_owner_only_probe\t2026-10-29':
  raise RuntimeError('real_distributed_replica_insert_readback_mismatch_'+readback[:90])
 REPORT['real_replica_write_distributed_readback_qualified']=True
 # Execute the exact git-pinned infi.clickhouse_orm Database.migrate on ONE
 # synthetic, specifically whitelisted migration package. Never import or run
 # any PostHog production migrations or its Django management command.
 import importlib.metadata
 from infi.clickhouse_orm import Database
 if importlib.metadata.version('infi-clickhouse-orm')!='2.1.0.post20':
  raise RuntimeError('infi_clickhouse_orm_lock_version_drift')
 direct_url=importlib.metadata.distribution('infi-clickhouse-orm').read_text('direct_url.json')
 if not direct_url:
  raise RuntimeError('infi_clickhouse_orm_source_git_provenance_missing')
 vcs=json.loads(direct_url).get('vcs_info',{})
 pinned_commit='4e3996becf66bf5c26580aff12a80425d9d56fe5'
 if vcs.get('vcs')!='git' or vcs.get('commit_id')!=pinned_commit:
  raise RuntimeError('infi_clickhouse_orm_git_commit_mismatch')
 if free_space()<FLOOR:
  raise RuntimeError('disk_floor_before_actual_infi_migrate')
 pkgname='flind_wave260_synthetic_one_migration'
 srcdir=SCRATCH/'migration_python'
 package=srcdir/pkgname
 package.mkdir(parents=True)
 write(package/'__init__.py','# isolated synthetic owner-only migration package\n')
 migration_statement=f'CREATE TABLE IF NOT EXISTS {DB}.flind_wave260_synthetic_schema ON CLUSTER {CLUSTER} (event_id UInt64, team_id UInt64) ENGINE = MergeTree ORDER BY event_id'
 if not migration_statement.startswith(f'CREATE TABLE IF NOT EXISTS {DB}.flind_wave260_synthetic_schema ON CLUSTER {CLUSTER} '):
  raise RuntimeError('unapproved_migration_sql')
 # This hardcoded Python source contains no side effects except a RunSQL op.
 write(package/'0001_synthetic_schema.py','from infi.clickhouse_orm.migrations import RunSQL\noperations = [RunSQL('+repr(migration_statement)+')]\n')
 import sys
 sys.path.insert(0,str(srcdir))
 database=Database(DB,db_url=f'http://127.0.0.1:{http_port}/',
                   username='default',password='',cluster=CLUSTER,
                   autocreate=False,randomize_replica_paths=False,trust_env=False,
                   timeout=10)
 database.migrate(pkgname,up_to=1,replicated=True)
 first=http_sql(http_port,f"SELECT package_name,module_name FROM {DB}.infi_clickhouse_orm_migrations_distributed WHERE package_name='{pkgname}' FORMAT TSVRaw")
 if first!=pkgname+'\t0001_synthetic_schema':
  raise RuntimeError('original_infi_migration_not_recorded_'+first[:100])
 if http_sql(http_port,f"SELECT engine FROM system.tables WHERE database='{DB}' AND name='flind_wave260_synthetic_schema'")!='MergeTree':
  raise RuntimeError('synthetic_infi_sql_migration_missing_table')
 REPORT['real_infi_synthetic_migration_applied']=True
 database.migrate(pkgname,up_to=1,replicated=True)
 second=http_sql(http_port,f"SELECT count() FROM {DB}.infi_clickhouse_orm_migrations_distributed WHERE package_name='{pkgname}'")
 if second!='1':
  raise RuntimeError('infi_repeated_migration_not_idempotent_'+second)
 REPORT['real_infi_migration_repeat_noop']=True
 REPORT['infi_migration_runner_executed']=True
 REPORT['infi_source_git_pin']='4e3996becf66bf5c26580aff12a80425d9d56fe5'
 REPORT['original_flind_django_migrate_command_executed']=False
 REPORT['first_party_tracking_ddl_executed']=True
 REPORT['readback_empty_migration_history_pass']=True
 REPORT['one_node_replica_healthy']=True
 REPORT['source_scope']='original infi ORM engine against a single synthetic fixture; NOT actual Flind Django command or its 345 migrations'
 REPORT['observed_keeper_listener']='127.0.0.1'
 REPORT['observed_clickhouse_version']='25.12.7.21'

def main():
 try:
  run()
 except Exception as e:
  REPORT['blocker']=str(e)[:350]
 finally:
  stop_all()
  REPORT['owned_children_stopped']=all(p.poll() is not None for _,p in children)
  REPORT['free_gib_after']=round(free_space()/1024**3,3)
  if SCRATCH.is_dir() and not SCRATCH.is_symlink() and SCRATCH.parent==ROOT and (SCRATCH/'.flind-owner-only').read_text()==MARKER:
   logs={}
   for name,_p in children:
    f=SCRATCH/(name+'.log')
    if f.exists():
     lines=f.read_text(errors='replace').splitlines()
     logs[name]=lines[-1][:220] if lines else ''
   if 'blocker' in REPORT:
    REPORT['diagnostic_tail']=logs
    for name,_p in children:
     f=SCRATCH/(name+'.log')
     if f.exists():
      lines=[x.strip()[:280] for x in f.read_text(errors='replace').splitlines()
             if '<Error>' in x or '<Warning>' in x or 'readonly' in x.lower() or 'keeper' in x.lower()]
      REPORT[name+'_errors_tail']=lines[-9:]
   shutil.rmtree(SCRATCH)
   REPORT['owner_scratch_cleaned']=True
  else:REPORT['owner_scratch_cleaned']=False
  print(json.dumps(REPORT,sort_keys=True),flush=True)
 return 0 if (REPORT['first_party_tracking_ddl_executed'] and REPORT['owned_children_stopped'] and REPORT['owner_scratch_cleaned']) else 2

if __name__=='__main__':raise SystemExit(main())
