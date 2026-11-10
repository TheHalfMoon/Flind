"""Tests for clearing a retired token's team metadata cache on token reset.

Adapted from upstream PostHog a3f2a2e71. Upstream keeps these handlers in posthog/storage/team_metadata_signal_handlers.py;
in Flind they live in posthog/tasks/team_metadata.py.
"""

import json

from posthog.test.base import BaseTest
from unittest.mock import Mock, patch

from django.db import transaction
from django.test import override_settings

from posthog.models.utils import generate_random_token_secret, hash_key_value
from posthog.storage import object_storage
from posthog.storage.team_access_cache import TOKEN_CACHE_PREFIX, token_auth_cache
from posthog.storage.team_metadata_cache import team_metadata_hypercache, update_team_metadata_cache
from posthog.tasks.team_metadata import clear_team_metadata_cache_for_token_task


@override_settings(FLAGS_REDIS_URL="redis://localhost:6379")
class TestRetiredTokenTeamMetadataClear(BaseTest):
    @patch("posthog.tasks.integrations.push_vercel_secrets.delay")
    def test_token_reset_clears_the_old_tokens_metadata_in_redis_and_s3(self, _mock_push_vercel: Mock) -> None:
        update_team_metadata_cache(self.team)
        api_token = self.team.api_token
        cache_key = team_metadata_hypercache.get_cache_key(api_token)
        assert team_metadata_hypercache.cache_client.get(cache_key) is not None
        assert object_storage.read(cache_key, missing_ok=True) is not None

        with self.captureOnCommitCallbacks(execute=True):
            self.team.reset_token_and_save(user=self.user, is_impersonated_session=False)
            # This write stands in for a refresh that writes the old token's entry before the commit.
            team_metadata_hypercache.set_cache_value(api_token, {"api_token": api_token})

        assert team_metadata_hypercache.cache_client.get(cache_key) is None
        assert object_storage.read(cache_key, missing_ok=True) is None

    @patch("posthog.tasks.integrations.push_vercel_secrets.delay")
    def test_token_reset_drops_the_secret_key_auth_entry(self, _mock_push_vercel: Mock) -> None:
        self.team.secret_api_token = generate_random_token_secret()
        self.team.save()
        auth_key = f"{TOKEN_CACHE_PREFIX}{hash_key_value(self.team.secret_api_token, mode='sha256')}"
        token_auth_cache.redis.setex(auth_key, 300, json.dumps({"type": "secret", "api_token": self.team.api_token}))

        with self.captureOnCommitCallbacks(execute=True):
            self.team.reset_token_and_save(user=self.user, is_impersonated_session=False)

        assert not token_auth_cache.redis.exists(auth_key)

    @patch("posthog.tasks.team_metadata.clear_team_metadata_cache_for_token_task.delay")
    @patch("posthog.tasks.integrations.push_vercel_secrets.delay")
    def test_rolled_back_token_reset_does_not_enqueue_the_clear(self, _mock_push_vercel: Mock, mock_clear: Mock) -> None:
        with self.captureOnCommitCallbacks(execute=True), self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.team.reset_token_and_save(user=self.user, is_impersonated_session=False)
                raise RuntimeError("roll back the reset")

        mock_clear.assert_not_called()

    @patch("posthog.tasks.team_access_cache_tasks.invalidate_team_tokens_task.apply_async")
    @patch("posthog.tasks.team_metadata.clear_team_metadata_cache_for_token_task.delay")
    @patch("posthog.tasks.integrations.push_vercel_secrets.delay")
    def test_failed_auth_drop_on_token_reset_retries_and_still_enqueues_the_clear(
        self, _mock_push_vercel: Mock, mock_clear: Mock, mock_auth_retry: Mock
    ) -> None:
        old_token = self.team.api_token

        with (
            patch.object(token_auth_cache, "invalidate_team_tokens", side_effect=ConnectionError("redis down")),
            self.captureOnCommitCallbacks(execute=True),
        ):
            self.team.reset_token_and_save(user=self.user, is_impersonated_session=False)

        mock_auth_retry.assert_called_once_with(args=[self.team.id], countdown=5)
        mock_clear.assert_called_once_with(old_token)

    @override_settings(FLAGS_REDIS_URL="")
    @patch("posthog.tasks.team_metadata.clear_team_metadata_cache_for_token_task.delay")
    @patch("posthog.tasks.integrations.push_vercel_secrets.delay")
    def test_token_reset_without_flags_redis_does_not_enqueue_the_clear(
        self, _mock_push_vercel: Mock, mock_clear: Mock
    ) -> None:
        with self.captureOnCommitCallbacks(execute=True):
            self.team.reset_token_and_save(user=self.user, is_impersonated_session=False)

        mock_clear.assert_not_called()


