import { IconDownload } from '@flind/icons'
import { LemonButton } from '@flind/lemon-ui'

export interface TraceExportButtonProps {
    loading: boolean
    onExport: () => void
}

export function TraceExportButton({ loading, onExport }: TraceExportButtonProps): JSX.Element {
    return (
        <LemonButton
            size="small"
            type="secondary"
            icon={<IconDownload />}
            loading={loading}
            onClick={onExport}
            tooltip="Export this trace as a JSON file"
            data-attr="trace-view-export"
        />
    )
}
