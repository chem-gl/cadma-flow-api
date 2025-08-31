from django.db import migrations, models


def fill_branch_reason(apps, schema_editor):
    workflow_branch_model = apps.get_model('cadmaflow_models', 'WorkflowBranch')
    # Replace any existing NULL values with empty string before making field non-nullable
    workflow_branch_model.objects.filter(branch_reason__isnull=True).update(branch_reason='')


def noop(apps, schema_editor):
    # No reverse data migration; leaving any existing values as-is
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cadmaflow_models', '0004_alter_workflowbranch_branch_reason'),
    ]

    operations = [
        migrations.RunPython(fill_branch_reason, noop),
        migrations.AlterField(
            model_name='workflowbranch',
            name='branch_reason',
            field=models.TextField(blank=True),
        ),
    ]
