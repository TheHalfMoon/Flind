import {
    Assignment,
    CODES,
    ConsumerGlobalConfig,
    LibrdKafkaError,
    Message,
    MessageHeader,
    Metadata,
    PartitionMetadata,
    KafkaConsumer as RdKafkaConsumer,
    TopicPartitionOffset,
    WatermarkOffsets,
} from 'node-rdkafka'
import { hostname } from 'os'
import { Counter, Histogram } from 'prom-client'

import { instrumentFn } from '~/common/tracing/tracing-utils'
import { sanitizeString } from '~/common/utils/db/utils'
import { isTestEnv } from '~/common/utils/env-utils'
import { parseJSON } from '~/common/utils/json-parse'
import { normalizeSessionId } from '~/common/utils/utils'
import {
    EventHeaders,
    HealthCheckResult,
    HealthCheckResultDegraded,
    HealthCheckResultError,
    HealthCheckResultOk,
    LogLevel,
} from '~/types'

import { defaultConfig } from '../../config/config'
import { logger } from '../../utils/logger'
import { captureException } from '../../utils/posthog'
import { retryIfRetriable } from '../../utils/retries'
import { promisifyCallback } from '../../utils/utils'
import { ensureTopicExists } from '../admin'
import { getKafkaConfigFromEnv, stripClassicProtocolConfig } from '../config'
import { parseBrokerStatistics, trackBrokerMetrics } from '../kafka-client-metrics'
import { drainAndDisconnectConsumer } from './consumer-loop-cleanup'
import { OffsetCommitGate } from './offset-commit-gate'
import { awaitRevocationSafety } from './revocation-safety'
import { safeKafkaErrorContext, safeKafkaLogContext } from './safe-log-context'
import {
    consumedBatchBackgroundDuration,
    consumedBatchBackpressureDuration,
    consumedBatchDuration,
    consumerBatchUtilization as gaugeBatchUtilization,
    consumerBatchSize as histogramKafkaBatchSize,
    consumerBatchSizeKb as histogramKafkaBatchSizeKb,
    kafkaConsumerAssignment,
} from './metrics'

const DEFAULT_BATCH_TIMEOUT_MS = 500
const SLOW_BATCH_PROCESSING_LOG_THRESHOLD_MS = 10000
const MAX_HEALTH_HEARTBEAT_INTERVAL_MS = 60_000
const STATISTICS_INTERVAL_MS = 5000 // Emit internal metrics every 5 seconds

const kafkaHeaderStatusCounter = new Counter({
    name: 'kafka_header_status_total',
    help: 'Count of events by header name and presence status',
    labelNames: ['header', 'status'],
})

// v1-only metrics — v2 doesn't surface these. Kept here until v1 is deleted.
const histogramKafkaConsumeInterval = new Histogram({
    name: 'kafka_consume_interval_ms',
    help: 'Time elapsed between Kafka consume calls',
    labelNames: ['topic', 'groupId'],
    buckets: [0, 20, 100, 200, 500, 1000, 2500, 5000, 10000, 20000, 30000, 60000, Infinity],
})

export const findOffsetsToCommit = (messages: TopicPartitionOffset[]): TopicPartitionOffset[] => {
    // We only need to commit the highest offset for a batch of messages
    const messagesByTopicPartition = messages.reduce(
        (acc, message) => {
            if (!acc[message.topic]) {
                acc[message.topic] = {}
            }

            if (!acc[message.topic][message.partition]) {
                acc[message.topic][message.partition] = []
            }

            acc[message.topic][message.partition].push(message)

            return acc
        },
        {} as { [topic: string]: { [partition: number]: TopicPartitionOffset[] } }
    )

    // Then we find the highest offset for each topic partition
    const highestOffsets = Object.entries(messagesByTopicPartition).flatMap(([topic, partitions]) => {
        return Object.entries(partitions).map(([partition, messages]) => {
            const highestOffset = Math.max(...messages.map((message) => message.offset))

            return {
                topic,
                partition: parseInt(partition),
                // When committing to Kafka you commit the offset of the next message you want to consume
                offset: highestOffset + 1,
            }
        })
    })

    return highestOffsets
}

export type KafkaConsumerConfig = {
    groupId: string
    topic: string
    batchTimeoutMs?: number
    callEachBatchWhenEmpty?: boolean
    autoOffsetStore?: boolean
    autoCommit?: boolean
    enablePartitionEof?: boolean
    /**
     * Messages pulled per poll, overriding CONSUMER_BATCH_SIZE for this consumer only.
     *
     * For lanes whose per-message work is slow or unbounded, batch size is what keeps a batch inside
     * max.poll.interval.ms, so it belongs next to the code that depends on it rather than in a
     * deployment value that can drift away from the assumption without anything noticing.
     */
    fetchBatchSize?: number
}

export type RdKafkaConsumerConfig = Omit<
    ConsumerGlobalConfig,
    'group.id' | 'enable.auto.offset.store' | 'enable.auto.commit'
