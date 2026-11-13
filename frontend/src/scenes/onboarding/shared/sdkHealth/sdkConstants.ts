import { flindDocsUrl, flindPublicUrl } from 'lib/flindPublicLinks'

import type { SdkType } from './sdkHealthLogic'

export const SDK_TYPE_READABLE_NAME: Record<SdkType, string> = {
    web: 'Web',
    'posthog-ios': 'iOS',
    'posthog-android': 'Android',
    'posthog-java': 'Java (legacy)',
    'posthog-server': 'Java',
    'posthog-node': 'Node.js',
    'posthog-python': 'Python',
    'posthog-php': 'PHP',
    'posthog-laravel': 'Laravel',
    'posthog-ruby': 'Ruby',
    'posthog-go': 'Go',
    'posthog-flutter': 'Flutter',
    'posthog-react-native': 'React Native',
    'posthog-kmp': 'Kotlin Multiplatform',
    'posthog-dotnet': '.NET',
    'posthog-elixir': 'Elixir',
    'posthog-unity': 'Unity',
    'posthog-node-mcp': 'Node.js MCP',
    'posthog-python-mcp': 'Python MCP',
    'posthog-edge': 'Edge',
    'posthog-convex': 'Convex',
    'posthog-rails': 'Ruby on Rails',
    'posthog-aspnetcore': 'ASP.NET Core',
    'posthog-rs': 'Rust',
    'posthog-rs-mcp': 'Rust MCP',
    'posthog-godot': 'Godot',
    'posthog-unreal': 'Unreal Engine',
    'posthog-go-mcp': 'Go MCP',
    'posthog-ruby-mcp': 'Ruby MCP',
    'posthog-roblox': 'Roblox',
    js: 'JavaScript Lite',
}

// Local/owned SDK links only. The SDK report may identify upstream library
// versions, but its UI must never navigate to an inherited vendor website.
// Until the operator configures an owned HTTPS docs root, links remain hidden.
// SDK identity names here are compatibility values supplied by existing events.
const SDK_DOCS_PATHS: Record<SdkType, string> = {
    web: 'libraries/js',
    'posthog-ios': 'libraries/ios',
    'posthog-android': 'libraries/android',
    'posthog-java': 'libraries/java',
    'posthog-server': 'libraries/java',
    'posthog-node': 'libraries/node',
    'posthog-python': 'libraries/python',
    'posthog-php': 'libraries/php',
    'posthog-laravel': 'libraries/laravel',
    'posthog-ruby': 'libraries/ruby',
    'posthog-go': 'libraries/go',
    'posthog-flutter': 'libraries/flutter',
    'posthog-react-native': 'libraries/react-native',
    'posthog-kmp': 'libraries/kmp',
    'posthog-dotnet': 'libraries/dotnet',
    'posthog-elixir': 'libraries/elixir',
    'posthog-unity': 'libraries/unity',
    'posthog-node-mcp': 'mcp-analytics',
    'posthog-python-mcp': 'mcp-analytics',
    'posthog-edge': 'libraries/node',
    'posthog-convex': 'libraries/convex',
    'posthog-rails': 'libraries/ruby-on-rails',
    'posthog-aspnetcore': 'libraries/dotnet',
    'posthog-rs': 'libraries/rust',
    'posthog-rs-mcp': 'mcp-analytics',
    'posthog-godot': 'libraries/godot',
    'posthog-unreal': 'libraries/unreal',
    'posthog-go-mcp': 'mcp-analytics',
    'posthog-ruby-mcp': 'mcp-analytics',
    'posthog-roblox': 'libraries/roblox',
    js: 'libraries/js-lite',
}

type SdkOwnedLinks = { releases: string | null; docs: string | null }

// Keep the entire existing set of SDK choices, including mobile, MCP and
// integrations; only replace navigation destinations with validated URLs.
export const SDK_DOCS_LINKS: Record<SdkType, SdkOwnedLinks> = Object.fromEntries(
    Object.entries(SDK_DOCS_PATHS).map(([sdkType, docsPath]) => [
        sdkType,
        { releases: flindPublicUrl('changelog'), docs: flindDocsUrl(docsPath) },
    ])
) as Record<SdkType, SdkOwnedLinks>
