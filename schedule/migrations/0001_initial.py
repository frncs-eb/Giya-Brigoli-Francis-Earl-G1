import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name='ClassSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject_name', models.CharField(max_length=100)),
                ('room', models.CharField(blank=True, max_length=50, null=True)),
                ('day_of_week', models.SmallIntegerField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['day_of_week', 'start_time']},
        ),
        migrations.AddConstraint(
            model_name='classschedule',
            constraint=models.CheckConstraint(condition=models.Q(('day_of_week__gte', 1), ('day_of_week__lte', 7)), name='schedule_day_1_to_7'),
        ),
        migrations.AddConstraint(
            model_name='classschedule',
            constraint=models.CheckConstraint(condition=models.Q(('end_time__gt', models.F('start_time'))), name='schedule_end_after_start'),
        ),
        migrations.AddConstraint(
            model_name='classschedule',
            constraint=models.UniqueConstraint(fields=('user', 'day_of_week', 'start_time'), name='schedule_unique_user_day_start'),
        ),
    ]
