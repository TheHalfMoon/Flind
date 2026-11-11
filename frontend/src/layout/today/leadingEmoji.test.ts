import { leadingEmoji, withoutLeadingEmoji } from './leadingEmoji'

describe('leadingEmoji', () => {
    it.each([
        ['🎉 Flind App', '🎉', 'Flind App'],
        ['🎉Flind App', '🎉', 'Flind App'],
        ['👩‍💻 Dev team', '👩‍💻', 'Dev team'],
        ['❤️ Fans', '❤️', 'Fans'],
        ['👍🏽 Thumbs', '👍🏽', 'Thumbs'],
        ['🎉', '🎉', '🎉'],
        ['Flind 🎉', null, 'Flind 🎉'],
        ['Flind', null, 'Flind'],
        ['', null, ''],
    ])('splits %j into %j and %j', (name, emoji, rest) => {
        expect(leadingEmoji(name)).toEqual(emoji)
        expect(withoutLeadingEmoji(name)).toEqual(rest)
    })
})
