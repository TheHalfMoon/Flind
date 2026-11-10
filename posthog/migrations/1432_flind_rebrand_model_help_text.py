from django.db import migrations, models


class Migration(migrations.Migration):
    # Flind rebrand: help_text only. No schema change; Django records help_text in migration state.
    dependencies = [
        ("posthog", "1431_squash_2026_11_02_schema_addons"),
    ]

    operations = [
        migrations.AlterField(
            model_name="oauthapplication",
            name="is_verified",
            field=models.BooleanField(default=False, help_text="True if this application has been verified by Flind"),
        ),
        migrations.AlterField(
            model_name="oauthapplication",
            name="is_first_party",
            field=models.BooleanField(
                default=False,
                help_text="True if this is a first-party Flind application that skips OAuth consent",
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="is_ai_training_opted_in",
            field=models.BooleanField(
                blank=True,
                default=True,
                help_text="When True, this organization allows its data to be used to train Flind AI models.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="read_only_mcp_access",
            field=models.BooleanField(
                blank=True,
                default=False,
                help_text="When True, requests through the Flind MCP server can read but not change this organization's data.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="hide_mcp_hints",
            field=models.BooleanField(
                db_default=False,
                default=False,
                help_text="When true, the user has opted out of in-app hints promoting the Flind MCP integration after taking actions.",
            ),
        ),
    ]
