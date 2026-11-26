from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from notifications.services import generate_for_user

class Command(BaseCommand):
    help = 'Generate in-app reminders for every active user.'

    def handle(self, *args, **options):
        total = 0
        for user in get_user_model().objects.filter(is_active=True).iterator():
            total += generate_for_user(user)
        self.stdout.write(self.style.SUCCESS(f'Created {total} reminders.'))
