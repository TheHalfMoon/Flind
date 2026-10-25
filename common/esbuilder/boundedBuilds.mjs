// Opt-in bounded build scheduling for disk- and memory-constrained local machines.
// Production defaults remain fully parallel when no override is configured.
// Dev watchers intentionally bypass this scheduler to start every watcher.
export function productionBuildConcurrency(configCount, raw = process.env.FLIND_BUILD_MAX_PARALLEL) {
    if (!Number.isSafeInteger(configCount) || configCount < 0) {
        throw new RangeError('Invalid build config count')
    }
    if (raw === undefined || raw === '') {
        return configCount
    }
    if (typeof raw !== 'string' || !/^[1-9][0-9]{0,2}$/.test(raw)) {
        throw new RangeError('FLIND_BUILD_MAX_PARALLEL must be an integer from 1 to 999')
    }
    return Math.min(Number(raw), configCount)
}

export async function runBoundedBuilds(configs, worker, concurrency) {
    if (!Array.isArray(configs) || typeof worker !== 'function' || !Number.isSafeInteger(concurrency)) {
        throw new TypeError('Invalid build scheduler input')
    }
    if (concurrency < 0 || (configs.length > 0 && concurrency === 0)) {
        throw new RangeError('Positive concurrency required when there is work')
    }
    let next = 0
    const threads = Math.min(configs.length, concurrency)
    await Promise.all(
        Array.from({ length: threads }, async () => {
            while (next < configs.length) {
                const index = next++
                await worker(configs[index], index)
            }
        })
    )
}
