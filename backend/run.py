import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monitoria_site.settings')
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.argv.extend(['runserver', '127.0.0.1:8000'])
    execute_from_command_line(sys.argv)