>

interface RebalanceCoordination {
    isRebalancing: boolean
    rebalanceTimeoutMs: number
    rebalanceStartTime: number
}

export class KafkaConsumer {
    private isStopping = false
    private lastHeartbeatTime = 0
    private rdKafkaConsumer: RdKafkaConsumer
    private consumerConfig: ConsumerGlobalConfig
    private fetchBatchSize: number
    private maxHealthHeartbeatIntervalMs: number
    private maxBackgroundTasks: number
    private consumerLoop: Promise<void> | undefined
    private backgroundTask: { promise: Promise<void>; createdAt: number }[]
    private readonly offsetCommitGate = new OffsetCommitGate()
    private podName: string
    private lastBackgroundTaskCompletionTime: number
    private consumerId: string
    // New health monitoring state
    private consumerLoopStallThresholdMs: number
    private lastConsumerLoopTime = 0
    private consumerState: string | undefined
    private lastStatsEmitTime = 0
    private rebalanceCoordination: RebalanceCoordination = {
        isRebalancing: false,
        rebalanceTimeoutMs: defaultConfig.CONSUMER_REBALANCE_TIMEOUT_MS,
        rebalanceStartTime: 0,
    }
    private consumerLogStatsLevel: LogLevel
    private onPartitionsRevoked?: (assignments: Assignment[]) => Promise<void>

    constructor(
        private config: KafkaConsumerConfig,
        rdKafkaConfig: RdKafkaConsumerConfig = {}
    ) {
        this.backgroundTask = []
        this.podName = process.env.HOSTNAME || hostname()
        this.lastBackgroundTaskCompletionTime = Date.now()
        // Generate unique consumer ID: pod + group + timestamp + random number (need timestamp/random number because multiple consumers per pod)
        this.consumerId = `${this.podName}-${this.config.groupId}-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`

        this.config.autoCommit ??= true
        this.config.autoOffsetStore ??= true
        this.config.callEachBatchWhenEmpty ??= false
        this.maxBackgroundTasks = defaultConfig.CONSUMER_MAX_BACKGROUND_TASKS
        this.fetchBatchSize = config.fetchBatchSize ?? defaultConfig.CONSUMER_BATCH_SIZE
        this.maxHealthHeartbeatIntervalMs =
            defaultConfig.CONSUMER_MAX_HEARTBEAT_INTERVAL_MS || MAX_HEALTH_HEARTBEAT_INTERVAL_MS
        this.consumerLoopStallThresholdMs = defaultConfig.CONSUMER_LOOP_STALL_THRESHOLD_MS
        this.consumerLogStatsLevel = defaultConfig.CONSUMER_LOG_STATS_LEVEL

        this.consumerConfig = stripClassicProtocolConfig({
            'client.id': hostname(),
            'security.protocol': 'plaintext',
            'metadata.broker.list': 'kafka:9092', // Overridden with KAFKA_CONSUMER_METADATA_BROKER_LIST
            log_level: 4, // WARN as the default
            'group.id': this.config.groupId,
            'session.timeout.ms': 30_000,
            'max.poll.interval.ms': 300_000,
            'max.partition.fetch.bytes': 1_048_576,
            'fetch.error.backoff.ms': 100,
            'fetch.message.max.bytes': 10_485_760,
            'fetch.wait.max.ms': 50,
            'queued.min.messages': 100000,
            'queued.max.messages.kbytes': 102400, // 1048576 is the default, we go smaller to reduce mem usage.
            'client.rack': defaultConfig.KAFKA_CLIENT_RACK, // Helps with cross-AZ traffic awareness and is not unique to the consumer
            'metadata.max.age.ms': 30000, // Refresh metadata every 30s - Relevant for leader loss (MSK Security Patches)
            'socket.timeout.ms': 30000,
            'enable.partition.eof': this.config.enablePartitionEof ?? true,
            // Only enable statistics when using loop-based health check
            ...(defaultConfig.CONSUMER_LOOP_BASED_HEALTH_CHECK
                ? { 'statistics.interval.ms': STATISTICS_INTERVAL_MS }
                : {}),
            // Custom settings and overrides - this is where most configuration overrides should be done
            // e.g. KAFKA_CONSUMER_ENABLE_PARTITION_EOF=false to override the default above
            ...getKafkaConfigFromEnv('CONSUMER'),
            // Finally any specifically given consumer config overrides
            ...rdKafkaConfig,
            // Below is config that we explicitly DO NOT want to be overrideable by env vars - i.e. things that would require code changes to change
            'partition.assignment.strategy': isTestEnv() ? 'roundrobin' : 'cooperative-sticky', // Roundrobin is used for testing to avoid flakiness caused by running librdkafka v2.2.0
            'enable.auto.offset.store': false, // NOTE: This is always false - we handle it using a custom function
            'enable.auto.commit': this.config.autoCommit,
            rebalance_cb: this.rebalanceCallback.bind(this),
            offset_commit_cb: true,
        })

        this.rdKafkaConsumer = this.createConsumer()
    }

