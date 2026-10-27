import { build } from 'esbuild'
import path from 'node:path'
import { existsSync } from 'node:fs'
const root=process.cwd()
const firstparty=path.join(root,'firstparty/nodejs/src')
await build({
 entryPoints:[path.join(root,'server-kafka-durable-wire.mjs')],
 outfile:path.join(root,'dist/server-kafka-durable-wire.mjs'),
 bundle:true,platform:'node',format:'esm',target:'node26',
 logLevel:'warning',packages:'external',
 plugins:[{name:'original-flind-import-alias',setup(b){
  b.onResolve({filter:/^~\//},args=>({
   path:existsSync(path.join(firstparty,args.path.slice(2))+'.ts')
    ? path.join(firstparty,args.path.slice(2))+'.ts'
    :path.join(firstparty,args.path.slice(2))
  }))
 }}],
})
console.log('FLIND_WAVE190_ORIGINAL_NODE_SERVER_BUNDLE_PASS')
