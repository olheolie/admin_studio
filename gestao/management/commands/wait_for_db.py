import time
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand
from typing import NoReturn

class Command(BaseCommand):
    """
    Django command to wait for the database to be available.
    """
    help = 'Django command to wait for database'

    def handle(self, *args, **options) -> NoReturn:
        """
        Entrypoint for the command execution.
        """
        self.stdout.write('Waiting for database...')
        db_up = False
        while not db_up:
            try:
                self.check(databases=['default'])
                db_up = True
            except (OperationalError, Exception):
                self.stdout.write('Database unavailable, waiting 1 second...')
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS('Database available!'))