    public getConfig(): ConsumerGlobalConfig {
        return {
            ...this.consumerConfig,
        }
    }

    public heartbeat(): void {
        // Can be called externally to update the heartbeat time and keep the consumer alive
        // This is maintained for backward compatibility with the legacy health check mechanism
        this.lastHeartbeatTime = Date.now()
    }

    /**
     * Say that this consumer waits on purpose, and does not stall.
     *
     * Separate from `heartbeat()` because it relaxes the loop stall detector, and most callers must
     * not do that. Two lanes drive `heartbeat()` from a `setInterval`, which keeps firing while a
     * batch is wedged on a promise that never settles, so moving the loop clock there would leave
     * such a pod reporting healthy forever.
     *
     * Call this only from a handler that sleeps by design, and only from its own await chain.
     */
    public reportDeliberateWait(): void {
        this.lastHeartbeatTime = Date.now()
        this.lastConsumerLoopTime = Date.now()
    }

    public isHealthy(): HealthCheckResult {
        // Use legacy heartbeat-based health check if feature flag is disabled
        if (!defaultConfig.CONSUMER_LOOP_BASED_HEALTH_CHECK) {
            // this is called as a readiness and a liveness probe
            const isWithinInterval = Date.now() - this.lastHeartbeatTime < this.maxHealthHeartbeatIntervalMs
            const isConnected = this.rdKafkaConsumer.isConnected()

            if (isConnected && isWithinInterval) {
                return new HealthCheckResultOk()
            } else {
                return new HealthCheckResultError('Consumer unhealthy', {
                    isConnected,
                    isWithinInterval,
                    lastHeartbeatTime: this.lastHeartbeatTime,
                    maxHealthHeartbeatIntervalMs: this.maxHealthHeartbeatIntervalMs,
                })
            }
        }

        // New loop-based health check implementation
        const details: Record<string, any> = {
            topic: this.config.topic,
            groupId: this.config.groupId,
            healthCheckMode: 'loop-based',
        }

        // 1. Basic connectivity check
        if (!this.rdKafkaConsumer.isConnected()) {
            return new HealthCheckResultError('Consumer not connected to Kafka broker', details)
        }

        // 2. Consumer loop liveness check (ensure loop is not stalled)
        const timeSinceLastLoop = Date.now() - this.lastConsumerLoopTime
        if (this.lastConsumerLoopTime > 0 && timeSinceLastLoop > this.consumerLoopStallThresholdMs) {
            return new HealthCheckResultError(
                `Consumer loop appears stalled (no activity for ${Math.round(timeSinceLastLoop / 1000)}s)`,
                {
                    ...details,
                    lastConsumerLoopTime: this.lastConsumerLoopTime,
                    timeSinceLastLoop,
                    threshold: this.consumerLoopStallThresholdMs,
                }
            )
        }

        // Build status message with warnings
        const warnings: string[] = []

        // 3. Check librdkafka internal state if available
        if (this.consumerState && this.consumerState !== 'up') {
            warnings.push(`Consumer state: ${this.consumerState}`)
            details.consumerState = this.consumerState
        }

        // 4. Check if statistics are being emitted (indicates librdkafka is responsive)
        if (this.lastStatsEmitTime > 0) {
            const timeSinceLastStats = Date.now() - this.lastStatsEmitTime
            // Allow for 3x the statistics interval as buffer
            if (timeSinceLastStats > STATISTICS_INTERVAL_MS * 3) {
                warnings.push(`Statistics not emitted for ${Math.round(timeSinceLastStats / 1000)}s`)
                details.lastStatsEmitTime = this.lastStatsEmitTime
                details.timeSinceLastStats = timeSinceLastStats
            }
        }

        // 5. Rebalancing is normal operation, note it but don't fail
        if (this.rebalanceCoordination.isRebalancing) {
            const duration = Date.now() - this.rebalanceCoordination.rebalanceStartTime
            warnings.push(`Rebalancing in progress (${Math.round(duration / 1000)}s)`)
            details.rebalancing = true
            details.rebalanceDuration = duration
        }

        // Add assignments info (but handle errors gracefully)
        try {
            const assignments = this.assignments()
            if (assignments.length > 0) {
                details.assignments = assignments.map((a) => ({ topic: a.topic, partition: a.partition }))
            }
        } catch (error) {
            // Health diagnostics can be externally visible; never include raw native error text.
            details.assignmentError = 'Kafka partition assignment unavailable'
            Object.assign(details, safeKafkaErrorContext(error))
        }

        // Return degraded if there are warnings, otherwise healthy
        if (warnings.length > 0) {
            return new HealthCheckResultDegraded(`Healthy with warnings: ${warnings.join(', ')}`, details)
        }

        return new HealthCheckResultOk()
    }

    public isShuttingDown(): boolean {
        return this.isStopping
    }

    public isRebalancing(): boolean {
        return this.rebalanceCoordination.isRebalancing
    }

