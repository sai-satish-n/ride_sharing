from django.core.management.base import BaseCommand
from django.utils import timezone
from payments_module.models import Settlement, PaymentStatusLookup

class Command(BaseCommand):
    help = "Mark settlements as settled and update payment_status to COMPLETED"

    def handle(self, *args, **options):
        # Payment status 2 (assuming it exists)
        try:
            status_settled = PaymentStatusLookup.objects.get(status_name = 'COMPLETED')
        except PaymentStatusLookup.DoesNotExist:
            self.stdout.write(self.style.ERROR("PaymentStatusLookup with id=2 does not exist"))
            return

        # Filter settlements that are not settled yet
        settlements_to_update = Settlement.objects.filter(setteled_at__isnull=True)

        count = settlements_to_update.count()

        # Update fields
        settlements_to_update.update(
            setteled_at=timezone.now(),
            payment_status=status_settled
        )

        self.stdout.write(self.style.SUCCESS(f"Updated {count} settlements"))