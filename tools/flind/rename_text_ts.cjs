// Rename the product name PostHog to Flind inside TS/JS prose only: string and template literals, JSX text and
// comments. Code identifiers, imports and package names are left to the code-rename stages.
// Usage: node rename_text_ts.cjs <typescript-module-dir> <file-list> <report>
const fs = require('fs')
const ts = require(process.argv[2])

const WORD = /(?<![\w@./-])PostHog(?![\w/])(?!,? Inc\b)/g
const files = fs.readFileSync(process.argv[3], 'utf8').split(/\r?\n/).filter(Boolean)
const report = []

function scriptKind(path) {
    if (path.endsWith('.tsx')) return ts.ScriptKind.TSX
    if (path.endsWith('.jsx')) return ts.ScriptKind.JSX
    if (/\.(js|mjs|cjs)$/.test(path)) return ts.ScriptKind.JS
    return ts.ScriptKind.TS
}

for (const path of files) {
    let text
    try {
        text = fs.readFileSync(path, 'utf8')
    } catch {
        continue
    }
    if (!text.includes('PostHog')) continue
    const sf = ts.createSourceFile(path, text, ts.ScriptTarget.Latest, true, scriptKind(path))
    const ranges = []
    const seenComments = new Set()
    const addComments = (list) => {
        for (const c of list || []) {
            const key = c.pos + ':' + c.end
            if (!seenComments.has(key)) {
                seenComments.add(key)
                ranges.push([c.pos, c.end])
            }
        }
    }
    const visit = (node) => {
        addComments(ts.getLeadingCommentRanges(text, node.pos))
        addComments(ts.getTrailingCommentRanges(text, node.end))
        switch (node.kind) {
            case ts.SyntaxKind.StringLiteral:
            case ts.SyntaxKind.NoSubstitutionTemplateLiteral:
            case ts.SyntaxKind.TemplateHead:
            case ts.SyntaxKind.TemplateMiddle:
            case ts.SyntaxKind.TemplateTail:
            case ts.SyntaxKind.JsxText: {
                const parent = node.parent
                // Module specifiers name packages, not the product.
                const isSpecifier =
                    parent &&
                    (ts.isImportDeclaration(parent) ||
                        ts.isExportDeclaration(parent) ||
                        ts.isExternalModuleReference(parent) ||
                        ts.isImportTypeNode?.(parent?.parent))
                if (!isSpecifier) ranges.push([node.getStart(sf), node.end])
                break
            }
        }
        ts.forEachChild(node, visit)
    }
    visit(sf)
    addComments(ts.getLeadingCommentRanges(text, sf.endOfFileToken.pos))
    if (!ranges.length) continue
    ranges.sort((a, b) => a[0] - b[0])
    let out = ''
    let last = 0
    let changed = 0
    for (const [s, e] of ranges) {
        if (s < last) continue
        out += text.slice(last, s)
        const piece = text.slice(s, e).replace(WORD, () => {
            changed++
            return 'Flind'
        })
        out += piece
        last = e
    }
    out += text.slice(last)
    if (changed) {
        fs.writeFileSync(path, out)
        report.push(`${changed}\t${path}`)
    }
}
fs.writeFileSync(process.argv[4], report.join('\n') + '\n')
console.log(`${report.length} TS/JS files changed`)
