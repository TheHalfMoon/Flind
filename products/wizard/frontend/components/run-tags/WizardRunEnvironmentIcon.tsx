import { IconCloud, IconLaptop } from '@flind/icons'

import type { RunEnvironmentEnumApi } from '../../generated/api.schemas'

export function WizardRunEnvironmentIcon({ environment }: { environment: RunEnvironmentEnumApi }): JSX.Element {
    return environment === 'cloud' ? <IconCloud /> : <IconLaptop />
}
