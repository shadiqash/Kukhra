#!/usr/bin/env python
import os
import sys

from dotenv import load_dotenv
load_dotenv()


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you on the correct virtualenv?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
