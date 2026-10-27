import { build } from 'esbuild'
import path from 'node:path'
import {existsSync} from 'node:fs'
const root=process.cwd()
const firstparty=path.join(root,'firstparty/nodejs/src')
await build({
    entryPoints:[path.join(root,'test-wire.mjs')],
    outfile:path.join(root,'dist','test-wire.mjs'),
    bundle:true,platform:'node',format:'esm',target:'node26',logLevel:'warning',
    packages:'external',
    plugins:[{
        name:'flind-firstparty-local-alias',
        setup(builder) {
            builder.onResolve({filter:/^~\//}, args => ({
                path:existsSync(path.join(firstparty,args.path.slice(2))+'.ts') ? path.join(firstparty,args.path.slice(2))+'.ts' : path.join(firstparty,args.path.slice(2)),
            }))
        },
    }],
})
console.log('FLIND_FIRST_PARTY_ESBUILD_PASS')