    public assignments(): Assignment[] {
        return this.rdKafkaConsumer.isConnected() ? this.rdKafkaConsumer.assignments() : []
    }

    public offsetsStore(topicPartitionOffsets: TopicPartitionOffset[]): void {
        return this.rdKafkaConsumer.offsetsStore(topicPartitionOffsets)
    }

    public on: RdKafkaConsumer['on'] = (...args) => {
        // Delegate to the internal consumer
        return this.rdKafkaConsumer.on(...args)
    }

    public async queryWatermarkOffsets(topic: string, partition: number, timeout = 10000): Promise<[number, number]> {
        if (!this.rdKafkaConsumer.isConnected()) {
            throw new Error('Not connected')
        }

        const offsets = await promisifyCallback<WatermarkOffsets>((cb) =>
            this.rdKafkaConsumer.queryWatermarkOffsets(topic, partition, timeout, cb)
        ).catch((err) => {
            captureException(new Error('Kafka watermark lookup failed'))
            logger.error('🔥', 'Failed to query kafka watermark offsets', safeKafkaErrorContext(err))
            throw err
        })

        return [offsets.lowOffset, offsets.highOffset]
    }

    public async committedOffsets(timeout = 10000): Promise<TopicPartitionOffset[]> {
        if (!this.rdKafkaConsumer.isConnected()) {
            return []
        }

        return await promisifyCallback<TopicPartitionOffset[]>((cb) => this.rdKafkaConsumer.committed(timeout, cb))
    }

    public async getPartitionsForTopic(topic: string): Promise<PartitionMetadata[]> {
        if (!this.rdKafkaConsumer.isConnected()) {
            throw new Error('Not connected')
        }

        const meta = await promisifyCallback<Metadata>((cb) => this.rdKafkaConsumer.getMetadata({ topic }, cb)).catch(
            (err) => {
                captureException(new Error('Kafka partition metadata lookup failed'))
                logger.error('🔥', 'Failed to get partition metadata', safeKafkaErrorContext(err))
                throw err
            }
        )

        return meta.topics.find((x) => x.name === topic)?.partitions ?? []
    }

    public rebalanceCallback(err: LibrdKafkaError, assignments: Assignment[]): void {
        logger.info('🔁', 'kafka_consumer_rebalancing', { ...safeKafkaErrorContext(err), assignmentCount: assignments.length })

        if (err.code === CODES.ERRORS.ERR__ASSIGN_PARTITIONS) {
            // Mark rebalancing as complete when partitions are assigned
            this.resetRebalanceCoordination()
            assignments.forEach((tp) => {
                kafkaConsumerAssignment.set(
                    {
                        topic_name: tp.topic,
                        partition_id: tp.partition.toString(),
                        pod: this.podName,
                        group_id: this.config.groupId,
                    },
                    1
                )
            })
            if (this.rdKafkaConsumer.rebalanceProtocol() === 'COOPERATIVE') {
                this.rdKafkaConsumer.incrementalAssign(assignments)
            } else {
                this.rdKafkaConsumer.assign(assignments)
            }
        } else if (err.code === CODES.ERRORS.ERR__REVOKE_PARTITIONS) {
            // Mark rebalancing as starting when partitions are revoked
            this.rebalanceCoordination.isRebalancing = true
            this.rebalanceCoordination.rebalanceStartTime = Date.now()
            logger.info('🔁', 'partition_revocation_starting', {
                backgroundTaskCount: this.backgroundTask.length,
                revokedPartitions: assignments.map((tp) => ({
                    topic: tp.topic,
                    partition: tp.partition,
                })),
            })

            // Snapshots are local to this revoke. Even if one background batch
            // fails, wait for all remaining batches, and then wait for queued
            // ordered offset stores before relinquishing the partitions.
            // An empty in-flight list can still have a pending offset store.
            const pendingTasks = this.backgroundTask.map((task) => task.promise)
            void awaitRevocationSafety(pendingTasks, this.offsetCommitGate)
                .then(({ failedTasks, offsetGateFailed }) => {
                    if (failedTasks > 0 || offsetGateFailed) {
                        logger.error('🔁', 'background_task_error_during_revocation', {
                            failedTasks,
                            offsetGateFailed,
                        })
                    } else {
                        logger.info('🔁', 'background_tasks_completed_before_partition_revocation')
                    }
                })
                .catch((error) => {
                    // Still revoke after a local drain error; Kafka manages
                    // partition ownership, while the consumer failure fence
                    // prohibits subsequent offsets from being acknowledged.
                    logger.error('🔁', 'offset_gate_drain_failed_during_revocation', safeKafkaErrorContext(error))
                })
                .then(() => this.completeRevocation(assignments))
                .catch((error) => {
                    captureException(new Error('Kafka partition revocation failed'))
                    logger.error('🔁', 'partition_revocation_failed', safeKafkaErrorContext(error))
                    this.resetRebalanceCoordination()
                })
        } else {
            // Ignore exceptions if we are not connected
            if (this.rdKafkaConsumer.isConnected()) {
                logger.error('🔥', 'kafka_consumer_rebalancing_error', safeKafkaErrorContext(err))
                captureException(new Error('Kafka consumer rebalancing failed'))
            } else {
                logger.warn('🔥', 'kafka_consumer_rebalancing_error_while_not_connected', safeKafkaErrorContext(err))
            }
        }
    }

