"""Bounded owner-only REAL ClickHouse25.12 Keeper+one-node migrations metadata prerequisite."""
from __future__ import annotations
import hashlib,json,os,pathlib,shutil,signal,socket,subprocess,time
from http.client import HTTPConnection
from xml.sax.saxutils import escape
ROOT=pathlib.Path('/private/tmp')
CHECKOUT=ROOT/'flind-wave295-original-django-0020/source'
ORIGINAL=CHECKOUT/'posthog/management/commands/migrate_clickhouse.py'
ASSET=ROOT/'flind-wave188-ch2512-durable/clickhouse-original-compressed-aarch64'
SCRATCH=ROOT/'flind-wave298-clickhouse-0020-optimized'
MARKER='FLIND_WAVE298_OWNER_ONLY_REAL_DJANGO_APPLY_0020_OPTIMIZED_V1\n'
EXPECTED_SHA='e5be46727e773893b5786aaa3d28f5661a30179fe65e19096d8eb7d41a554fd6'
DB='flind_wave298_optimized_synthetic'
CLUSTER='posthog_migrations'
FLOOR=int(15.5*1024**3)
REPORT={'phase':'wave298_original_django_cli_apply_0001_0020_optimized',
 'source_git_sha':'6e5da8f24fb04312ea1dd7778811ca1b21339fd9',
 'first_party_tracking_ddl_executed':False,'real_keeper_version_supported':False,
 'one_node_cluster_qualified':False,'replicated_tracking_table_qualified':False,
 'distributed_tracking_table_qualified':False,'infi_migration_runner_executed':False,
 'original_0001_sql_direct_applied':False,'original_Django_command_executed':False,'full_original_migrations_executed':False,'multinode_replication_qualified':False,
 'release_qualified':False}
