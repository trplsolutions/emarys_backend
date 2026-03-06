import sys
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Promotes a user to the admin role'

    def add_arguments(self, parser):
        parser.add_argument('identifier', type=str, help='Email or username of the user to promote')

    def handle(self, *args, **options):
        User = get_user_model()
        identifier = options['identifier']
        
        try:
            # Try by email first
            user = User.objects.get(email=identifier)
        except User.DoesNotExist:
            try:
                # Fallback to username
                user = User.objects.get(username=identifier)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User "{identifier}" not found.'))
                sys.exit(1)
        
        user.role = 'admin'
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.stdout.write(self.style.SUCCESS(f'Successfully promoted {user.username} to admin (role=admin, is_superuser=True).'))
