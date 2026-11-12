import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

import { extractReactErrorCode } from '../src/lib/components/Errors/Exception/known-exceptions/javascript/react-minified-error-code.ts'

const component = readFileSync(new URL('../src/lib/components/Errors/Exception/known-exceptions/javascript/react-minified-error.tsx', import.meta.url), 'utf8')

test('canonical React minified production errors decode to numeric official docs URLs', () => {
    const samples = [
        ['Minified React error #418; visit https://react.dev/errors/418 for the full message.', '418'],
        ['Minified React error #31; visit https://react.dev/errors/31', '31'],
        ['React error #130', '130'],
        ['React.js error #185', '185'],
        ['React DOM production error #423', '423'],
        ['react production error #17', '17'],
    ]
    for (const [message, expected] of samples) {
        const actual = extractReactErrorCode(message)
        assert.equal(actual, expected, message)
        assert.equal('https://react.dev/errors/' + actual, 'https://react.dev/errors/' + expected)
    }
})

test('non-React and malformed strings cannot generate a React decoder URL', () => {
    for (const message of [
        'Minified React error #',
        'Minified React error #abc',
        'Minified Vue error #418',
        'SyntaxError: Unexpected token',
        'React error #418extra',
        'React error #<script>',
        '',
    ]) {
        assert.equal(extractReactErrorCode(message), null, message)
    }
})

test('actual React exception banner uses the runtime parser for both matching and rendering', () => {
    assert.match(component, /import \{ extractReactErrorCode \} from '\.\/react-minified-error-code'/)
    assert.match(component, /return extractReactErrorCode\(exception\.value\) !== null/)
    assert.match(component, /const errorCode = extractReactErrorCode\(exception\.value\)/)
    assert.match(component, /to=\{'https:\/\/react\.dev\/errors\/' \+ errorCode\}/)
    assert.doesNotMatch(component, /\.match\(\/React/)
})