LIVE_SOURCE="import os,sys,socket,json,contextlib,io,importlib\nfrom unittest.mock import patch\nport=int(sys.argv[1]);scratch=sys.argv[2];source=sys.argv[3];dbname=sys.argv[4];native_port=int(sys.argv[5])\norig_connect=socket.socket.connect\ndef owner_only(sock,address):\n    if not isinstance(address,tuple) or address[0] not in ('127.0.0.1','localhost') or address[1] not in (port,native_port):\n        raise RuntimeError('FLIND_W298_FOREIGN_NETWORK_REFUSED')\n    return orig_connect(sock,address)\nsocket.socket.connect=owner_only\nsocket.socket.connect_ex=lambda *a,**kw: (_ for _ in ()).throw(RuntimeError('FLIND_W298_CONNECT_EX_REFUSED'))\nos.environ.clear()\nos.environ.update({'PATH':'/usr/bin:/bin:/opt/homebrew/bin','HOME':scratch,'TMPDIR':scratch,'PYTHONDONTWRITEBYTECODE':'1',\n 'DJANGO_SETTINGS_MODULE':'posthog.settings','SECRET_KEY':'flind-wave288-synthetic-only',\n 'DATABASE_URL':'postgresql://invalid@127.0.0.1:1/flind_wave298_optimized_synthetic',\n 'REDIS_URL':'redis://127.0.0.1:1/0','CLICKHOUSE_HOST':'127.0.0.1',\n 'CLICKHOUSE_HTTP_URL':'http://127.0.0.1:'+str(port),'CLICKHOUSE_DATABASE':dbname,\n 'CLICKHOUSE_CLUSTER':'posthog','CLICKHOUSE_SECURE':'false',\n 'CLICKHOUSE_MIGRATIONS_HOST':'127.0.0.1','CLICKHOUSE_SATELLITE_CLUSTERS':'',\n 'CLICKHOUSE_MIGRATIONS_CLUSTER':'posthog_migrations','KAFKA_HOSTS':'127.0.0.1:1','SENTRY_DSN':''})\nsys.path.insert(0,source)\nimport django\ndjango.setup()\nfrom django.core.management import call_command,get_commands\nfrom clickhouse_driver import Client\nimport posthog.clickhouse.cluster as cluster_module\nimport posthog.management.commands.migrate_clickhouse as cmd_mod\nif get_commands().get('migrate_clickhouse')!='posthog':raise RuntimeError('FLIND_W298_UNEXPECTED_MIGRATION_COMMAND')\ncmd_mod.CLICKHOUSE_HTTP_URL='http://127.0.0.1:'+str(port)+'/'\ndef private_bootstrap(*args,**kwargs):\n    if kwargs.get('host') not in (None,'127.0.0.1'):raise RuntimeError('FLIND_W298_FOREIGN_BOOTSTRAP_HOST')\n    return Client(host='127.0.0.1',port=native_port,secure=False,user='default',password='',database='system')\ndef private_target(host,port):\n    if host not in ('127.0.0.1','localhost'):raise RuntimeError('FLIND_W298_FOREIGN_CLUSTER_TARGET')\n    return ('127.0.0.1',native_port)\nee_cols=importlib.import_module('ee.clickhouse.materialized_columns.columns')\ndef owner_only_native_execute(sql,params=None,**kwargs):\n    client=Client(host='127.0.0.1',port=native_port,secure=False,user='default',password='',database=dbname)\n    try:return client.execute(sql,params)\n    finally:client.disconnect()\nwith patch.object(ee_cols,'sync_execute',side_effect=owner_only_native_execute),patch.object(cluster_module,'default_client',side_effect=private_bootstrap),patch.object(cluster_module,'_resolve_connection_target',side_effect=private_target):\n    first=io.StringIO()\n    with contextlib.redirect_stdout(first):\n        call_command('migrate_clickhouse',upto=20,verbosity=0)\n    if 'Migration successful' not in first.getvalue():raise RuntimeError('FLIND_W298_FIRST_APPLY_FAILED')\n    second=io.StringIO()\n    with contextlib.redirect_stdout(second):\n        call_command('migrate_clickhouse',upto=20,verbosity=0)\n    if 'Migration successful' not in second.getvalue():raise RuntimeError('FLIND_W298_SECOND_APPLY_FAILED')\n    plan=io.StringIO()\n    with contextlib.redirect_stdout(plan):\n        call_command('migrate_clickhouse',plan=True,upto=20,verbosity=0)\n    if 'Clickhouse migrations up to date!' not in plan.getvalue():raise RuntimeError('FLIND_W298_PLAN_NOT_EMPTY_'+plan.getvalue()[-350:])\n    check=io.StringIO()\n    with contextlib.redirect_stdout(check):\n        call_command('migrate_clickhouse',check=True,upto=20,verbosity=0)\n    if 'Clickhouse migrations up to date!' not in check.getvalue():raise RuntimeError('FLIND_W298_CHECK_NOT_EMPTY')\nprint(json.dumps({'original_django_call_command_apply':True,'original_django_second_apply_noop':True,'original_django_plan_check_upto1_empty':True,'original_source_import':'all_original_migrations','endpoint_wiring':'test_only_owner_loopback_override'}),flush=True)\n"

RENDER_SOURCE="import os,sys,socket,json,importlib\ndef deny(*a,**k):raise RuntimeError('W269_NO_RENDER_NETWORK')\nsocket.socket.connect=deny\nsocket.socket.connect_ex=deny\nsocket.create_connection=deny\nos.environ.clear()\nos.environ.update({'PATH':'/usr/bin:/bin:/opt/homebrew/bin','HOME':sys.argv[1],'TMPDIR':sys.argv[1],\n 'PYTHONDONTWRITEBYTECODE':'1','DJANGO_SETTINGS_MODULE':'posthog.settings',\n 'SECRET_KEY':'flind-wave269-synthetic-only',\n 'DATABASE_URL':'postgresql://flind_invalid@127.0.0.1:1/flind_wave269_synthetic',\n 'REDIS_URL':'redis://127.0.0.1:1/0','CLICKHOUSE_HOST':'127.0.0.1',\n 'CLICKHOUSE_DATABASE':'flind_wave269_synthetic','CLICKHOUSE_CLUSTER':'posthog',\n 'CLICKHOUSE_MIGRATIONS_CLUSTER':'posthog_migrations','KAFKA_HOSTS':'127.0.0.1:1','SENTRY_DSN':''})\nsys.path.insert(0,sys.argv[2])\nimport django\ndjango.setup()\nm=importlib.import_module('posthog.clickhouse.migrations.0001_initial')\nprint(json.dumps([op._sql for op in m.operations]),flush=True)\n"
children=[]
def free_space():
 return shutil.disk_usage(ROOT).free
