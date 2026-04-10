import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import OperationalError, ProgrammingError


class Command(BaseCommand):
    help = 'Create or update a bootstrap admin user from environment variables.'

    def handle(self, *args, **options):
        email = os.environ.get('ADMIN_EMAIL', '').strip()
        password = os.environ.get('ADMIN_PASSWORD', '').strip()

        if not email or not password:
            self.stdout.write('Skipping admin bootstrap (ADMIN_EMAIL/ADMIN_PASSWORD not set).')
            return

        User = get_user_model()
        try:
            user, created = User.objects.get_or_create(email=email)
        except (OperationalError, ProgrammingError) as exc:
            self.stdout.write(self.style.WARNING(f'Skipping admin bootstrap ({exc}).'))
            return

        changed = False
        if not user.is_staff:
            user.is_staff = True
            changed = True
        if not user.is_superuser:
            user.is_superuser = True
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True

        # Keep password in sync with env so recovery is possible without shell access.
        if not user.check_password(password):
            user.set_password(password)
            changed = True

        if created or changed:
            user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {email}'))
        elif changed:
            self.stdout.write(self.style.SUCCESS(f'Updated admin user: {email}'))
        else:
            self.stdout.write(f'Admin user already configured: {email}')
