#!/usr/bin/env node
/**
 * Wave193: no-install source-attested original product driver + real HTTP/2 gRPC.
 * Runs with pre-existing locally pinned Node test dependencies only.
 * Does not run production joined pipeline, real Kafka or ClickHouse.
 */
import assert from 'node:assert/strict'
import { execFileSync, spawnSync } from 'node:child_process'
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..')
const deps=process.env.FLIND_WAVE193_DEPS_DIR || '/private/tmp/flind-wave186-grpc-core'
const sources=[
  'nodejs/src/ingestion/framework/batch-budget.ts',
  'nodejs/src/ingestion/framework/results.ts',
  'nodejs/src/ingestion/api/batch-metrics.ts',
  'nodejs/src/ingestion/api/feed-order-sentinel.ts',
  'nodejs/src/ingestion/api/grpc-error-sanitizer.ts',
  'nodejs/src/ingestion/api/grpc-message-converter.ts',
  'nodejs/src/ingestion/api/grpc-server.ts',
  'nodejs/src/ingestion/api/kafka-message-converter.ts',
  'nodejs/src/ingestion/api/types.ts',
  'nodejs/src/common/generated/ingestion-worker/ingestion/worker/v1/worker_pb.ts',
  'nodejs/src/common/utils/logger.ts',
  'nodejs/src/common/utils/promise-scheduler.ts',
  'nodejs/src/servers/grpc-stream-ingest-driver.ts',
]
const owner='.flind-wave193-owned'
const marker='FLIND_WAVE193_ORIGINAL_DRIVER_WIRE_V1\n'
let scratch
try{
  assert.ok(existsSync(path.join(deps,'node_modules','esbuild','package.json')),'local esbuild cache required; no downloads')
  assert.ok(existsSync(path.join(deps,'node_modules','@connectrpc','connect','package.json')),'local Connect cache required')
  assert.ok(existsSync(path.join(deps,'node_modules','@bufbuild','protobuf','package.json')),'local Protobuf cache required')
  scratch=mkdtempSync('/private/tmp/flind-wave193-wire-')
  writeFileSync(path.join(scratch,owner),marker)
  writeFileSync(path.join(scratch,'package.json'),JSON.stringify({name:'flind-wave193-synthetic',private:true,type:'module'}))
  symlinkSync(path.join(deps,'node_modules'),path.join(scratch,'node_modules'),'dir')
  for(const filename of sources){
    const data=execFileSync('git',['show','HEAD:'+filename],{cwd:root,timeout:12000,maxBuffer:4*1024*1024})
    const target=path.join(scratch,'firstparty',filename)
    mkdirSync(path.dirname(target),{recursive:true})
    writeFileSync(target,data)
    assert.deepEqual(readFileSync(target),data)
  }
  copyFileSync(
    path.join(root,'tools/flind/verify_production_grpc_driver_wire_wave193.mjs'),
    path.join(scratch,'verify.mjs')
  )
  // Only helper source is a test double: the original helper has a broad runtime
  // import graph beyond the isolated gRPC boundary, so this fixture cannot be
  // treated as full joined-ingestion pipeline qualification.
  const helperStub=`
    export function createKafkaDebugContext(message){
      return { topic:message.topic, partition:message.partition, offset:message.offset }
    }
    export function createOkContext(value,context){
      return { result:{type:0,value,sideEffects:[],warnings:[]},
               context:{lastStep:undefined,sideEffects:[],warnings:[],...context} }
    }
  `;
  const {build}=createRequire(path.join(deps,'package.json'))('esbuild')
  const firstparty=path.join(scratch,'firstparty/nodejs/src')
  await build({
    entryPoints:[path.join(scratch,'verify.mjs')],
    outfile:path.join(scratch,'dist/verify.mjs'),
    bundle:true,platform:'node',format:'esm',target:'node26',logLevel:'warning',
    packages:'external',
    plugins:[{name:'flind-wave193-first-party',setup(build){
      build.onResolve({filter:/^~\/ingestion\/framework\/helpers$/},()=>({path:'flind-wave193-test-helper',namespace:'wave193-helper'}))
      build.onLoad({filter:/.*/,namespace:'wave193-helper'},()=>({contents:helperStub,loader:'js'}))
      build.onResolve({filter:/^~\/common\/utils\/logger$/},()=>({path:'flind-wave193-test-logger',namespace:'wave193-logger'}))
      build.onLoad({filter:/.*/,namespace:'wave193-logger'},()=>({
        contents:'export const logger={info(){},warn(){},error(){}}',loader:'js'
      }))
      build.onResolve({filter:/^~\//},args=>{
        const base=path.join(firstparty,args.path.slice(2))
        const resolved=existsSync(base+'.ts')?base+'.ts':base
        if(!resolved.startsWith(firstparty+path.sep)||!existsSync(resolved)) throw Error('unstaged original firstparty source '+args.path)
        return {path:resolved}
      })
    }}],
  })
  const run=spawnSync(process.execPath,[path.join(scratch,'dist/verify.mjs')],{
    cwd:scratch,encoding:'utf8',timeout:28000,maxBuffer:128*1024,
    env:{...process.env,NODE_NO_WARNINGS:'1'},
  })
  if(run.error||run.status!==0){
    throw Error('production-driver real gRPC wire failed: '+String(run.error||run.stderr||run.stdout).slice(0,3000))
  }
  const outputs=run.stdout.trim().split('\n').filter(Boolean)
  assert.equal(outputs.length,1,'only the expected fixture evidence accepted')
  const result=JSON.parse(outputs[0])
  for(const field of [
    'original_grpc_server_used','original_grpc_driver_used','real_http2_proto_stream_pass',
    'no_early_ack_before_side_effects','timed_out_offset_replayable',
  ])assert.equal(result[field],true,'missing evidence: '+field)
  for(const field of [
    'production_joined_pipeline_qualified','durable_clickhouse_qualified',
    'production_rust_consumer_qualified','release_qualified',
  ])assert.equal(result[field],false,'false qualification: '+field)
  assert.equal(result.accepted,1)
  assert.equal(result.unfinished,1)
  console.log(JSON.stringify({...result,git_source_staged_exactly:true,
    source_count:sources.length,offline_cached_dependencies:true,
    test_helper_only:true,owned_scratch_removed:true}))
}catch(error){
  console.error('FLIND_WAVE193_FAILED '+String(error.stack||error).slice(0,4000))
  process.exitCode=1
}finally{
  if(scratch?.startsWith('/private/tmp/flind-wave193-wire-') &&
     readFileSync(path.join(scratch,owner),'utf8')===marker){
    rmSync(scratch,{recursive:true,force:true})
  }
}
