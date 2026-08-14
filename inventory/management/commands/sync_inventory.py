from django.core.management.base import BaseCommand

from inventory.services.google_sync import sync_inventory


class Command(BaseCommand):

    help = "Synchronize inventory from CSV file"


    def handle(self, *args, **options):

        self.stdout.write(
            "Reading inventory CSV..."
        )


        try:

            result = sync_inventory()


            self.stdout.write(
                self.style.SUCCESS(
                    "\nSynchronization completed."
                )
            )


            self.stdout.write(
                f"Added: {result['added']}"
            )

            self.stdout.write(
                f"Updated: {result['updated']}"
            )

            self.stdout.write(
                f"Restored: {result['restored']}"
            )

            self.stdout.write(
                f"Removed: {result['removed']}"
            )


        except Exception as error:


            self.stdout.write(
                self.style.ERROR(
                    str(error)
                )
            )

            raise