    private completeRevocation(assignments: Assignment[]): void {
        try {
            if (this.rdKafkaConsumer.rebalanceProtocol() === 'COOPERATIVE') {
                this.rdKafkaConsumer.incrementalUnassign(assignments)
            } else {
                this.rdKafkaConsumer.unassign()
            }
            this.updateMetricsAfterRevocation(assignments)
        } finally {
            this.resetRebalanceCoordination()
        }
        Promise.resolve()
            .then(() => this.onPartitionsRevoked?.(assignments))
            .catch((error) => {
                logger.error('🔁', 'partition_revoked_handler_failed', safeKafkaErrorContext(error))
            })
    }

    private updateMetricsAfterRevocation(assignments: Assignment[]): void {
        assignments.forEach((tp) => {
            kafkaConsumerAssignment.set(
                {
                    topic_name: tp.topic,
                    partition_id: tp.partition.toString(),
                    pod: this.podName,
                    group_id: this.config.groupId,
                },
                0
            )
        })
    }

    private createConsumer(): RdKafkaConsumer {
        // auto.offset.reset is a topic-level property, and librdkafka ignores the global-config
        // form on our version (see node-rdkafka #984), so the resolved value, including any
        // caller override, must be mirrored into the explicit topic config. v2 does the same.
        const autoOffsetReset =
            (this.consumerConfig['auto.offset.reset' as keyof ConsumerGlobalConfig] as
                | 'earliest'
                | 'latest'
                | undefined) ?? 'earliest'
        const consumer = new RdKafkaConsumer(this.consumerConfig, {
            'auto.offset.reset': autoOffsetReset,
        })

        consumer.on('event.log', () => {
            // Native log text may include SASL/TLS material.
            logger.info('📝', 'librdkafka_log_event')
        })

        consumer.on('event.error', (error: LibrdKafkaError) => {
            logger.error('📝', 'librdkafka_error', safeKafkaErrorContext(error))
        })

        consumer.on('event.stats', (stats: any) => {
            // Parse the statistics JSON
            try {
                const parsedStats = parseJSON(stats.message)

                // Update internal health monitoring state
                this.lastStatsEmitTime = Date.now()
                // cgrp field only appears when consumer is part of a group
                this.consumerState = parsedStats.cgrp?.state || 'no-group'

                const brokerStats = parseBrokerStatistics(parsedStats)

                trackBrokerMetrics(brokerStats, this.config.groupId, this.consumerId)

                // Log key metrics for observability - only include cgrp fields if present
                const logData: any = {
                    rx_msgs: parsedStats.rxmsgs, // Total messages received
                    rx_bytes: parsedStats.rx_bytes || parsedStats.rxbytes, // Total bytes received
                    topics: Object.keys(parsedStats.topics || {}),
                    broker_count: brokerStats.size,
                    brokers: Array.from(brokerStats.entries()).map(([name, stats]) => ({
                        ...stats,
                        name,
                    })),
                }

                // Only add consumer group fields if cgrp exists
                if (parsedStats.cgrp) {
                    logData.consumer_group_state = parsedStats.cgrp.state
                    logData.rebalance_state = parsedStats.cgrp.join_state
                    logData.rebalance_age = parsedStats.cgrp.rebalance_age
                    logData.rebalance_cnt = parsedStats.cgrp.rebalance_cnt
                    logData.assignment_size = parsedStats.cgrp.assignment_size
                }

                logger[this.consumerLogStatsLevel]('📊', 'Kafka consumer statistics', logData)
            } catch (error) {
                logger.error('📊', 'Failed to parse consumer statistics', safeKafkaErrorContext(error))
            }
        })

        consumer.on('subscribed', (topics) => {
            logger.info('📝', 'librdkafka consumer subscribed', { topics, ...safeKafkaLogContext(this.config) })
        })

        consumer.on('connection.failure', (error: LibrdKafkaError) => {
            // Native metrics and error objects may include transport details.
            // Log the documented error code, not their arbitrary fields.
            logger.error('📝', 'librdkafka connection failure', {
                ...safeKafkaErrorContext(error),
                ...safeKafkaLogContext(this.config),
            })
        })

        consumer.on('offset.commit', (error: LibrdKafkaError, topicPartitionOffsets: TopicPartitionOffset[]) => {
            if (error) {
                logger.warn('📝', 'librdkafka_offet_commit_error', { ...safeKafkaErrorContext(error), partitionCount: topicPartitionOffsets.length })
            } else {
                logger.debug('📝', 'librdkafka_offset_commit', { topicPartitionOffsets })
            }
        })

        return consumer
    }

