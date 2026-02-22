from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from rides.models import Region
from payments_module.models import SurgePricing, SurgePricingLog
from decimal import Decimal

class Command(BaseCommand):
    help = "Automatically calculate and insert surge pricing per region"

    def handle(self, *args, **kwargs):
        now = timezone.now()

        regions = Region.objects.filter(is_service_active=True)

        for region in regions:
            # Example surge calculation logic
            # TODO: Replace with your actual logic (demand, traffic, etc.)
            # Here we use random example surge for demo purposes
            import random
            new_multiplier = round(1 + random.random() * 1.0, 2)  # 1.0 to 2.0

            # Check if there is an active surge
            active_surge = SurgePricing.objects.filter(
                region=region,
                effective_from__lte=now,
                expires_at__gte=now
            ).first()

            # Set default 1-hour validity
            effective_from = now
            expires_at = now + timedelta(hours=1)

            if active_surge:
                old_multiplier = active_surge.surge_multiplier
                # Only insert new surge if multiplier changed
                if old_multiplier != new_multiplier:
                    # Insert new surge
                    surge = SurgePricing.objects.create(
                        region=region,
                        surge_multiplier=Decimal(new_multiplier),
                        effective_from=effective_from,
                        expires_at=expires_at
                    )

                    # Log the change
                    SurgePricingLog.objects.create(
                        surge_pricing_id=surge.surge_pricing_id,
                        region_code=region.region_code,
                        old_multiplier=old_multiplier,
                        new_multiplier=new_multiplier,
                        effective_from=effective_from,
                        expires_at=expires_at
                    )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Updated surge for region {region.region_name} from {old_multiplier} → {new_multiplier}"
                        )
                    )
                else:
                    self.stdout.write(
                        f"No change in surge for region {region.region_name} ({new_multiplier})"
                    )
            else:
                # No active surge, create one
                surge = SurgePricing.objects.create(
                    region=region,
                    surge_multiplier=Decimal(new_multiplier),
                    effective_from=effective_from,
                    expires_at=expires_at
                )

                SurgePricingLog.objects.create(
                    surge_pricing_id=surge.surge_pricing_id,
                    region_code=region.region_code,
                    old_multiplier=None,
                    new_multiplier=new_multiplier,
                    effective_from=effective_from,
                    expires_at=expires_at
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created new surge for region {region.region_name}: {new_multiplier}"
                    )
                )
