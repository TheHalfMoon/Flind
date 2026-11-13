/**
 * SDK logos are bundled with Flind. External vendor images are stored as
 * static assets with source URLs and checksums in shared/logos/vendor/SOURCES.json.
 * SDK selection must never fetch an unrelated image CDN when rendered.
 * Local SVG/PNG/WebP imports and inline TSX components are both supported.
 */
import { Logomark } from 'lib/brand'
import { flindDocsUrl } from 'lib/flindPublicLinks'

import { SDK, SDKKey, SDKTag } from '~/types'

import androidImage from '../shared/logos/android.svg'
import angularImage from '../shared/logos/angular.svg'
import { AnthropicLogo } from '../shared/logos/AnthropicLogo'
import { AstroLogo } from '../shared/logos/AstroLogo'
import { BubbleLogo } from '../shared/logos/BubbleLogo'
import djangoImage from '../shared/logos/django.svg'
import docusaurusImage from '../shared/logos/docusaurus.svg'
import dotnetImage from '../shared/logos/dotnet.svg'
import elixirImage from '../shared/logos/elixir.svg'
import flutterImage from '../shared/logos/flutter.svg'
import { FramerLogo } from '../shared/logos/FramerLogo'
import gatsbyImage from '../shared/logos/gatsby.svg'
import geminiImage from '../shared/logos/gemini.svg'
import goImage from '../shared/logos/go.svg'
import gtmImage from '../shared/logos/gtm.svg'
import honoImage from '../shared/logos/hono.svg'
import { IOSLogo } from '../shared/logos/IOSLogo'
import javaImage from '../shared/logos/java.svg'
import jsImage from '../shared/logos/javascript_web.svg'
import { LangChainLogo } from '../shared/logos/LangChainLogo'
import langfuseImage from '../shared/logos/langfuse.svg'
import laravelImage from '../shared/logos/laravel.svg'
import moengageImage from '../shared/logos/moengage.png'
import n8nImage from '../shared/logos/n8n.svg'
import nextjsImage from '../shared/logos/nextjs.svg'
import nodejsImage from '../shared/logos/nodejs.svg'
import nuxtImage from '../shared/logos/nuxt.svg'
import { OpenAILogo } from '../shared/logos/OpenAILogo'
import { OpenRouterLogo } from '../shared/logos/OpenRouterLogo'
import phpImage from '../shared/logos/php.svg'
import pythonImage from '../shared/logos/python.svg'
import railsImage from '../shared/logos/rails.svg'
import reactImage from '../shared/logos/react.svg'
import reactNativeImage from '../shared/logos/react.svg'
import { ReactRouterLogo } from '../shared/logos/ReactRouterLogo'
import { RemixLogo } from '../shared/logos/RemixLogo'
import { RetoolLogo } from '../shared/logos/RetoolLogo'
import rubyImage from '../shared/logos/ruby.svg'
import { RudderstackLogo } from '../shared/logos/RudderstackLogo'
import rustImage from '../shared/logos/rust.svg'
import segmentImage from '../shared/logos/segment.svg'
import { SentryLogo } from '../shared/logos/SentryLogo'
import shopifyImage from '../shared/logos/shopify.svg'
import svelteImage from '../shared/logos/svelte.svg'
import tanStackImage from '../shared/logos/tanstack.png'
import traceloopImage from '../shared/logos/traceloop.svg'
import viteImage from '../shared/logos/vite.svg'
import vueImage from '../shared/logos/vue.svg'
import webflowImage from '../shared/logos/webflow.svg'
import { WordpressLogo } from '../shared/logos/WordpressLogo'
import zapierImage from '../shared/logos/zapier.svg'

