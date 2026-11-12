// React documents production error codes as "Minified React error #<digits>".
// Older SDKs may report related React DOM / React.js variants. Keep the
// extracted code numeric so an exception cannot inject an arbitrary URL path.
const REACT_PRODUCTION_ERROR = /\b(?:Minified\s+)?React(?:\.js)?(?: DOM)?(?: production)? error #(\d+)\b/i

export function extractReactErrorCode(message: string): string | null {
    return REACT_PRODUCTION_ERROR.exec(message)?.[1] ?? null
}
