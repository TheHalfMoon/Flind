import json
from typing import Any, cast

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.utils.cache import patch_cache_control
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import ensure_csrf_cookie

from flind.region_redirect import allowed_region_host, valid_region_hostname

from posthog.cloud_utils import is_cloud
from posthog.dataclasses import frozen
from posthog.models.user import User
from posthog.templatetags.posthog_filters import TolerantJSONEncoder
from posthog.utils import add_user_app_context, feature_flag_bootstrap, full_stage_user_app_context, render_template
from posthog.views import login_required

@frozen
class _PageMetadata:
    title: str
    description: str
    self_hosted_description: str


# Each title matches the document title the SPA sets for the scene, so the tab title doesn't change when the app boots.
_PUBLIC_PAGE_METADATA: dict[str, _PageMetadata] = {
    "/login": _PageMetadata(
        title="Log in • Flind",
        description="Log in to Flind, the single platform for engineers to analyze, test, observe, and deploy new features.",
        self_hosted_description="Log in to your self-hosted Flind instance.",
    ),
    "/signup": _PageMetadata(
        title="Sign up • Flind",
        description=(
            "Create your Flind account to analyze, test, observe, and deploy new features. "
            "Configure analytics, experimentation, and observability for your workspace."
        ),
        self_hosted_description="Create an account on your self-hosted Flind instance.",
    ),
}


def _structured_data_json(metadata: _PageMetadata, canonical_url: str) -> str:
    structured_data = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": metadata.title,
        "description": metadata.description,
        "url": canonical_url,
        "isPartOf": {"@type": "WebSite", "name": "Flind", "url": settings.SITE_URL},
        "about": {
            "@type": "SoftwareApplication",
            "name": "Flind",
            "applicationCategory": "BusinessApplication",
            "operatingSystem": "Web",
            "url": settings.SITE_URL,
        },
        "publisher": {"@type": "Organization", "name": "Flind", "url": settings.SITE_URL},
    }
    # The template renders this inside <script> with |safe, so no character may close the element.
    return json.dumps(structured_data).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def public_page_metadata_context(request: HttpRequest) -> dict[str, str]:
    """Template context for the search and link-preview tags of a public page, or an empty
    dict for every other path. The canonical URL drops the query string, so links such as
    `/login?next=...` count as one page."""
    path = request.path.rstrip("/")
    metadata = _PUBLIC_PAGE_METADATA.get(path)
    if metadata is None:
        return {}
    canonical_url = f"{settings.SITE_URL}{path}"
    if not is_cloud():
        return {
            "page_title": metadata.title,
            "page_description": metadata.self_hosted_description,
            "canonical_url": canonical_url,
        }
    return {
        "page_title": metadata.title,
        "page_description": metadata.description,
        "canonical_url": canonical_url,
        "structured_data_json": _structured_data_json(metadata, canonical_url),
    }


def region_host_from_current_instance(cookie_value: str | None) -> str | None:
    """Only accept hosts that the Flind operator explicitly configured."""
    return allowed_region_host(
        cookie_value,
        (settings.FLIND_REGION_HOST_US, settings.FLIND_REGION_HOST_EU),
    )


def app_region_redirect(request: HttpRequest) -> HttpResponseRedirect | None:
    """Opt-in Flind multi-region redirect; no default external destination.

    A user-controlled cookie is not authority to redirect to arbitrary hosts.
    Self-hosted single-instance Flind never enables this by default.
    """
    if request.method not in ("GET", "HEAD"):
        return None
    app_host = valid_region_hostname(settings.FLIND_APP_HOST)
    if not app_host or request.get_host().split(":")[0].lower() != app_host:
        return None

    target_host = region_host_from_current_instance(request.COOKIES.get("ph_current_instance"))
    if target_host is None and settings.FLIND_REDIRECT_TO_PRIMARY:
        target_host = valid_region_hostname(settings.FLIND_REGION_HOST_US)
    if not target_host or target_host == app_host:
        return None

    url = "https://{}{}".format(target_host, request.get_full_path())
    if url_has_allowed_host_and_scheme(url, target_host, True):
        return HttpResponseRedirect(url)
    return None


@ensure_csrf_cookie
def _render_home(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
    return render_template("index.html", request, public_page_metadata_context(request))


# Wrapped once at import time (as `login_required(home)` used to be) so the catch-all
# authenticated route doesn't rebuild the wrapper on every request.
_login_required_render_home = login_required(_render_home)


def home(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
    """Entrypoint for the unauthenticated frontend routes (login, signup, …). Runs the
    configured Flind cross-region redirect before rendering so users land on their
    logged-in region (see `app_region_redirect`)."""
    region_redirect = app_region_redirect(request)
    if region_redirect is not None:
        return region_redirect
    return _render_home(request, *args, **kwargs)


def home_with_region_redirect(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
    """Catch-all entrypoint for authenticated frontend routes. The cross-region redirect
    runs before `login_required` so configured Flind deep links reach the right region
    without a detour through the login page (see `app_region_redirect`). It wraps
    `_render_home` rather than `home` so the redirect check runs exactly once per request."""
    region_redirect = app_region_redirect(request)
    if region_redirect is not None:
        return region_redirect
    return _login_required_render_home(request, *args, **kwargs)


def app_context(request: HttpRequest) -> JsonResponse:
    """The signed-in user's part of the app context, for an app page rendered without it.

    The `boot` stage, the default, has what the first screen reads. The page boots on it, then fetches the `full`
    stage for the rest."""
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication credentials were not provided."}, status=401)
    stage = request.GET.get("stage", "boot")
    if stage == "full":
        body: dict[str, Any] = {"app_context": full_stage_user_app_context(request)}
    elif stage == "boot":
        posthog_app_context: dict[str, Any] = {}
        add_user_app_context(request, posthog_app_context, stage="boot")
        body = {
            "app_context": posthog_app_context,
            "feature_flags": feature_flag_bootstrap(cast(User, request.user), posthog_app_context["current_user"]),
        }
    else:
        return JsonResponse({"detail": "stage must be boot or full."}, status=400)
    response = JsonResponse(body, encoder=TolerantJSONEncoder)
    patch_cache_control(response, no_store=True)
    return response
