"""
CLI Authentication API using OAuth2 Device Flow

This implements the device authorization flow (RFC 8628) for the Flind CLI.
Users can authenticate without copying/pasting API keys.

Flow:
1. CLI requests device code
2. User opens browser and authorizes
3. CLI polls for completion
4. Returns Personal API Key
"""

import string
import secrets

from django.core.cache import cache
from django.utils import timezone

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from posthog.accessible_teams import AccessibleTeams, CredentialScopeDenied
from posthog.api.personal_api_key import validate_personal_api_key_scopes
from posthog.auth import SessionAuthentication
from posthog.models import PersonalAPIKey, Team, User
from posthog.personal_api_key_minting import mint_personal_api_key
from posthog.scopes import UNPRIVILEGED_SCOPES

# Device code lives for 10 minutes
DEVICE_CODE_EXPIRY_SECONDS = 600

# CLI polling interval (5 seconds)
CLI_POLL_INTERVAL_SECONDS = 5

# Scopes granted to CLI
CLI_SCOPES = [
    "event_definition:read",
    "property_definition:read",
    "error_tracking:write",
]


def generate_user_code() -> str:
    """Generate a human-readable code like 'ABCD-1234'"""
    letters = "".join(secrets.choice(string.ascii_uppercase) for _ in range(4))
    numbers = "".join(secrets.choice(string.digits) for _ in range(4))
    return f"{letters}-{numbers}"


def generate_device_code() -> str:
    """Generate a secure random device code"""
    return secrets.token_urlsafe(32)


def get_device_cache_key(device_code: str) -> str:
    """Get cache key for device code"""
    return f"cli_device:{device_code}"


def get_user_code_cache_key(user_code: str) -> str:
    """Get cache key for user code"""
    return f"cli_user_code:{user_code}"


def get_device_authorization_claim_key(device_code: str) -> str:
    """Atomic one-time claim while a CLI device request is minting its API key."""
    return f"cli_authorize_claim:{device_code}"


def get_device_poll_claim_key(device_code: str) -> str:
    """Atomic one-time claim before an authorized API key is returned."""
    return f"cli_poll_claim:{device_code}"


def get_validation_error_description(error: serializers.ValidationError) -> str:
    detail = error.detail
    if isinstance(detail, list) and detail:
        return str(detail[0])
    return str(detail)


class DeviceCodeResponseSerializer(serializers.Serializer):
    """Response containing device and user codes"""

    device_code = serializers.CharField(help_text="Code for CLI to poll with")
    user_code = serializers.CharField(help_text="Code for user to enter in browser")
    verification_uri = serializers.CharField(help_text="URL for user to visit")
    verification_uri_complete = serializers.CharField(help_text="URL with code pre-filled")
    expires_in = serializers.IntegerField(help_text="Seconds until code expires")
    interval = serializers.IntegerField(help_text="Polling interval in seconds")


class DeviceAuthorizationSerializer(serializers.Serializer):
    """User authorizes the device code"""

    user_code = serializers.CharField(max_length=9, help_text="The user code displayed in CLI")
    project_id = serializers.IntegerField(help_text="The project to authorize CLI access for")
    scopes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Scopes to grant to the CLI (defaults to CLI_SCOPES)",
    )


class DevicePollSerializer(serializers.Serializer):
    """CLI polls for authorization status"""

    device_code = serializers.CharField(help_text="Device code from initial request")


class DevicePollResponseSerializer(serializers.Serializer):
    """Response to poll request"""

    status = serializers.ChoiceField(choices=["pending", "authorized", "expired"])
    personal_api_key = serializers.CharField(required=False, help_text="The API key (only if authorized)")
    label = serializers.CharField(required=False, help_text="Label of the created key")  # type: ignore[assignment]
    project_id = serializers.CharField(required=False, help_text="The project ID (only if authorized)")
    scopes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Scopes granted to the created API key (only if authorized)",
    )


