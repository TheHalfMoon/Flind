import { isInheritedProviderHostname } from '@/auth/hostSafety'
import { isInternalBuild, isLoopbackHost } from '@/lib/environment'

type ProjectScope = { host: string; projectId: number } | null

/** An operator, not a donor's app, chooses the host and project where Tasks agent runs. */
export function configuredTasksOrigin(
    hostValue: string | undefined = process.env.EXPO_PUBLIC_FLIND_TASKS_HOST
): string | null {
    if (!hostValue?.trim()) return null
    try {
        const url = new URL(hostValue.trim())
        if (
            !url.hostname ||
            url.username ||
            url.password ||
            url.pathname !== '/' ||
            url.search ||
            url.hash ||
            isInheritedProviderHostname(url.hostname) ||
            !(
                url.protocol === 'https:' ||
                (isInternalBuild && url.protocol === 'http:' && isLoopbackHost(url.hostname))
            )
        ) {
            return null
        }
        return url.origin
    } catch {
        return null
    }
}

/**
 * Default to the interoperable classic conversation API until an operator enables
 * a Tasks runtime for one exact signed-in Flind project. Existing conversations
 * are still opened by their server-reported runtime, not this setting.
 */
export function isTasksRuntimeProject(
    scope: ProjectScope,
    hostValue: string | undefined = process.env.EXPO_PUBLIC_FLIND_TASKS_HOST,
    projectValue: string | undefined = process.env.EXPO_PUBLIC_FLIND_TASKS_PROJECT_ID
): boolean {
    const origin = configuredTasksOrigin(hostValue)
    if (!scope || !origin || !projectValue || !/^[1-9]\d{0,9}$/.test(projectValue)) return false
    const projectId = Number(projectValue)
    if (!Number.isSafeInteger(projectId) || scope.projectId !== projectId) return false
    try {
        const host = new URL(scope.host)
        return (
            host.origin === origin &&
            host.pathname === '/' &&
            !host.search &&
            !host.hash &&
            !host.username &&
            !host.password
        )
    } catch {
        return false
    }
}
