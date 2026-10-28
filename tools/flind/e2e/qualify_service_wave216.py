#!/usr/bin/env python3
"""Execute original Node/Jest service E2E against owned Flind databases and Kafka."""
import json, os, re, shutil, socket, subprocess, sys, tempfile
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.flind import qualify_ephemeral_kafka_wave84 as kafka
from tools.flind.qualify_original_rust_kafka_wave212 import verify_runtime
from tools.flind.e2e.verify_wave216 import SERVICES, inspect, assert_owned_service, read_database_names, check_redis, check_clickhouse
from tools.flind.e2e.schema_preflight_wave216 import preflight
RUNTIME = Path.home()/'work/Flind-wave212-runtime'
NODE = Path.home()/'.nvm/versions/node/v24.15.0/bin/node'
RUNNER = ROOT/'nodejs/tests/service-e2e/run-rust-node-sandbox-e2e.mjs'
ENV = {
 'FLIND_E2E_DESTRUCTIVE_ACK':'I_OWN_THESE_DISPOSABLE_FLIND_TEST_DATABASES',
 'FLIND_E2E_POSTGRES_BASE_URL':'postgres://flind_test:flind_local_only@127.0.0.1:15439',
 'FLIND_E2E_KAFKA_BOOTSTRAP':'127.0.0.1:19093',
 'FLIND_E2E_REDIS_URL':'redis://127.0.0.1:16380',
 'FLIND_E2E_CLICKHOUSE_HOST':'127.0.0.1',
 'FLIND_E2E_CLICKHOUSE_HTTP_PORT':'18124',
 'FLIND_E2E_CLICKHOUSE_DATABASE':'flind_test_wave216abc123',
 'FLIND_E2E_CLICKHOUSE_USER':'flind_test',
 'FLIND_E2E_CLICKHOUSE_PASSWORD':'flind_local_only',
}
def ports():
 with socket.socket() as service:
  service.bind(('127.0.0.1',19093))
 with socket.socket() as controller:
  controller.bind(('127.0.0.1',0))
  ctrl=controller.getsockname()[1]
 if ctrl in (19093,9092,9093): raise ValueError('controller collision')
 return 19093,ctrl
def main():
 result={
  'phase':'wave216_original_node_service_e2e',
  'owned_databases_ready':False,
  'original_runner_dry_run_passed':False,
  'isolated_kafka_passed':False,
  'original_service_jest_passed':False,
  'release_qualified':False,
 }
 try:
  for service in SERVICES: assert_owned_service(service,inspect(service))
  read_database_names();check_redis();check_clickhouse()
  result['owned_databases_ready']=True
  schema=preflight()
  result['original_postgres_schema_ready']=schema['original_postgres_schema_ready']
  result['original_clickhouse_schema_ready']=schema['original_clickhouse_schema_ready']
  if not (schema['original_postgres_schema_ready'] and schema['original_clickhouse_schema_ready']):
   raise ValueError('Original migrations required: PG='+
     ','.join(schema['missing_postgres_tables'])+' CH='+
     ','.join(schema['missing_clickhouse_tables']))
  if not verify_runtime(RUNTIME): raise ValueError('owned Kafka distro missing or unverified')
  if not NODE.is_file() or not RUNNER.is_file(): raise ValueError('original Node runner missing')
  if shutil.disk_usage(ROOT).free < 12*1024**3: raise ValueError('low disk')
  env={'PATH':str(NODE.parent)+':'+os.getenv('PATH','/usr/bin:/bin'),
       'HOME':str(Path.home()),'JAVA_HOME':str(RUNTIME/'java'),
       'PROTOC':str(Path.home()/'work/Flind-wave211-protoc/local/usr/bin/protoc'),
       'LD_LIBRARY_PATH':str(Path.home()/'work/Flind-wave211-protoc/local/usr/lib/x86_64-linux-gnu'),**ENV}
  dry=subprocess.run([str(NODE),str(RUNNER),'--dry-run'],cwd=ROOT,env=env,
                     capture_output=True,text=True,timeout=20)
  if dry.returncode or 'configuration admitted' not in dry.stdout:
   raise ValueError('original isolated E2E admission preflight failed')
  result['original_runner_dry_run_passed']=True
  private=RUNTIME/'wave216-private'
  if private.is_symlink(): raise ValueError('unsafe private Kafka temp path')
  private.mkdir(exist_ok=True)
  def original_service(bootstrap):
   if bootstrap!='127.0.0.1:19093': return {'passed':False,'blocker':'broker identity mismatch'}
   proc=subprocess.run([str(NODE),str(RUNNER)],cwd=ROOT,env=env,
                       capture_output=True,text=True,timeout=335)
   output=(proc.stdout+'\n'+proc.stderr).replace('flind_local_only','[synthetic-credential-redacted]')
   (private/'original-service-jest.log').write_text(output[-18000:])
   passed=proc.returncode==0 and bool(re.search(r'Test Suites:\s+1 passed,\s+1 total',output))
   return {'passed':passed,'exit':proc.returncode,'diagnostic':output[-850:] if not passed else ''}
  with patch.dict(os.environ, {'JAVA_HOME': str(RUNTIME/'java')}),patch.object(kafka,'loopback_ports',ports),patch.object(kafka,'available_disk_gib',
          lambda:shutil.disk_usage(RUNTIME).free/1024**3),patch.object(tempfile,'tempdir',str(private)):
   receipt=kafka.qualify_kafka(RUNTIME/'kafka',on_broker_ready=original_service)
  native=receipt.get('native_capture_relay') or {}
  result['isolated_kafka_passed']=receipt.get('isolated_kafka_passed') is True
  result['original_service_jest_passed']=native.get('passed') is True
  result['original_service_exit']=native.get('exit')
  result['diagnostic']=native.get('diagnostic','')
  if receipt.get('blocker'): result['blocker']=receipt['blocker']
 except (Exception,) as e:
  result['blocker']=type(e).__name__+': '+str(e)[:180]
 print(json.dumps(result,indent=2,sort_keys=True))
 return 0 if result['original_service_jest_passed'] else 2
if __name__=='__main__':sys.exit(main())
