import { useActions, useValues } from 'kea'
import {
    Button,
    Dialog,
    DialogBody,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    Empty,
    EmptyDescription,
    EmptyHeader,
    EmptyTitle,
    Skeleton,
    Text,
} from 'lib/ui/quill'

import { SourceMapsExamplesBrowser } from './SourceMapsExamplesBrowser'
import { sourceMapsExamplesLogic } from './sourceMapsExamplesLogic'
import { SOURCE_MAPS_PLATFORM_LABELS } from './sourceMapsPlatforms'

export function SourceMapsExamplesModal(): JSX.Element {
    const { isOpen, platform, examples, examplesLoading, examplesFailed, selectedExampleIndex } =
        useValues(sourceMapsExamplesLogic)
    const { closeExamples, loadExamples, selectExample } = useActions(sourceMapsExamplesLogic)
    const labels = SOURCE_MAPS_PLATFORM_LABELS[platform ?? 'javascript']
    const lookbackHours = examples?.lookback_hours ?? 24
    const retry = (): void => {
        if (platform) {
            loadExamples(platform)
        }
    }

    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && closeExamples()}>
            <DialogContent size="wide">
                <DialogHeader>
                    <DialogTitle>{`${labels.platform} frames missing ${labels.symbols}`}</DialogTitle>
                    <DialogDescription>
                        {`The files and builds with the most frames missing ${labels.symbols} in the last ${lookbackHours} hours.`}
                    </DialogDescription>
                </DialogHeader>
                <DialogBody>
                    {examplesLoading || (examples === null && !examplesFailed) ? (
                        <div className="flex flex-col gap-2">
                            <Skeleton className="h-12" />
                            <Skeleton className="h-12" />
                            <Skeleton className="h-12" />
                        </div>
                    ) : examplesFailed || !examples ? (
                        <Text size="xs" variant="destructive">
                            Couldn't load the examples. If it keeps failing, contact support.{' '}
                            <Button variant="link" size="inline" onClick={retry}>
                                Try again
                            </Button>
                        </Text>
                    ) : examples.results.length === 0 ? (
                        <Empty>
                            <EmptyHeader>
                                <EmptyTitle>{`No frames are missing ${labels.symbols}`}</EmptyTitle>
                                <EmptyDescription>
                                    {`Nothing to upload from the last ${lookbackHours} hours.`}
                                </EmptyDescription>
                            </EmptyHeader>
                        </Empty>
                    ) : (
                        <SourceMapsExamplesBrowser
                            examples={examples}
                            selectedIndex={selectedExampleIndex}
                            onSelect={selectExample}
                            onRetry={retry}
                            onOpenException={closeExamples}
                        />
                    )}
                </DialogBody>
                <DialogFooter>
                    <Button variant="outline" onClick={closeExamples}>
                        Close
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