class TestClearTeamMetadataCacheForTokenTask(BaseTest):
    def test_skips_a_token_that_belongs_to_a_team(self) -> None:
        with patch.object(team_metadata_hypercache, "delete_cache_entry") as mock_delete:
            clear_team_metadata_cache_for_token_task(self.team.api_token)

        mock_delete.assert_not_called()

    def test_deletes_a_retired_token_with_strict_mirror(self) -> None:
        with patch.object(team_metadata_hypercache, "delete_cache_entry") as mock_delete:
            clear_team_metadata_cache_for_token_task("phc_retired_token")

        mock_delete.assert_called_once_with("phc_retired_token", strict_mirror=True)

    # Adapted from upstream PostHog a2605f740. Flind's task skips a token that still belongs to a team,
    # so this uses a retired token where upstream passes the live team token.
    def test_failed_mirror_delete_raises_so_the_task_retries(self) -> None:
        mirror = Mock()
        mirror.delete.side_effect = ConnectionError("mirror down")

        with (
            patch.object(team_metadata_hypercache, "secondary_cache_client", mirror),
            patch.object(object_storage, "delete"),
            self.assertRaises(ConnectionError),
        ):
            clear_team_metadata_cache_for_token_task("phc_retired_token")


# Adapted from upstream PostHog a2605f740 (posthog/storage/test/test_team_metadata_signal_handlers.py).
@override_settings(FLAGS_REDIS_URL="redis://localhost:6379")
class TestDeletedTeamTeamMetadataClear(BaseTest):
    def test_team_delete_clears_team_metadata_cache_in_redis_and_s3(self) -> None:
        update_team_metadata_cache(self.team)
        api_token = self.team.api_token
        cache_key = team_metadata_hypercache.get_cache_key(api_token)
        assert team_metadata_hypercache.cache_client.get(cache_key) is not None
        assert object_storage.read(cache_key, missing_ok=True) is not None

        with self.captureOnCommitCallbacks(execute=True):
            self.team.delete()
            # This write stands in for a refresh that runs after the pre_delete clear and before the commit.
            team_metadata_hypercache.set_cache_value(api_token, {"api_token": api_token})

        assert team_metadata_hypercache.cache_client.get(cache_key) is None
        assert object_storage.read(cache_key, missing_ok=True) is None

    @patch("posthog.tasks.team_metadata.clear_team_metadata_cache_for_token_task.delay")
    def test_team_delete_enqueues_the_retrying_clear_for_its_token(self, mock_clear: Mock) -> None:
        api_token = self.team.api_token

        with self.captureOnCommitCallbacks(execute=True):
            self.team.delete()

        mock_clear.assert_called_once_with(api_token)

    @patch("posthog.tasks.team_metadata.clear_team_metadata_cache_for_token_task.delay")
    def test_rolled_back_team_delete_does_not_enqueue_the_clear(self, mock_clear: Mock) -> None:
        with self.captureOnCommitCallbacks(execute=True), self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.team.delete()
                raise RuntimeError("roll back the delete")

        mock_clear.assert_not_called()

    @override_settings(FLAGS_REDIS_URL="")
    @patch("posthog.tasks.team_metadata.clear_team_metadata_cache_for_token_task.delay")
    def test_team_delete_without_flags_redis_does_not_enqueue_the_clear(self, mock_clear: Mock) -> None:
        with self.captureOnCommitCallbacks(execute=True):
            self.team.delete()

        mock_clear.assert_not_called()