    private storeOffsetsForMessages = (topicPartitionOffsetsToCommit: TopicPartitionOffset[]): void => {
        if (topicPartitionOffsetsToCommit.length > 0) {
            logger.debug('📝', 'Storing offsets', { topicPartitionOffsetsToCommit })
            try {
                this.rdKafkaConsumer.offsetsStore(topicPartitionOffsetsToCommit)
            } catch (e) {
                // NOTE: We don't throw here - this can happen if we were re-assigned partitions
                // and the offsets are no longer valid whilst processing a batch
                logger.error('📝', 'Failed to store offsets', {
                    ...safeKafkaErrorContext(e),
                    affectedPartitionCount: topicPartitionOffsetsToCommit.length,
                })
                captureException(new Error('Kafka offset store failed'))
                // Kafka offset storage is part of the delivery guarantee.
                // Swallowing the error makes OffsetCommitGate treat this batch
                // as acknowledged and allows a newer batch to advance past it.
                // Fail closed even on a rebalance-related error: replay may
                // duplicate events, but it must never skip unacknowledged work.
                throw e
            }
        }
    }

    public async connect(
        eachBatch: (messages: Message[]) => Promise<{ backgroundTask?: Promise<any> } | void>,
        onPartitionsRevoked?: (assignments: Assignment[]) => Promise<void>
    ): Promise<void> {
        const { topic, groupId, callEachBatchWhenEmpty = false } = this.config
        this.onPartitionsRevoked = onPartitionsRevoked

        try {
            await promisifyCallback<Metadata>((cb) => this.rdKafkaConsumer.connect({}, cb))
            logger.info('📝', 'librdkafka consumer connected')
        } catch (error) {
            logger.error('⚠️', 'connect_error', safeKafkaErrorContext(error))
            throw error
        }

        this.heartbeat() // Setup the heartbeat so we are healthy since connection is established

        // Initialize health monitoring state for new loop-based check
        this.lastConsumerLoopTime = Date.now()

        if (defaultConfig.CONSUMER_AUTO_CREATE_TOPICS) {
            // For hobby deploys we want to auto-create, but on cloud we don't
            await ensureTopicExists(this.consumerConfig, this.config.topic)
        }

        // The consumer has an internal pre-fetching queue that sequentially pools
        // each partition, with the consumerMaxWaitMs timeout. We want to read big
        // batches from this queue, but guarantee we are still running (with smaller
        // batches) if the queue is not full enough. batchingTimeoutMs is that
        // timeout, to return messages even if fetchBatchSize is not reached.
        this.rdKafkaConsumer.setDefaultConsumeTimeout(this.config.batchTimeoutMs || DEFAULT_BATCH_TIMEOUT_MS)
        this.rdKafkaConsumer.subscribe([this.config.topic])

        const startConsuming = async (): Promise<void> => {
            let lastConsumeTime = 0
            let loopFailure: unknown
            try {
                while (!this.isStopping) {
                    if (this.offsetCommitGate.failed) {
                        throw new Error('Kafka background task failed; refusing to acknowledge subsequent offsets')
                    }
                    // Track that the consumer loop is alive
                    this.lastConsumerLoopTime = Date.now()
                    logger.debug('🔁', 'main_loop_consuming')

                    // If we're rebalancing, skip consuming to avoid processing messages
                    // during rebalancing when background tasks might be running
                    if (this.rebalanceCoordination.isRebalancing) {
                        if (
                            Date.now() - this.rebalanceCoordination.rebalanceStartTime >
                            this.rebalanceCoordination.rebalanceTimeoutMs
                        ) {
                            logger.error('🔁', 'rebalancing_timeout_forcing_recovery', {
                                rebalanceTimeoutMs: this.rebalanceCoordination.rebalanceTimeoutMs,
                                rebalanceStartTime: this.rebalanceCoordination.rebalanceStartTime,
                            })
                            this.rebalanceCoordination.isRebalancing = false
                        }
                        logger.info('🔁', 'main_loop_paused_for_rebalancing')
                        await new Promise((resolve) => setTimeout(resolve, 10)) // Small delay to avoid busy waiting
                        continue
                    }

                    const consumeStartTime = performance.now()
                    if (lastConsumeTime > 0) {
                        const intervalMs = consumeStartTime - lastConsumeTime
                        histogramKafkaConsumeInterval.labels({ topic, groupId }).observe(intervalMs)
                    }
                    lastConsumeTime = consumeStartTime
                    // TRICKY: We wrap this in a retry check. It seems that despite being connected and ready, the client can still have an undeterministic
                    // error when consuming, hence the retryIfRetriable.
                    const messages = await retryIfRetriable(() =>
                        promisifyCallback<Message[]>((cb) => this.rdKafkaConsumer.consume(this.fetchBatchSize, cb))
                    )

                    if (this.offsetCommitGate.failed) {
                        throw new Error('Kafka background task failed; refusing to acknowledge subsequent offsets')
                    }

                    // After successfully pulling a batch, update heartbeat for backward compatibility
                    this.heartbeat()

                    gaugeBatchUtilization.labels({ groupId }).set(messages.length / this.fetchBatchSize)

                    logger.debug('🔁', 'main_loop_consumed', { messagesLength: messages.length })
                    histogramKafkaBatchSize.observe(messages.length)
                    histogramKafkaBatchSizeKb.observe(
                        messages.reduce((acc, m) => (m.value?.length ?? 0) + acc, 0) / 1024
                    )

                    if (!messages.length && !callEachBatchWhenEmpty) {
                        logger.debug('🔁', 'main_loop_empty_batch', { cause: 'empty' })
                        continue
                    }

                    const startProcessingTimeMs = new Date().valueOf()
                    const result = await eachBatch(messages)

                    const processingTimeMs = new Date().valueOf() - startProcessingTimeMs
                    consumedBatchDuration.labels({ topic, groupId }).observe(processingTimeMs)

                    const logSummary = `Processed ${messages.length} events in ${
                        Math.round(processingTimeMs / 10) / 100
                    }s`
                    if (processingTimeMs > SLOW_BATCH_PROCESSING_LOG_THRESHOLD_MS) {
                        logger.warn('🕒', `Slow batch: ${logSummary}, groupId: ${groupId}`)
                    }

                    // TRICKY: The commit logic needs to be aware of background work. If we were to just store offsets here,
                    // it would be hard to mix background work with non-background work.
                    // So we just create pretend work to simplify the rest of the logic
                    const rawBackgroundTask = result?.backgroundTask
                    const backgroundTask = rawBackgroundTask
                        ? instrumentFn(
                              {
                                  key: 'consumer_background_task',
                                  timeoutMs: defaultConfig.CONSUMER_BACKGROUND_TASK_TIMEOUT_MS,
                                  sendException: false,
                              },
                              () => rawBackgroundTask
                          )
                        : Promise.resolve()
                    const stopBackgroundTaskTimer = rawBackgroundTask
                        ? consumedBatchBackgroundDuration.startTimer({
                              topic: this.config.topic,
                              groupId: this.config.groupId,
                          })
                        : undefined
                    const taskCreatedAt = Date.now()
                    // Pull out the offsets to commit from the messages so we can release the messages reference
                    const topicPartitionOffsetsToCommit = findOffsetsToCommit(messages)

                    // Offset stores are ordered by batch arrival, not task
                    // completion. A rejected background task poisons future
                    // acknowledgements so no later successful batch can skip
                    // failed events on a restart.
                    this.offsetCommitGate.observe(backgroundTask, () => {
                        if (this.config.autoCommit && this.config.autoOffsetStore) {
                            this.storeOffsetsForMessages(topicPartitionOffsetsToCommit)
                        }
                    })

                    // Bookkeeping runs for either outcome, with an explicit
                    // rejection handler: .finally() would preserve rejection
                    // and create an unhandled observer promise.
                    const completeBackgroundTask = (): void => {
                        this.lastBackgroundTaskCompletionTime = Date.now()
                        stopBackgroundTaskTimer?.()
                        const index = this.backgroundTask.findIndex((t) => t.promise === backgroundTask)
                        if (index < 0) {
                            captureException(new Error('Background task not found in array during cleanup'))
                        } else {
                            this.backgroundTask.splice(index, 1)
                        }
                    }
                    void backgroundTask.then(completeBackgroundTask, completeBackgroundTask)

                    // At first we just add the background work to the queue with metadata
                    this.backgroundTask.push({
                        promise: backgroundTask,
                        createdAt: taskCreatedAt,
                    })

                    // If we have too much "backpressure" we need to await one of the background tasks. We await the oldest one on purpose
                    if (this.backgroundTask.length >= this.maxBackgroundTasks) {
                        const stopTimer = consumedBatchBackpressureDuration.startTimer({
                            topic: this.config.topic,
                            groupId: this.config.groupId,
                        })
                        // If we have more than the max, we need to await one
                        await instrumentFn(
                            { key: 'consumer_backpressure_wait', timeoutMs: 30_000, sendException: false },
                            () => this.backgroundTask[0].promise
                        )
                        stopTimer()
                    }
                }

                // Event work, ordered offsets and broker teardown are drained in
                // one place, including when earlier stages fail.
            } catch (error) {
                loopFailure = error
                logger.error('🔁', 'main_loop_error', safeKafkaErrorContext(error))
            } finally {
                logger.info('🔁', 'main_loop_stopping')
                // Promise.all would abort cleanup at the first rejection and
                // could disconnect while later batches still own in-flight work.
                // Preserve the original loop error along with teardown failures.
                await drainAndDisconnectConsumer(
                    this.backgroundTask.map((task) => task.promise),
                    this.offsetCommitGate,
                    () => this.disconnectConsumer(),
                    loopFailure
                )
                logger.info('🔁', 'Disconnected node-rdkafka consumer')
            }
        }

        this.consumerLoop = startConsuming().catch((error) => {
            logger.error('🔁', 'consumer_loop_error', {
                ...safeKafkaErrorContext(error),
                ...safeKafkaLogContext(this.config),
            })
            // We re-throw the error as that way it will be caught in server.ts and trigger a full shutdown
            throw error
        })
    }

