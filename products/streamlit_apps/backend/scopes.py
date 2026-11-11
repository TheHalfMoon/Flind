"""What each API scope object this product owns is for. See posthog/scope_docs.py."""

from posthog.scope_docs import ScopeDoc

SCOPE_DOCS = (
    ScopeDoc(
        object="streamlit_app",
        name="Streamlit app",
        plural="Streamlit apps",
        description="Streamlit apps that run on your Flind data, including their source, versions, and running state.",
        group="Data warehouse & pipelines",
    ),
)