@extend_schema(extensions={"x-product": "core"})
class CLIAuthViewSet(viewsets.ViewSet):
    """
    OAuth2 Device Authorization Flow for CLI authentication

    Endpoints:
    - POST /api/cli-auth/device-code/  (no auth required)
    - POST /api/cli-auth/authorize/    (session auth required)
    - POST /api/cli-auth/poll/         (no auth required)
    """

    def get_permissions(self):
        """Authorize endpoint requires auth, others don't"""
        if getattr(self, "action", None) == "authorize":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_authenticators(self):
        """Only use session auth for browser-based authorization"""
        action = getattr(self, "action", None)

        # Check both action and URL path since action might not be set yet
        if action == "authorize" or (hasattr(self, "request") and "authorize" in self.request.path):
            return [SessionAuthentication()]

        return []

    @extend_schema(request=None, responses={200: DeviceCodeResponseSerializer})
    # nosemgrep: api-path-underscore -- shipped public API path, a rename breaks clients
    @action(methods=["POST"], detail=False, url_path="device-code")
    def device_code(self, request):
        """
        Step 1: CLI requests device code

        Returns device code for polling and user code for browser authorization.
        """
        device_code = generate_device_code()

        # A human-readable code has much less entropy than the device code.
        # Reserve its reverse lookup atomically so a collision cannot silently
        # redirect a browser's consent to another device.
        for _ in range(8):
            user_code = generate_user_code()
            user_code_cache_key = get_user_code_cache_key(user_code)
            if cache.add(user_code_cache_key, device_code, timeout=DEVICE_CODE_EXPIRY_SECONDS):
                break
        else:
            return Response(
                {"error": "temporarily_unavailable", "error_description": "Could not allocate a unique user code"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        device_cache_key = get_device_cache_key(device_code)
        try:
            cache.set(
                device_cache_key,
                {
                    "user_code": user_code,
                    "status": "pending",
                    "created_at": timezone.now().isoformat(),
                },
                timeout=DEVICE_CODE_EXPIRY_SECONDS,
            )
        except Exception:
            cache.delete(user_code_cache_key)
            raise

        # Get the base URL for verification
        # In production this would be the actual domain
        base_url = request.build_absolute_uri("/").rstrip("/")

        response_data = {
            "device_code": device_code,
            "user_code": user_code,
            "verification_uri": f"{base_url}/cli/authorize",
            "verification_uri_complete": f"{base_url}/cli/authorize?code={user_code}",
            "expires_in": DEVICE_CODE_EXPIRY_SECONDS,
            "interval": CLI_POLL_INTERVAL_SECONDS,
        }

        serializer = DeviceCodeResponseSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=DeviceAuthorizationSerializer)
    @action(methods=["POST"], detail=False, url_path="authorize")
    def authorize(self, request):
        """
        Step 2: User authorizes in browser

        Requires authenticated session. Creates a Personal API Key and marks
        the device code as authorized.
        """
        serializer = DeviceAuthorizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_code = serializer.validated_data["user_code"]
        project_id = serializer.validated_data["project_id"]
        scopes = serializer.validated_data.get("scopes", CLI_SCOPES)
        user: User = request.user

        # Validate that at least one scope is provided
        if not scopes:
            return Response(
                {"error": "invalid_request", "error_description": "At least one scope is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_personal_api_key_scopes(scopes, user, allowed_scopes=UNPRIVILEGED_SCOPES)
        except serializers.ValidationError as error:
            return Response(
                {"error": "invalid_scope", "error_description": get_validation_error_description(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Look up device code from user code
        user_code_cache_key = get_user_code_cache_key(user_code)
        device_code = cache.get(user_code_cache_key)
        if not device_code:
            return Response(
                {"error": "invalid_code", "error_description": "User code not found or expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get device code data
        device_cache_key = get_device_cache_key(device_code)
        device_data = cache.get(device_cache_key)
        if not device_data:
            return Response(
                {"error": "expired", "error_description": "Device code expired"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Prevent duplicate authorization (race condition)
        if device_data.get("status") == "authorized":
            return Response(
                {"error": "already_authorized", "error_description": "This code has already been authorized"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            team = Team.objects.get(id=project_id)
        except Team.DoesNotExist:
            return Response(
                {"error": "invalid_project", "error_description": "Project not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            teams = AccessibleTeams.for_request(request, [team.id])
        except CredentialScopeDenied:
            return Response(
                {"error": "access_denied", "error_description": "You do not have access to this project"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Label max length is 40 chars, so truncate if needed
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
        max_team_name_len = 40 - len("CLI - ") - len(f" - {timestamp}")
        team_name_truncated = team.name[:max_team_name_len] if len(team.name) > max_team_name_len else team.name
        label = f"CLI - {team_name_truncated} - {timestamp}"

        # cache.get() followed by minting is not atomic: two concurrent
        # consent requests can both observe "pending" and create two PATs.
        # cache.add() is atomic on supported shared cache backends. Keep the
        # successful claim until the device code expires to forbid replays.
        authorization_claim_key = get_device_authorization_claim_key(device_code)
        if not cache.add(authorization_claim_key, True, timeout=DEVICE_CODE_EXPIRY_SECONDS):
            return Response(
                {"error": "already_authorizing", "error_description": "This device authorization is already in progress"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        had_prior_pat = PersonalAPIKey.objects.filter(user=user).exists()
        try:
            minted = mint_personal_api_key(user, label=label, scopes=scopes, teams=teams)
        except Exception:
            # No key was returned: allow a new consent attempt after a
            # transient mint failure. Other post-mint errors leave the claim
            # intact rather than risking a duplicate credential.
            cache.delete(authorization_claim_key)
            raise

        # User explicitly authorized this CLI via SessionAuthentication (see
        # CLIAuthViewSet.get_authenticators - authorize is session-only). If they
        # had no prior PATs, treat the CLI key as already-acknowledged so the
        # review interstitial doesn't fire for the key they just minted. Skip
        # when prior PATs exist - those may be partner-issued and still warrant
        # the review.
        if not had_prior_pat and user.credentials_reviewed_at is None:
            user.credentials_reviewed_at = timezone.now()
            user.save(update_fields=["credentials_reviewed_at"])

        # Mark device as authorized and store the API key
        device_data["status"] = "authorized"
        device_data["personal_api_key"] = minted.value
        device_data["label"] = label
        device_data["project_id"] = str(project_id)
        device_data["scopes"] = scopes
        device_data["authorized_at"] = timezone.now().isoformat()
        device_data["user_id"] = user.id

        # Update cache with longer TTL to ensure CLI can poll
        cache.set(device_cache_key, device_data, timeout=60)  # 1 minute to retrieve

        return Response(
            {
                "status": "success",
                "label": label,
                "mask_value": minted.key.mask_value,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=DevicePollSerializer, responses={200: DevicePollResponseSerializer})
    @action(methods=["POST"], detail=False, url_path="poll")
    def poll(self, request):
        """
        Step 3: CLI polls for authorization status

        Returns:
        - 202: Still pending (keep polling)
        - 200: Authorized (includes API key)
        - 400: Expired or invalid
        """
        serializer = DevicePollSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device_code = serializer.validated_data["device_code"]

        # Look up device code
        device_cache_key = get_device_cache_key(device_code)
        device_data = cache.get(device_cache_key)

        if not device_data:
            return Response(
                {"status": "expired", "error": "expired_token", "error_description": "Device code expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if device_data["status"] == "pending":
            # Still waiting for authorization
            return Response(
                {"status": "pending"},
                status=status.HTTP_202_ACCEPTED,  # Indicates to keep polling
            )

        if device_data["status"] == "authorized":
            # Two polls can both read "authorized" before either deletes the
            # cache entry. Make the credential delivery one-time atomically.
            if not cache.add(get_device_poll_claim_key(device_code), True, timeout=DEVICE_CODE_EXPIRY_SECONDS):
                return Response(
                    {"status": "expired", "error": "expired_token", "error_description": "Device code already consumed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            response_data = {
                "status": "authorized",
                "personal_api_key": device_data["personal_api_key"],
                "label": device_data["label"],
                "project_id": device_data["project_id"],
                "scopes": device_data.get("scopes", []),
            }

            # Clean up - key has been retrieved
            cache.delete(device_cache_key)
            user_code_cache_key = get_user_code_cache_key(device_data["user_code"])
            cache.delete(user_code_cache_key)

            response_serializer = DevicePollResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        # Unknown status
        return Response(
            {"error": "invalid_request", "error_description": "Invalid device code status"},
            status=status.HTTP_400_BAD_REQUEST,
        )
