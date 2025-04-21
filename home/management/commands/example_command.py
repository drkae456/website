from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Description of what this command does'

    def add_arguments(self, parser):
        # Add command line arguments here
        parser.add_argument(
            '--example',
            type=str,
            help='Example argument',
        )

    def handle(self, *args, **options):
        # Command logic goes here
        example_arg = options.get('example')
        
        if example_arg:
            self.stdout.write(self.style.SUCCESS(f'Example argument: {example_arg}'))
        else:
            self.stdout.write(self.style.SUCCESS('Command executed successfully')) 