    public async disconnect(): Promise<void> {
        if (this.isStopping) {
            return
        }
        // Mark as stopping before waiting, so the consumer loop stops polling.
        this.isStopping = true

        logger.info('🔁', 'waiting_for_background_tasks_before_disconnect', {
            backgroundTaskCount: this.backgroundTask.length,
        })

        // Promise.all would reject on the first failed task and skip broker
        // teardown. Wait for all tasks and the Wave 88 offset gate, preserving
        // failures until after the consumer has been disconnected.
        const settled = await Promise.allSettled(this.backgroundTask.map((t) => t.promise))
        const failures: unknown[] = settled
            .filter((result) => result.status === 'rejected')
            .map((result) => (result as PromiseRejectedResult).reason)

        try {
            await this.offsetCommitGate.drain()
        } catch (error) {
            failures.push(error)
        }
        if (this.offsetCommitGate.failed && failures.length === 0) {
            failures.push(new Error('Kafka offset commit gate failed during shutdown'))
        }

        logger.info('🔁', 'background_tasks_completed_proceeding_with_disconnect')

        // Keep the existing consumer-loop error diagnostics, then always attempt
        // physical broker disconnect even after failed background processing.
        if (this.consumerLoop) {
            await this.consumerLoop.catch((error) => {
                logger.error('🔁', 'failed to stop consumer loop safely. Continuing shutdown', {
                    ...safeKafkaErrorContext(error),
                    ...safeKafkaLogContext(this.config),
                })
            })
        }

        try {
            await this.disconnectConsumer()
        } catch (error) {
            failures.push(error)
        }
        if (failures.length === 1) {
            throw failures[0]
        }
        if (failures.length > 1) {
            throw new AggregateError(failures, 'Kafka consumer shutdown failed')
        }
    }

