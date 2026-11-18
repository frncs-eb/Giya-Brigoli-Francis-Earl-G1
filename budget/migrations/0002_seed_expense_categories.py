from django.db import migrations


def seed_categories(apps, schema_editor):
    ExpenseCategory = apps.get_model('budget', 'ExpenseCategory')
    database = schema_editor.connection.alias
    for name in ('Food', 'Materials', 'Transportation', 'Others'):
        ExpenseCategory.objects.using(database).get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ('budget', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_categories, migrations.RunPython.noop),
    ]
