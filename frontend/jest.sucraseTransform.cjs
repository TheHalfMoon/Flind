'use strict'

// Sucrase emits CJS for Jest but intentionally leaves import.meta untouched.
// Flind's browser-only Vite environment variables must fail closed in Jest,
// where there is no import.meta.env and no production Vite configuration.
const sucrase = require('@sucrase/jest-plugin')
const ts = require('typescript')

const browserConfigModules = [
    '/frontend/src/lib/flindPublicLinks.ts',
    '/frontend/src/lib/flindSupportMailto.ts',
    '/frontend/src/lib/flindRegionHosts.ts',
    '/frontend/src/lib/oauth/oauthClient.ts',
    '/frontend/src/lib/components/HelpMenu/incidentStatus.ts',
    '/frontend/src/scenes/authentication/shared/arrivedFromWebsiteLogic.ts',
]

function jestSafeViteEnv(source, filename) {
    if (
        typeof source !== 'string' ||
        typeof filename !== 'string' ||
        !browserConfigModules.some((suffix) => filename.replaceAll('\\', '/').endsWith(suffix))
    ) {
        return source
    }
    // Syntax-aware replacement: never touch string literals, comments or
    // SDK instruction snippets that *describe* Vite environment syntax.
    const parsed = ts.createSourceFile(filename, source, ts.ScriptTarget.Latest, true)
    const spans = []
    function visit(node) {
        if (
            ts.isPropertyAccessExpression(node) &&
            node.name.text === 'env' &&
            ts.isMetaProperty(node.expression) &&
            node.expression.keywordToken === ts.SyntaxKind.ImportKeyword &&
            node.expression.name.text === 'meta'
        ) {
            spans.push([node.getStart(parsed), node.end])
        }
        ts.forEachChild(node, visit)
    }
    visit(parsed)
    let result = source
    for (const [start, end] of spans.reverse()) {
        result = result.slice(0, start) + '({})' + result.slice(end)
    }
    return result
}

module.exports = {
    process(source, filename, options) {
        return sucrase.process(jestSafeViteEnv(source, filename), filename, options)
    },
    jestSafeViteEnv,
}
