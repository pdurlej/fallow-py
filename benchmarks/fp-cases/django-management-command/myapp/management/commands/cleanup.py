class Command:
    def handle(self, *args, **options):
        return "cleaned"


def handle():
    return "legacy-command-entry"