import sdkVendorLogo1 from '../shared/logos/vendor/vendor_autogen_a8c56d013e_35f7cbb8.svg'
import sdkVendorLogo2 from '../shared/logos/vendor/vendor_azure_openai_884ba0124a_72239bdd.svg'
import sdkVendorLogo3 from '../shared/logos/vendor/vendor_bedrock_5c06698148_e0758f37.png'
import sdkVendorLogo4 from '../shared/logos/vendor/vendor_cerebras_4d953c1c2b_da9aaa6d.png'
import sdkVendorLogo5 from '../shared/logos/vendor/vendor_cloudflare_logo_6572a9f441_0b6ea2ee.svg'
import sdkVendorLogo6 from '../shared/logos/vendor/vendor_cohere_0ddf02d545_b0f743a9.svg'
import sdkVendorLogo7 from '../shared/logos/vendor/vendor_convex_d8dcddcd63_0ca3df9c.svg'
import sdkVendorLogo8 from '../shared/logos/vendor/vendor_crewai_67ee9f5eb6_42235c29.svg'
import sdkVendorLogo9 from '../shared/logos/vendor/vendor_dedalus_labs_logo_e03bb97137_45da41f8.svg'
import sdkVendorLogo10 from '../shared/logos/vendor/vendor_deepseek_df02608124_9502b156.svg'
import sdkVendorLogo11 from '../shared/logos/vendor/vendor_dspy_548bc2f255_4bfba519.webp'
import sdkVendorLogo12 from '../shared/logos/vendor/vendor_fireworks_ai_a3d8a59e96_a3a4a24f.svg'
import sdkVendorLogo13 from '../shared/logos/vendor/vendor_groq_a0ed539e47_bf4a73fa.png'
import sdkVendorLogo14 from '../shared/logos/vendor/vendor_helicone_7c41fa4c2d_04dff6cb.svg'
import sdkVendorLogo15 from '../shared/logos/vendor/vendor_hugging_face_ae0a406f62_c111ddab.svg'
import sdkVendorLogo16 from '../shared/logos/vendor/vendor_instructor_b1982d9ce9_395d9925.svg'
import sdkVendorLogo17 from '../shared/logos/vendor/vendor_kmp_7d185d2b.svg'
import sdkVendorLogo18 from '../shared/logos/vendor/vendor_langgraph_2f91869ac8_a07af6a3.svg'
import sdkVendorLogo19 from '../shared/logos/vendor/vendor_litellmicon_a2805d75e5_4f00e46f.webp'
import sdkVendorLogo20 from '../shared/logos/vendor/vendor_llamaindex_f831132d7c_253ea49a.svg'
import sdkVendorLogo21 from '../shared/logos/vendor/vendor_mastra_7ea7df92ab_e12c81b1.svg'
import sdkVendorLogo22 from '../shared/logos/vendor/vendor_mirascope_33f38e04ea_d6d7112f.svg'
import sdkVendorLogo23 from '../shared/logos/vendor/vendor_mistral_551c75e2dd_57184110.svg'
import sdkVendorLogo24 from '../shared/logos/vendor/vendor_ollama_ff56896a1f_648edce0.svg'
import sdkVendorLogo25 from '../shared/logos/vendor/vendor_opentelemetry_afb29df5ab_18f8dd86.svg'
import sdkVendorLogo26 from '../shared/logos/vendor/vendor_perplexity_7d451cb62c_c2a182ca.svg'
import sdkVendorLogo27 from '../shared/logos/vendor/vendor_portkey_15a83f0395_bd770b7c.svg'
import sdkVendorLogo28 from '../shared/logos/vendor/vendor_pydantic_ai_55029bc39b_3e547f5b.svg'
import sdkVendorLogo29 from '../shared/logos/vendor/vendor_roblox_corporation_2025_logo_svg_301751b47c_690ea5fc.webp'
import sdkVendorLogo30 from '../shared/logos/vendor/vendor_semantic_kernel_5102489978_3715458d.webp'
import sdkVendorLogo31 from '../shared/logos/vendor/vendor_smolagents_logo_1_545072ae17_0920db57.webp'
import sdkVendorLogo32 from '../shared/logos/vendor/vendor_together_ai_49ac1a57fb_b9fe3320.svg'
import sdkVendorLogo33 from '../shared/logos/vendor/vendor_unity_9f9c332941_714334c6.svg'
import sdkVendorLogo34 from '../shared/logos/vendor/vendor_vercel_373fa70879_50d1ba95.svg'
import sdkVendorLogo35 from '../shared/logos/vendor/vendor_xai_77b917714b_1137cefb.svg'

