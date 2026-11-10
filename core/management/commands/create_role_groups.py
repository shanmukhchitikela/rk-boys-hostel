from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from core.permissions import ROLE_GROUPS


class Command(BaseCommand):
    help = "Create the Owner, Manager, and Warden staff role groups."

    def handle(self, *args, **options):
        for role_name in ROLE_GROUPS:
            _, created = Group.objects.get_or_create(name=role_name)
            status = "created" if created else "already exists"
            self.stdout.write(f"{role_name}: {status}")