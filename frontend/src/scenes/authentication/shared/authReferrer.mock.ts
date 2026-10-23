export const WEBSITE_REFERRER = 'https://flind.example/pricing'

export function setDocumentReferrer(referrer: string): void {
    Object.defineProperty(document, 'referrer', { value: referrer, configurable: true })
}
