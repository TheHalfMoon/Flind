import json
from collections.abc import Callable

from django.core.management.base import BaseCommand

import requests

from posthog.models import Project, User
from posthog.ph_client import PH_US_API_KEY, PH_US_HOST, flind_capture_host_allowed

from products.feature_flags.backend.models.feature_flag import FeatureFlag


def _build_filters(flag_data: dict) -> dict:
    # /flags?v=2 only exposes the single variant the distinct_id evaluated to,
    # so for multivariate flags we seed with that one variant at 100% and let
    # the user fill in the rest — better than silently dropping to boolean.
    variant = flag_data.get("variant")
    base: dict = {"groups": [{"properties": [], "rollout_percentage": 100}], "payloads": {}}
    if variant:
        base["multivariate"] = {"variants": [{"key": variant, "name": variant, "rollout_percentage": 100}]}
    return base


def sync_feature_flags_from_api(
    distinct_id: str,
    groups: dict[str, str] | None = None,
    output_fn: Callable[[str], None] = print,
) -> None:
    """
    Fetch feature flags from the PostHog API and sync them to the database.

    Args:
        distinct_id: The distinct ID for which to evaluate feature flags
        groups: Optional dict of group types to IDs (customer, instance, organization, project)
        output_fn: Function to call for output (defaults to print, can use self.stdout.write for management commands)
    """
    if not PH_US_API_KEY or not PH_US_HOST or not flind_capture_host_allowed(PH_US_HOST):
        raise RuntimeError("Flind-owned US analytics host and project API key must be configured")

    # Do not silently evaluate the flags of an unrelated customer/project.
    if groups is None:
        groups = {}

    output_fn(f"Fetching Flind feature flags for {distinct_id}...")
    response = requests.post(
        f"{PH_US_HOST.rstrip('/')}/flags?v=2",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"api_key": PH_US_API_KEY, "distinct_id": distinct_id, "groups": groups}),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    if "flags" not in data:
        output_fn("No flags found in API response")
        return

    first_user = User.objects.first()
    if not first_user:
        output_fn("No users found in database")
        return

    for project in Project.objects.all():
        team = project.teams.first()
        if team is None:
            output_fn(f"\nSkipping project {project.id} - {project.name or ''}: it has no teams")
            continue
        output_fn(f"\nProcessing project {project.id} - {project.name or ''}")
        output_fn("=" * 50)

        existing_flags = set(
            FeatureFlag.objects_including_soft_deleted.filter(team__project_id=project.id).values_list("key", flat=True)
        )
        deleted_flags = set(
            FeatureFlag.objects_including_soft_deleted.filter(team__project_id=project.id, deleted=True).values_list(
                "key", flat=True
            )
        )

        enabled_flags = sum(1 for flag_data in data["flags"].values() if flag_data.get("enabled", False))
        total_flags = enabled_flags
        undeleted_count = 0
        created_count = 0
        activated_count = 0
        deactivated_count = 0
        unchanged_count = 0

        for flag_key, flag_data in data["flags"].items():
            is_enabled = flag_data.get("enabled", False)
            if flag_key in deleted_flags and is_enabled:
                ff = FeatureFlag.objects_including_soft_deleted.get(team__project_id=project.id, key=flag_key)
                ff.deleted = False
                ff.active = True
                ff.save()
                output_fn(f"Undeleted feature flag '{flag_key}'")
                undeleted_count += 1

            elif flag_key not in existing_flags and is_enabled:
                FeatureFlag.objects.create(
                    team=team,
                    name=flag_key,
                    key=flag_key,
                    created_by=first_user,
                    active=True,
                    filters=_build_filters(flag_data),
                )
                output_fn(f"Created feature flag '{flag_key}'")
                created_count += 1

            else:
                ff = FeatureFlag.objects.filter(team__project_id=project.id, key=flag_key).first()
                if ff and ff.active != is_enabled:
                    ff.active = is_enabled
                    ff.save()
                    if is_enabled:
                        output_fn(f"Activated feature flag '{flag_key}'")
                        activated_count += 1
                    else:
                        output_fn(f"Deactivated feature flag '{flag_key}'")
                        deactivated_count += 1
                else:
                    unchanged_count += 1

        output_fn("\nProject Summary")
        output_fn("-" * 20)
        output_fn(f"Enabled flags from API: {total_flags}")
        output_fn(f"Existing: {len(existing_flags)}")
        output_fn(f"Undeleted: {undeleted_count}")
        output_fn(f"Created: {created_count}")
        output_fn(f"Activated: {activated_count}")
        output_fn(f"Deactivated: {deactivated_count}")
        output_fn(f"Unchanged: {unchanged_count}")
        output_fn(f"Total after sync: {len(existing_flags) + created_count}")

    output_fn("\nFeature flag sync complete.")


class Command(BaseCommand):
    help = "Sync feature flags from the configured Flind analytics API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--distinct_id", type=str, required=True, help="The distinct ID for which to evaluate feature flags"
        )
        parser.add_argument("--organization", type=str, help="Organization ID")
        parser.add_argument("--project", type=str, help="Project ID")
        parser.add_argument("--instance", type=str, help="Instance ID")
        parser.add_argument("--customer", type=str, help="Customer ID")

    def handle(self, *args, **options):
        distinct_id = options["distinct_id"]

        groups = {}

        for group_type in ["customer", "instance", "organization", "project"]:
            if options.get(group_type):
                groups[group_type] = options[group_type]

        try:
            sync_feature_flags_from_api(distinct_id=distinct_id, groups=groups or None, output_fn=self.stdout.write)
        except requests.exceptions.RequestException as e:
            self.stdout.write(f"Failed to fetch feature flags: {str(e)}")
            raise
        except Exception as e:
            self.stdout.write(f"Error while syncing flags: {str(e)}")
            raise