def port():
 with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
  s.bind(('127.0.0.1',0));return s.getsockname()[1]
def write(path,data):path.write_text(data);path.chmod(0o600)
def xml_path(path):return escape(str(path))
def http_sql(port_num,statement,database=False):
 if type(port_num) is not int or port_num<1024 or port_num>65535 or not statement.isascii() or len(statement)>12000:raise ValueError('unsafe_or_nonloopback_query')
 conn=HTTPConnection('127.0.0.1',port_num,timeout=11)
 try:
  conn.request('POST','/?wait_end_of_query=1'+('&database='+DB if database else ''),statement.encode('ascii'),
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
 expected_git_blob='711cb55e01a19b16bc8f95478010574654560db3'
 actual_git_blob=subprocess.check_output(['git','-C',str(CHECKOUT),'hash-object',str(ORIGINAL)],text=True).strip()
 if actual_git_blob!=expected_git_blob:raise RuntimeError('first_party_migrate_clickhouse_source_blob_changed')
 migration_path=CHECKOUT/'posthog/clickhouse/migrations/0001_initial.py'
 migration_blob=subprocess.check_output(['git','-C',str(CHECKOUT),'hash-object',str(migration_path)],text=True).strip()
 if migration_blob!='9c7bb587ed038654464fcd877527b84110076698':raise RuntimeError('original_0001_git_blob_drift')
 REPORT['original_command_git_blob']=actual_git_blob
 REPORT['original_0001_git_blob']=migration_blob
 migration_0002=CHECKOUT/'posthog/clickhouse/migrations/0002_events_materialized.py'
 second_blob=subprocess.check_output(['git','-C',str(CHECKOUT),'hash-object',str(migration_0002)],text=True).strip()
 if second_blob!='c5928ce6670863ad54c2e4f9dd93b789646a98ac':raise RuntimeError('original_0002_git_blob_drift')
 if 'operations = [run_sql_with_exceptions("SELECT 1")]' not in migration_0002.read_text():raise RuntimeError('original_0002_sentinel_drift')
 REPORT['original_0002_git_blob']=second_blob
 third_path=CHECKOUT/'posthog/clickhouse/migrations/0003_person.py'
 third_sha=subprocess.check_output(['git','-C',str(CHECKOUT),'hash-object',str(third_path)],text=True).strip()
 if third_sha!='c1309e6ae6d3a1b596c0f82ee2e16ff396832332':raise RuntimeError('original_0003_git_blob_drift')
 REPORT['original_0003_git_blob']=third_sha
 fourth_path=CHECKOUT/'posthog/clickhouse/migrations/0004_kafka.py'
 fourth_sha=subprocess.check_output(['git','-C',str(CHECKOUT),'hash-object',str(fourth_path)],text=True).strip()
 if fourth_sha!='3280209971bbf07c805cf10a23026b439fcadcbf':raise RuntimeError('original_0004_git_blob_drift')
 REPORT['original_0004_git_blob']=fourth_sha
 sixth_path=CHECKOUT/'posthog/clickhouse/migrations/0006_session_recording_events.py'
 sixth_sha=subprocess.check_output(['git','-C',str(CHECKOUT),'hash-object',str(sixth_path)],text=True).strip()
 if sixth_sha!='75fbbf6e61d4feb4aeb783287a052e3b69106128':raise RuntimeError('0006 historical empty migration drift')
 seventh_path=CHECKOUT/'posthog/clickhouse/migrations/0007_static_cohorts_table.py'
 seventh_sha=subprocess.check_output(['git','-C',str(CHECKOUT),'hash-object',str(seventh_path)],text=True).strip()
 if seventh_sha!='d3812a6722c47e321bf5ae5ff415463648f5760a':raise RuntimeError('0007 static cohort source drift')
 REPORT['original_0006_git_blob']=sixth_sha
 REPORT['original_0007_git_blob']=seventh_sha
 for name,pin in (
  ('0008_plugin_log_entries.py','da6eb0bebededad2988f26c36966f4aaf52f038a'),
  ('0009_person_deleted_column.py','67ec90b46ac3e7fb40f2977390c595b48122ca3f'),
  ('0010_cohortpeople.py','2ca3c5ab34fb3a7e95d34f5b04f3404c0a91f7f4'),
 ):
  path=CHECKOUT/'posthog/clickhouse/migrations'/name
  actual=subprocess.check_output(['git','-C',str(CHECKOUT),'hash-object',str(path)],text=True).strip()
  if actual!=pin:raise RuntimeError('source_migration_drift_'+name)
  REPORT['migration_blob_'+name]=actual
 for name,pin in (
  ('0011_cohortpeople_no_shard.py','8305d46e0b37d428546e312ab5e777ca277cf664'),
  ('0012_person_id_deleted_column.py','a8b5a2ef057859abaf7f0b5add70431ac2258865'),
  ('0013_persons_distinct_ids_column.py','fd62e3cceefbf3894c4ec0a6a19666d88df16b03'),
  ('0014_persons_distinct_ids_column_remove.py','7982034b2ca2a9b2f452cf1dae594de08e69f362'),
  ('0015_materialized_column_comments.py','44aa353daf0ebd0f3dcae888d925b522bc95330b'),
 ):
  path=CHECKOUT/'posthog/clickhouse/migrations'/name
  actual=subprocess.check_output(['git','-C',str(CHECKOUT),'hash-object',str(path)],text=True).strip()
  if actual!=pin:raise RuntimeError('original_later_source_drift_'+name)
  REPORT['migration_blob_'+name]=actual
 for name,pin in (
  ('0016_collapsing_person_distinct_id.py','2e5dc2c46b2948ee38bf5f64311fb80b3b271265'),
  ('0017_events_dead_letter_queue.py','bdabeba226fac91a4a41c5c9397b1e56ef8e7561'),
  ('0018_group_analytics_schema.py','c35f8ca2d59c800bad92bb894cf4d256dbc175cd'),
  ('0019_group_analytics_materialized_columns.py','1b02f1cb6f3b70bb88a95630726420e671c31ef8'),
  ('0020_session_recording_events_window_id.py','75fbbf6e61d4feb4aeb783287a052e3b69106128'),
 ):
  path=CHECKOUT/'posthog/clickhouse/migrations'/name
  actual=subprocess.check_output(['git','-C',str(CHECKOUT),'hash-object',str(path)],text=True).strip()
  if actual!=pin:raise RuntimeError('W295_original_migration_drift_'+name)
  REPORT['migration_blob_'+name]=actual



 migration_tools_blob=subprocess.check_output(['git','-C',str(CHECKOUT),'hash-object',str(CHECKOUT/'posthog/clickhouse/client/migration_tools.py')],text=True).strip()
 if migration_tools_blob!='17a082e56f6c2825279e8337d1572be921b0aeac':raise RuntimeError('current_migration_tools_git_blob_drift')
 REPORT['original_migration_tools_git_blob']=migration_tools_blob
 for exact in ("CREATE DATABASE IF NOT EXISTS {database} ON CLUSTER {cluster}",
    "CREATE TABLE IF NOT EXISTS {database}.infi_clickhouse_orm_migrations",
    "ENGINE = ReplicatedMergeTree(", "'/clickhouse/prod/tables/noshard/{{database}}/{{table}}'",
    "ENGINE = Distributed({cluster}, {database}, infi_clickhouse_orm_migrations, rand())"):
  if exact not in source:raise RuntimeError('original_first_party_migration_tracking_ddl_drift')
 SCRATCH.mkdir(mode=0o700);write(SCRATCH/'.flind-owner-only',MARKER)
 exe=SCRATCH/'clickhouse-25.12-official'
 shutil.copyfile(ASSET,exe);exe.chmod(0o700)
 # Official decompression is triggered once; strict resource reserve applies.
 v=subprocess.run([str(exe),'--version'],capture_output=True,timeout=100,check=False)
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
 <remote_servers><posthog><shard><replica><host>127.0.0.1</host><port>{sql_port}</port></replica></shard></posthog><{CLUSTER}><shard><replica><host>127.0.0.1</host><port>{sql_port}</port></replica></shard></{CLUSTER}></remote_servers>
 <macros><shard>01</shard><replica>replica01</replica><hostClusterType>online</hostClusterType><hostClusterRole>data</hostClusterRole></macros>
 <named_collections><msk_cluster><kafka_broker_list>127.0.0.1:1</kafka_broker_list></msk_cluster></named_collections>
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
 http_sql(http_port,f"INSERT INTO {DB}.infi_clickhouse_orm_migrations (package_name,module_name,applied) VALUES ('flind_wave259_synthetic','safe_owner_only_probe','2026-10-29')")
 readback=http_sql(http_port,f"SELECT package_name,module_name,applied FROM {DB}.infi_clickhouse_orm_migrations_distributed FORMAT TSVRaw")
 if readback!='flind_wave259_synthetic\tsafe_owner_only_probe\t2026-10-29':
  raise RuntimeError('real_distributed_replica_insert_readback_mismatch_'+readback[:90])
 REPORT['real_replica_write_distributed_readback_qualified']=True
 # Snapshot the exact owned database's metadata before and after the actual first-party Django CLI apply.
 snapshot_sql=f"SELECT name,engine,create_table_query FROM system.tables WHERE database='{DB}' ORDER BY name FORMAT JSONEachRow"
 before_tables=http_sql(http_port,snapshot_sql)
 before_history=http_sql(http_port,f"SELECT module_name FROM {DB}.infi_clickhouse_orm_migrations_distributed WHERE package_name='posthog.clickhouse.migrations' ORDER BY module_name FORMAT TSVRaw")
 if before_history:raise RuntimeError('original_migration_history_not_empty_before_apply')
 child=SCRATCH/'run_original_django_apply_0001.py'
 write(child,LIVE_SOURCE)
 venv=ROOT/'flind-wave267-full-runtime/venv/bin/python'
 if not venv.is_file():raise RuntimeError('source_locked_python_missing')
 if free_space()<FLOOR+500*1024**2:raise RuntimeError('disk_reserve_before_live_apply')
 result=subprocess.run([str(venv),'-O','-B',str(child),str(http_port),str(SCRATCH),str(CHECKOUT),DB,str(sql_port)],
    cwd=SCRATCH,env={**os.environ,'HOME':str(SCRATCH),'TMPDIR':str(SCRATCH),'PYTHONDONTWRITEBYTECODE':'1'},
    capture_output=True,text=True,timeout=125)
 if result.returncode:
  raise RuntimeError('real_original_django_apply_failed_'+result.stderr[-750:].replace('\n',' '))
 observed=json.loads(result.stdout.strip().splitlines()[-1])
 if not observed.get('original_django_call_command_apply'):raise RuntimeError('original_command_not_executed')
 after_history=http_sql(http_port,f"SELECT module_name FROM {DB}.infi_clickhouse_orm_migrations_distributed WHERE package_name='posthog.clickhouse.migrations' ORDER BY module_name FORMAT TSVRaw")
 if after_history!='0001_initial\n0002_events_materialized\n0003_person\n0004_kafka\n0006_session_recording_events\n0007_static_cohorts_table\n0008_plugin_log_entries\n0009_person_deleted_column\n0010_cohortpeople\n0011_cohortpeople_no_shard\n0012_person_id_deleted_column\n0013_persons_distinct_ids_column\n0014_persons_distinct_ids_column_remove\n0015_materialized_column_comments\n0016_collapsing_person_distinct_id\n0017_events_dead_letter_queue\n0018_group_analytics_schema\n0019_group_analytics_materialized_columns\n0020_session_recording_events_window_id':raise RuntimeError('wrong_original_migration_history_'+after_history[:150])
 table_engine=http_sql(http_port,f"SELECT engine FROM system.tables WHERE database='{DB}' AND name='sharded_events' FORMAT TSVRaw")
 if table_engine!='ReplicatedReplacingMergeTree':raise RuntimeError('original_sharded_events_engine_mismatch_'+table_engine)
 after_tables=http_sql(http_port,snapshot_sql)
 if before_tables==after_tables:raise RuntimeError('original_migration_created_no_table')
 # Current original 0003 creates two person tables in the synthetic DB.
 person_tables=http_sql(http_port,f"SELECT name,engine FROM system.tables WHERE database='{DB}' AND name IN ('person','person_distinct_id') ORDER BY name FORMAT TSVRaw")
 if len(person_tables.splitlines())!=2 or not all('MergeTree' in row for row in person_tables.splitlines()):
  raise RuntimeError('original_0003_real_person_tables_missing_or_wrong_'+person_tables[:200])
 REPORT['original_0003_person_tables']=person_tables.splitlines()
 original_0004_tables=http_sql(http_port,f"SELECT name,engine FROM system.tables WHERE database='{DB}' AND name IN ('kafka_person','kafka_person_distinct_id','person_mv','person_distinct_id_mv','writable_events','events') ORDER BY name FORMAT TSVRaw")
 REPORT['original_0004_six_objects']=original_0004_tables.splitlines()
 if len(REPORT['original_0004_six_objects'])!=6:
  raise RuntimeError('original_0004_six_objects_missing_'+original_0004_tables[:500])
 for k in ['kafka_person\tKafka','kafka_person_distinct_id\tKafka','person_mv\tMaterializedView','person_distinct_id_mv\tMaterializedView','writable_events\tDistributed','events\tDistributed']:
  if k not in REPORT['original_0004_six_objects']:raise RuntimeError('original_0004_wrong_engine_'+k)
 cohort=http_sql(http_port,f"SELECT name,engine FROM system.tables WHERE database='{DB}' AND name='person_static_cohort' FORMAT TSVRaw")
 if cohort!='person_static_cohort\tReplicatedReplacingMergeTree':
  raise RuntimeError('original_0007_missing_static_cohort_'+cohort)
 REPORT['original_0007_static_cohort_engine']=cohort

 wanted=[
  'cohortpeople\tReplicatedCollapsingMergeTree',
  'kafka_plugin_log_entries\tKafka',
  'plugin_log_entries\tReplicatedReplacingMergeTree',
  'plugin_log_entries_mv\tMaterializedView',
 ]
 rows=http_sql(http_port,f"SELECT name,engine FROM system.tables WHERE database='{DB}' AND name IN ('cohortpeople','kafka_plugin_log_entries','plugin_log_entries','plugin_log_entries_mv') ORDER BY name FORMAT TSVRaw")
 if rows.splitlines()!=wanted:
  raise RuntimeError('unexpected_later_objects_'+repr(rows[:350]))
 REPORT['later_objects_0008_to_0010']=rows.splitlines()
 column=http_sql(http_port,f"SELECT count() FROM system.columns WHERE database='{DB}' AND table='person' AND name='is_deleted' FORMAT TSVRaw")
 if column!='1':raise RuntimeError('person_is_deleted_missing')
 REPORT['person_is_deleted_column_qualified']=True
 both=http_sql(http_port,f"SELECT table,name FROM system.columns WHERE database='{DB}' AND table IN ('person','person_distinct_id') AND name='is_deleted' ORDER BY table FORMAT TSVRaw")
 if both!='person\tis_deleted\nperson_distinct_id\tis_deleted':
  raise RuntimeError('W294_person_and_distinct_id_deleted_columns_wrong_'+both)
 distinct=http_sql(http_port,f"SELECT count() FROM system.columns WHERE database='{DB}' AND table='person' AND name='distinct_ids' FORMAT TSVRaw")
 if distinct!='0':raise RuntimeError('W294_distinct_ids_should_be_removed_'+distinct)
 REPORT['W294_0012_to_0014_schema_qualified']=True

 expected=[
  'events_dead_letter_queue\tReplicatedReplacingMergeTree',
  'events_dead_letter_queue_mv\tMaterializedView',
  'groups\tReplicatedReplacingMergeTree',
  'groups_mv\tMaterializedView',
  'kafka_events_dead_letter_queue\tKafka',
  'kafka_groups\tKafka',
 ]
 rows=http_sql(http_port,f"SELECT name,engine FROM system.tables WHERE database='{DB}' AND name IN ('events_dead_letter_queue','events_dead_letter_queue_mv','groups','groups_mv','kafka_events_dead_letter_queue','kafka_groups') ORDER BY name FORMAT TSVRaw")
 REPORT['W295_later_0017_0018_objects']=rows.splitlines()
 if rows.splitlines()!=expected:raise RuntimeError('W295_wrong_0017_0018_objects_'+repr(rows[:450]))
 group_names=['$group_0','$group_1','$group_2','$group_3','$group_4']
 group_select=','.join("'"+name+"'" for name in group_names)
 group_rows=http_sql(http_port,f"SELECT table,name FROM system.columns WHERE database='{DB}' AND table IN ('sharded_events','events') AND name IN ({group_select}) ORDER BY table,name FORMAT TSVRaw")
 expected_group=[f'events\t{x}' for x in group_names]+[f'sharded_events\t{x}' for x in group_names]
 REPORT['W298_0019_materialized_columns']=group_rows.splitlines()
 if REPORT['W298_0019_materialized_columns']!=expected_group:
  raise RuntimeError('original_0019_materialized_group_schema_missing_'+repr(group_rows[:450]))
 if free_space()<FLOOR:raise RuntimeError('disk_floor_after_apply')
 REPORT.update(observed)
 REPORT['original_Django_command_executed']=True
 REPORT['first_party_tracking_ddl_executed']=True
 REPORT['python_mode']='optimized'
 REPORT['original_django_cli_apply_0001_0020_live']=True
 REPORT['original_migration_history_exact']=['0001_initial','0002_events_materialized','0003_person','0004_kafka','0006_session_recording_events','0007_static_cohorts_table','0008_plugin_log_entries','0009_person_deleted_column','0010_cohortpeople','0011_cohortpeople_no_shard','0012_person_id_deleted_column','0013_persons_distinct_ids_column','0014_persons_distinct_ids_column_remove','0015_materialized_column_comments','0016_collapsing_person_distinct_id','0017_events_dead_letter_queue','0018_group_analytics_schema','0019_group_analytics_materialized_columns','0020_session_recording_events_window_id']
 REPORT['original_sharded_events_engine']=table_engine
 REPORT['full_original_migrations_executed']=False
 REPORT['source_scope']='Original full Django call_command apply upto=20 and repeat, then plan/check, owner-only supported ClickHouse25.12 Keeper; native endpoint wiring test-only; no production data'
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
 return 0 if (REPORT.get('original_django_cli_apply_0001_0020_live',False) and REPORT['owned_children_stopped'] and REPORT['owner_scratch_cleaned']) else 2

if __name__=='__main__':raise SystemExit(main())