export const ALL_SDKS: SDK[] = [
    // Web
    {
        name: 'Next.js',
        key: SDKKey.NEXT_JS,
        tags: [SDKTag.WEB, SDKTag.SERVER, SDKTag.POPULAR],
        recommended: true,
        image: nextjsImage,
        docsLink: flindDocsUrl('libraries/next-js') ?? '',
    },
    {
        name: 'Web',
        key: SDKKey.JS_WEB,
        recommended: true,
        tags: [SDKTag.POPULAR, SDKTag.WEB],
        image: jsImage,
        docsLink: flindDocsUrl('libraries/js') ?? '',
    },
    {
        name: 'React',
        key: SDKKey.REACT,
        tags: [SDKTag.WEB, SDKTag.POPULAR],
        recommended: true,
        image: reactImage,
        docsLink: flindDocsUrl('libraries/react') ?? '',
    },
    {
        name: 'React Native',
        key: SDKKey.REACT_NATIVE,
        tags: [SDKTag.MOBILE, SDKTag.POPULAR],
        recommended: true,
        image: reactNativeImage,
        docsLink: flindDocsUrl('libraries/react-native') ?? '',
    },
    {
        name: 'Android',
        key: SDKKey.ANDROID,
        tags: [SDKTag.MOBILE],
        image: androidImage,
        docsLink: flindDocsUrl('libraries/android') ?? '',
    },
    {
        name: 'Angular',
        key: SDKKey.ANGULAR,
        tags: [SDKTag.WEB],
        image: angularImage,
        docsLink: flindDocsUrl('libraries/angular') ?? '',
    },
    {
        name: 'API',
        key: SDKKey.API,
        tags: [SDKTag.SERVER, SDKTag.INTEGRATION],
        image: (
            <span className="flex h-8 w-8">
                <Logomark className="w-8 h-auto" />
            </span>
        ),
        docsLink: flindDocsUrl('api') ?? '',
    },
    {
        name: 'Astro',
        key: SDKKey.ASTRO,
        tags: [SDKTag.WEB],
        image: <AstroLogo />,
        docsLink: flindDocsUrl('libraries/astro') ?? '',
    },
    {
        name: 'Bubble',
        key: SDKKey.BUBBLE,
        tags: [SDKTag.WEB],
        image: <BubbleLogo />,
        docsLink: flindDocsUrl('libraries/bubble') ?? '',
    },
    {
        name: 'Django',
        key: SDKKey.DJANGO,
        tags: [SDKTag.SERVER],
        image: djangoImage,
        docsLink: flindDocsUrl('libraries/django') ?? '',
    },
    {
        name: '.NET',
        key: SDKKey.DOTNET,
        tags: [SDKTag.SERVER],
        image: dotnetImage,
        docsLink: flindDocsUrl('libraries/dotnet') ?? '',
    },
    {
        name: 'Elixir',
        key: SDKKey.ELIXIR,
        tags: [SDKTag.SERVER],
        image: elixirImage,
        docsLink: flindDocsUrl('libraries/elixir') ?? '',
    },
    {
        name: 'Flutter',
        key: SDKKey.FLUTTER,
        tags: [SDKTag.MOBILE],
        image: flutterImage,
        docsLink: flindDocsUrl('libraries/flutter') ?? '',
    },
    {
        name: 'Framer',
        key: SDKKey.FRAMER,
        tags: [SDKTag.WEB],
        image: <FramerLogo />,
        docsLink: flindDocsUrl('libraries/framer') ?? '',
    },
    {
        name: 'Gatsby',
        key: SDKKey.GATSBY,
        tags: [SDKTag.WEB],
        image: gatsbyImage,
        docsLink: flindDocsUrl('libraries/gatsby') ?? '',
    },
    {
        name: 'Go',
        key: SDKKey.GO,
        tags: [SDKTag.SERVER],
        image: goImage,
        docsLink: flindDocsUrl('libraries/go') ?? '',
    },
    {
        name: 'Hono',
        key: SDKKey.HONO,
        tags: [SDKTag.SERVER],
        image: honoImage,
        docsLink: flindDocsUrl('libraries/hono') ?? '',
    },
    {
        name: 'OpenAI',
        key: SDKKey.OPENAI,
        tags: [SDKTag.MODEL_PROVIDER, SDKTag.FRAMEWORK],
        image: <OpenAILogo />,
        docsLink: flindDocsUrl('ai-observability/installation/openai') ?? '',
    },
    {
        name: 'OpenAI Agents',
        key: SDKKey.OPENAI_AGENTS,
        tags: [SDKTag.FRAMEWORK],
        image: <OpenAILogo />,
        docsLink: flindDocsUrl('ai-observability/installation/openai-agents') ?? '',
    },
    {
        name: 'Anthropic',
        key: SDKKey.ANTHROPIC,
        tags: [SDKTag.MODEL_PROVIDER],
        image: <AnthropicLogo />,
        docsLink: flindDocsUrl('ai-observability/installation/anthropic') ?? '',
    },
    {
        name: 'Google Gemini',
        key: SDKKey.GOOGLE_GEMINI,
        tags: [SDKTag.MODEL_PROVIDER],
        image: geminiImage,
        docsLink: flindDocsUrl('ai-observability/installation/google') ?? '',
    },
    {
        name: 'Google ADK',
        key: SDKKey.GOOGLE_ADK,
        tags: [SDKTag.FRAMEWORK],
        image: geminiImage,
        docsLink: flindDocsUrl('ai-observability/installation/google-adk') ?? '',
    },
    {
        name: 'Vercel AI SDK',
        key: SDKKey.VERCEL_AI,
        tags: [SDKTag.FRAMEWORK],
        image: sdkVendorLogo34,
        docsLink: flindDocsUrl('ai-observability/installation/vercel-ai') ?? '',
    },
    {
        name: 'Eve',
        key: SDKKey.EVE,
        tags: [SDKTag.FRAMEWORK],
        searchTerms: ['Vercel Eve', 'agent'],
        image: sdkVendorLogo34,
        docsLink: flindDocsUrl('ai-observability/installation/eve') ?? '',
    },
    {
        name: 'LangChain',
        key: SDKKey.LANGCHAIN,
        tags: [SDKTag.FRAMEWORK],
        image: <LangChainLogo />,
        docsLink: flindDocsUrl('ai-observability/installation/langchain') ?? '',
    },
    {
        name: 'LiteLLM',
        key: SDKKey.LITELLM,
        tags: [SDKTag.FRAMEWORK, SDKTag.GATEWAY],
        image: sdkVendorLogo19,
        docsLink: flindDocsUrl('ai-observability/installation/litellm') ?? '',
    },
    {
        name: 'OpenRouter',
        key: SDKKey.OPENROUTER,
        tags: [SDKTag.GATEWAY],
        image: <OpenRouterLogo />,
        docsLink: flindDocsUrl('ai-observability/installation/openrouter') ?? '',
    },
    {
        name: 'Cloudflare AI Gateway',
        key: SDKKey.CLOUDFLARE_AI_GATEWAY,
        tags: [SDKTag.GATEWAY],
        image: sdkVendorLogo5,
        docsLink: flindDocsUrl('ai-observability/installation/cloudflare-ai-gateway') ?? '',
    },
    {
        name: 'Dedalus Labs',
        key: SDKKey.DEDALUS,
        tags: [SDKTag.GATEWAY],
        image: sdkVendorLogo9,
        docsLink: flindDocsUrl('ai-observability/installation/dedalus') ?? '',
    },
    {
        name: 'DeepSeek',
        key: SDKKey.DEEPSEEK,
        tags: [SDKTag.MODEL_PROVIDER],
        image: sdkVendorLogo10,
        docsLink: flindDocsUrl('ai-observability/installation/deepseek') ?? '',
    },
    {
        name: 'LangGraph',
        key: SDKKey.LANGGRAPH,
        tags: [SDKTag.FRAMEWORK],
        image: sdkVendorLogo18,
        docsLink: flindDocsUrl('ai-observability/installation/langgraph') ?? '',
    },
    {
        name: 'Ollama',
        key: SDKKey.OLLAMA,
        tags: [SDKTag.MODEL_PROVIDER],
        image: sdkVendorLogo24,
        docsLink: flindDocsUrl('ai-observability/installation/ollama') ?? '',
    },
    {
        name: 'AWS Bedrock',
        key: SDKKey.AWS_BEDROCK,
        tags: [SDKTag.MODEL_PROVIDER],
        image: sdkVendorLogo3,
        docsLink: flindDocsUrl('ai-observability/installation/aws-bedrock') ?? '',
    },
    {
        name: 'Azure OpenAI',
        key: SDKKey.AZURE_OPENAI,
        tags: [SDKTag.MODEL_PROVIDER],
        image: sdkVendorLogo2,
        docsLink: flindDocsUrl('ai-observability/installation/azure-openai') ?? '',
    },
    {
        name: 'Groq',
        key: SDKKey.GROQ,
        tags: [SDKTag.MODEL_PROVIDER],
        image: sdkVendorLogo13,
        docsLink: flindDocsUrl('ai-observability/installation/groq') ?? '',
    },
    {
        name: 'Mistral',
        key: SDKKey.MISTRAL,
        tags: [SDKTag.MODEL_PROVIDER],
        image: sdkVendorLogo23,
        docsLink: flindDocsUrl('ai-observability/installation/mistral') ?? '',
    },
    {
        name: 'LlamaIndex',
        key: SDKKey.LLAMAINDEX,
        tags: [SDKTag.FRAMEWORK],
        image: sdkVendorLogo20,
        docsLink: flindDocsUrl('ai-observability/installation/llamaindex') ?? '',
    },
    {
        name: 'CrewAI',
        key: SDKKey.CREWAI,
        tags: [SDKTag.FRAMEWORK],
        image: sdkVendorLogo8,
        docsLink: flindDocsUrl('ai-observability/installation/crewai') ?? '',
    },
    {
        name: 'Instructor',
        key: SDKKey.INSTRUCTOR,
        tags: [SDKTag.FRAMEWORK],
        image: sdkVendorLogo16,
        docsLink: flindDocsUrl('ai-observability/installation/instructor') ?? '',
    },
    {
        name: 'Pydantic AI',
        key: SDKKey.PYDANTIC_AI,
        tags: [SDKTag.FRAMEWORK],
        image: sdkVendorLogo28,
        docsLink: flindDocsUrl('ai-observability/installation/pydantic-ai') ?? '',
    },
    {
        name: 'xAI',
        key: SDKKey.XAI,
        tags: [SDKTag.MODEL_PROVIDER],
        image: sdkVendorLogo35,
        docsLink: flindDocsUrl('ai-observability/installation/xai') ?? '',
    },
    {
        name: 'Perplexity',
        key: SDKKey.PERPLEXITY,
        tags: [SDKTag.MODEL_PROVIDER],
        image: sdkVendorLogo26,
        docsLink: flindDocsUrl('ai-observability/installation/perplexity') ?? '',
    },
    {
        name: 'Together AI',
        key: SDKKey.TOGETHER_AI,
        tags: [SDKTag.MODEL_PROVIDER],
        image: sdkVendorLogo32,
        docsLink: flindDocsUrl('ai-observability/installation/together-ai') ?? '',
    },
    {
        name: 'Fireworks AI',
        key: SDKKey.FIREWORKS_AI,
        tags: [SDKTag.MODEL_PROVIDER],
        image: sdkVendorLogo12,
        docsLink: flindDocsUrl('ai-observability/installation/fireworks-ai') ?? '',
    },
    {
        name: 'Cohere',
        key: SDKKey.COHERE,
        tags: [SDKTag.MODEL_PROVIDER],
        image: sdkVendorLogo6,
        docsLink: flindDocsUrl('ai-observability/installation/cohere') ?? '',
    },
    {
        name: 'Hugging Face',
        key: SDKKey.HUGGING_FACE,
        tags: [SDKTag.MODEL_PROVIDER],
        image: sdkVendorLogo15,
        docsLink: flindDocsUrl('ai-observability/installation/hugging-face') ?? '',
    },
    {
        name: 'DSPy',
        key: SDKKey.DSPY,
        tags: [SDKTag.FRAMEWORK],
        image: sdkVendorLogo11,
        docsLink: flindDocsUrl('ai-observability/installation/dspy') ?? '',
    },
    {
        name: 'AutoGen',
        key: SDKKey.AUTOGEN,
        tags: [SDKTag.FRAMEWORK],
        image: sdkVendorLogo1,
        docsLink: flindDocsUrl('ai-observability/installation/autogen') ?? '',
    },
    {
        name: 'Semantic Kernel',
        key: SDKKey.SEMANTIC_KERNEL,
        tags: [SDKTag.FRAMEWORK],
        image: sdkVendorLogo30,
        docsLink: flindDocsUrl('ai-observability/installation/semantic-kernel') ?? '',
    },
    {
        name: 'smolagents',
        key: SDKKey.SMOLAGENTS,
        tags: [SDKTag.FRAMEWORK],
        image: sdkVendorLogo31,
        docsLink: flindDocsUrl('ai-observability/installation/smolagents') ?? '',
    },
    {
        name: 'Mastra',
        key: SDKKey.MASTRA,
        tags: [SDKTag.FRAMEWORK],
        image: sdkVendorLogo21,
        docsLink: flindDocsUrl('ai-observability/installation/mastra') ?? '',
    },
    {
        name: 'Mirascope',
        key: SDKKey.MIRASCOPE,
        tags: [SDKTag.FRAMEWORK],
        image: sdkVendorLogo22,
        docsLink: flindDocsUrl('ai-observability/installation/mirascope') ?? '',
    },
    {
        name: 'Convex',
        key: SDKKey.CONVEX,
        tags: [SDKTag.FRAMEWORK],
        image: sdkVendorLogo7,
        docsLink: flindDocsUrl('ai-observability/installation/convex') ?? '',
    },
    {
        name: 'Cerebras',
        key: SDKKey.CEREBRAS,
        tags: [SDKTag.MODEL_PROVIDER],
        image: sdkVendorLogo4,
        docsLink: flindDocsUrl('ai-observability/installation/cerebras') ?? '',
    },
    {
        name: 'Vercel AI Gateway',
        key: SDKKey.VERCEL_AI_GATEWAY,
        tags: [SDKTag.GATEWAY],
        image: sdkVendorLogo34,
        docsLink: flindDocsUrl('ai-observability/installation/vercel-ai-gateway') ?? '',
    },
    {
        name: 'Portkey',
        key: SDKKey.PORTKEY,
        tags: [SDKTag.GATEWAY],
        image: sdkVendorLogo27,
        docsLink: flindDocsUrl('ai-observability/installation/portkey') ?? '',
    },
    {
        name: 'Helicone',
        key: SDKKey.HELICONE,
        tags: [SDKTag.LLM, SDKTag.GATEWAY],
        image: sdkVendorLogo14,
        docsLink: flindDocsUrl('ai-observability/installation/helicone') ?? '',
    },
    {
        name: 'Manual Capture',
        key: SDKKey.MANUAL_CAPTURE,
        tags: [SDKTag.FRAMEWORK, SDKTag.MODEL_PROVIDER, SDKTag.GATEWAY],
        image: (
            <span className="flex w-8 pb-3">
                <Logomark className="w-8 h-auto" />
            </span>
        ),
        docsLink: flindDocsUrl('ai-observability/installation/manual-capture') ?? '',
    },
    {
        name: 'OpenTelemetry',
        key: SDKKey.OPENTELEMETRY,
        tags: [SDKTag.INTEGRATION],
        image: sdkVendorLogo25,
        docsLink: flindDocsUrl('ai-observability/installation/opentelemetry') ?? '',
    },
    {
        name: 'iOS',
        key: SDKKey.IOS,
        tags: [SDKTag.MOBILE],
        image: <IOSLogo />,
        docsLink: flindDocsUrl('libraries/ios') ?? '',
    },
    {
        name: 'Java',
        key: SDKKey.JAVA,
        tags: [SDKTag.SERVER],
        image: javaImage,
        docsLink: flindDocsUrl('libraries/java') ?? '',
    },
    {
        name: 'Kotlin Multiplatform',
        key: SDKKey.KMP,
        tags: [SDKTag.MOBILE, SDKTag.WEB],
        image: sdkVendorLogo17,
        docsLink: flindDocsUrl('libraries/kmp') ?? '',
    },
    {
        name: 'Langfuse',
        key: SDKKey.LANGFUSE,
        tags: [SDKTag.LLM],
        image: langfuseImage,
        docsLink: flindDocsUrl('ai-observability/integrations/langfuse-posthog') ?? '',
    },
    {
        name: 'Laravel',
        key: SDKKey.LARAVEL,
        tags: [SDKTag.SERVER],
        image: laravelImage,
        docsLink: flindDocsUrl('libraries/laravel') ?? '',
    },
    {
        name: 'Node.js',
        key: SDKKey.NODE_JS,
        tags: [SDKTag.SERVER, SDKTag.POPULAR],
        recommended: true,
        image: nodejsImage,
        docsLink: flindDocsUrl('libraries/node') ?? '',
    },
    {
        name: 'Nuxt.js 3.7+',
        key: SDKKey.NUXT_JS,
        tags: [SDKTag.WEB, SDKTag.SERVER],
        image: nuxtImage,
        docsLink: flindDocsUrl('libraries/nuxt-js') ?? '',
    },
    {
        name: 'Nuxt.js 3.6 and below',
        key: SDKKey.NUXT_JS_36,
        tags: [SDKTag.WEB, SDKTag.SERVER],
        image: nuxtImage,
        docsLink: flindDocsUrl('libraries/nuxt-js') ?? '',
    },
    {
        name: 'PHP',
        key: SDKKey.PHP,
        tags: [SDKTag.SERVER],
        image: phpImage,
        docsLink: flindDocsUrl('libraries/php') ?? '',
    },
    {
        name: 'Python',
        key: SDKKey.PYTHON,
        tags: [SDKTag.SERVER, SDKTag.POPULAR],
        recommended: true,
        image: pythonImage,
        docsLink: flindDocsUrl('libraries/python') ?? '',
    },
    {
        name: 'React Router',
        key: SDKKey.REACT_ROUTER,
        tags: [SDKTag.WEB],
        searchTerms: ['remix'],
        image: <ReactRouterLogo />,
        docsLink: flindDocsUrl('libraries/react-router') ?? '',
    },
    {
        name: 'Remix',
        key: SDKKey.REMIX,
        tags: [SDKTag.WEB],
        image: <RemixLogo />,
        docsLink: flindDocsUrl('libraries/remix') ?? '',
    },
    {
        name: 'Ruby',
        key: SDKKey.RUBY,
        tags: [SDKTag.SERVER],
        image: rubyImage,
        docsLink: flindDocsUrl('libraries/ruby') ?? '',
    },
    {
        name: 'Ruby on Rails',
        key: SDKKey.RUBY_ON_RAILS,
        tags: [SDKTag.SERVER],
        image: railsImage,
        docsLink: flindDocsUrl('libraries/rails') ?? '',
    },
    {
        name: 'Roblox',
        key: SDKKey.ROBLOX,
        tags: [SDKTag.OTHER],
        image: sdkVendorLogo29,
        docsLink: flindDocsUrl('error-tracking/installation/roblox') ?? '',
    },
    {
        name: 'Rust',
        key: SDKKey.RUST,
        tags: [SDKTag.SERVER],
        image: rustImage,
        docsLink: flindDocsUrl('error-tracking/installation/rust') ?? '',
    },
    {
        name: 'Svelte',
        key: SDKKey.SVELTE,
        tags: [SDKTag.WEB],
        image: svelteImage,
        docsLink: flindDocsUrl('libraries/svelte') ?? '',
    },
    {
        name: 'TanStack Start',
        key: SDKKey.TANSTACK_START,
        tags: [SDKTag.WEB],
        image: tanStackImage,
        docsLink: flindDocsUrl('libraries/react') ?? '',
    },
    {
        name: 'Unity',
        key: SDKKey.UNITY,
        tags: [SDKTag.OTHER],
        image: sdkVendorLogo33,
        docsLink: flindDocsUrl('error-tracking/installation/unity') ?? '',
    },
    {
        name: 'Traceloop',
        key: SDKKey.TRACELOOP,
        tags: [SDKTag.LLM],
        image: traceloopImage,
        docsLink: flindDocsUrl('ai-observability/integrations/traceloop-posthog') ?? '',
    },
    {
        name: 'Vite',
        key: SDKKey.VITE,
        tags: [SDKTag.WEB],
        image: viteImage,
        docsLink: flindDocsUrl('libraries/react') ?? '',
    },
    {
        name: 'Vue.js',
        key: SDKKey.VUE_JS,
        tags: [SDKTag.WEB],
        image: vueImage,
        docsLink: flindDocsUrl('libraries/vue-js') ?? '',
    },
    {
        name: 'Webflow',
        key: SDKKey.WEBFLOW,
        tags: [SDKTag.WEB],
        image: webflowImage,
        docsLink: flindDocsUrl('libraries/webflow') ?? '',
    },
    // Integrations
    {
        name: 'Google Tag Manager',
        key: SDKKey.GOOGLE_TAG_MANAGER,
        tags: [SDKTag.WEB, SDKTag.INTEGRATION],
        image: gtmImage,
        docsLink: flindDocsUrl('libraries/google-tag-manager') ?? '',
    },
    {
        name: 'Docusaurus',
        key: SDKKey.DOCUSAURUS,
        tags: [SDKTag.INTEGRATION],
        image: docusaurusImage,
        docsLink: flindDocsUrl('libraries/docusaurus') ?? '',
    },
    {
        name: 'MoEngage',
        key: SDKKey.MOENGAGE,
        tags: [SDKTag.WEB, SDKTag.INTEGRATION],
        image: moengageImage,
        docsLink: flindDocsUrl('libraries/moengage') ?? '',
    },
    {
        name: 'n8n',
        key: SDKKey.N8N,
        tags: [SDKTag.INTEGRATION],
        image: n8nImage,
        docsLink: flindDocsUrl('libraries/n8n') ?? '',
    },
    {
        name: 'Segment',
        key: SDKKey.SEGMENT,
        tags: [SDKTag.INTEGRATION],
        image: segmentImage,
        docsLink: flindDocsUrl('libraries/segment') ?? '',
    },
    {
        name: 'Sentry',
        key: SDKKey.SENTRY,
        tags: [SDKTag.INTEGRATION],
        image: <SentryLogo />,
        docsLink: flindDocsUrl('libraries/sentry') ?? '',
    },
    {
        name: 'Shopify',
        key: SDKKey.SHOPIFY,
        tags: [SDKTag.INTEGRATION],
        image: shopifyImage,
        docsLink: flindDocsUrl('libraries/shopify') ?? '',
    },
    {
        name: 'RudderStack',
        key: SDKKey.RUDDERSTACK,
        tags: [SDKTag.INTEGRATION],
        image: <RudderstackLogo />,
        docsLink: flindDocsUrl('libraries/rudderstack') ?? '',
    },
    {
        name: 'Wordpress',
        key: SDKKey.WORDPRESS,
        tags: [SDKTag.INTEGRATION],
        image: <WordpressLogo />,
        docsLink: flindDocsUrl('libraries/wordpress') ?? '',
    },
    {
        name: 'Retool',
        key: SDKKey.RETOOL,
        tags: [SDKTag.INTEGRATION],
        image: <RetoolLogo />,
        docsLink: flindDocsUrl('libraries/retool') ?? '',
    },
    {
        name: 'Zapier',
        key: SDKKey.ZAPIER,
        tags: [SDKTag.INTEGRATION],
        image: zapierImage,
        docsLink: flindDocsUrl('libraries/zapier') ?? '',
    },
]
