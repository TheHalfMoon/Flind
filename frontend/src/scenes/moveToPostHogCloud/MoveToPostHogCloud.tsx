import { SceneExport } from 'scenes/sceneTypes'

// Keep the legacy route registered for existing bookmarks, but never
// direct a Flind user to another product's cloud signup or documentation.
export const scene: SceneExport = {
    component: FlindCloudMigrationUnavailable,
}

export function FlindCloudMigrationUnavailable(): JSX.Element {
    return (
        <div className="max-w-2xl mx-auto p-8">
            <h1 className="text-2xl font-bold">Flind Cloud migration is unavailable</h1>
            <p className="mt-4">
                Flind does not currently offer an automated hosted migration. Your self-hosted
                instance remains the data destination until you configure a service you control.
            </p>
        </div>
    )
}
