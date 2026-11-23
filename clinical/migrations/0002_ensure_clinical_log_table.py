from django.db import migrations


def ensure_clinical_log_table(apps, schema_editor):
    """Repair databases that recorded the regenerated initial migration as applied."""
    ClinicalLog = apps.get_model('clinical', 'ClinicalLog')
    existing_tables = schema_editor.connection.introspection.table_names()
    if ClinicalLog._meta.db_table not in existing_tables:
        schema_editor.create_model(ClinicalLog)


class Migration(migrations.Migration):
    dependencies = [
        ('clinical', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(ensure_clinical_log_table, migrations.RunPython.noop),
    ]