    private async disconnectConsumer(): Promise<void> {
        if (this.rdKafkaConsumer.isConnected()) {
            logger.info('📝', 'Disconnecting consumer...')
            await new Promise<void>((res, rej) => this.rdKafkaConsumer.disconnect((e) => (e ? rej(e) : res())))
            logger.info('📝', 'Disconnected consumer!')
        }
    }

    private resetRebalanceCoordination(): void {
        this.rebalanceCoordination.isRebalancing = false
        this.rebalanceCoordination.rebalanceStartTime = 0
    }
}

export const parseKafkaHeaders = (headers?: MessageHeader[]): Record<string, string> => {
    // Kafka headers come from librdkafka as an array of objects with keys value pairs per header.
    // It's a confusing format so we simplify it to a record.

    const result: Record<string, string> = {}

    headers?.forEach((header) => {
        Object.keys(header).forEach((key) => {
            result[key] = header[key].toString()
        })
    })

    return result
}

export const parseEventHeaders = (headers?: MessageHeader[]): EventHeaders => {
    // Kafka headers come from librdkafka as an array of objects with keys value pairs per header.
    // We extract the specific headers we care about into a structured format.

    const result: EventHeaders = {
        force_disable_person_processing: false,
        historical_migration: false,
        skip_heatmap_processing: false,
    }

    headers?.forEach((header) => {
        Object.keys(header).forEach((key) => {
            const value = header[key].toString()
            if (key === 'token') {
                result.token = sanitizeString(value)
            } else if (key === 'distinct_id') {
                result.distinct_id = sanitizeString(value)
            } else if (key === 'session_id') {
                result.session_id = normalizeSessionId(sanitizeString(value))
            } else if (key === 'timestamp') {
                result.timestamp = value
            } else if (key === 'event') {
                result.event = value
            } else if (key === 'uuid') {
                result.uuid = value
            } else if (key === 'force_disable_person_processing') {
                result.force_disable_person_processing = value === 'true'
            } else if (key === 'now') {
                const parsed = new Date(value)
                if (!isNaN(parsed.getTime())) {
                    result.now = parsed
                }
            } else if (key === 'historical_migration') {
                result.historical_migration = value === 'true'
            } else if (key === 'skip_heatmap_processing') {
                result.skip_heatmap_processing = value === 'true'
            } else if (key === 'redirect-original-key') {
                result.redirect_original_key = value
            }
        })
    })

    // Track comprehensive header status metrics
    const trackedHeaders = [
        'token',
        'distinct_id',
        'session_id',
        'timestamp',
        'event',
        'uuid',
        'now',
        'force_disable_person_processing',
        'historical_migration',
        'skip_heatmap_processing',
    ] as const
    trackedHeaders.forEach((header) => {
        const status = result[header] ? 'present' : 'absent'
        kafkaHeaderStatusCounter.labels(header, status).inc()
    })

    return result
}
