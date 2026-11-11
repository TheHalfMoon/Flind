import { LemonDialog } from '@flind/lemon-ui'

export function confirmRemoveFromQueue(queueName: string, onConfirm: () => void): void {
    LemonDialog.open({
        title: `Remove from "${queueName}"?`,
        primaryButton: { status: 'danger', children: 'Remove from queue', onClick: onConfirm },
        secondaryButton: { children: 'Cancel' },
    })
}
