import time
from decimal import Decimal
from django.core.management.base import BaseCommand
from billing.models import Charge
from billing.whatsapp import send_rent_reminder


class Command(BaseCommand):
    help = "Send WhatsApp rent reminders to all residents with unpaid charges."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview messages without sending via WhatsApp API.",
        )
        parser.add_argument(
            "--test-phone",
            type=str,
            help="Send all reminders to this single test phone number instead of resident numbers.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        test_phone = options.get("test_phone")

        unpaid_charges = (
            Charge.objects.exclude(status="PAID")
            .select_related("resident")
            .order_by("due_date")
        )

        sent_count = 0
        skipped_count = 0
        failed_count = 0

        for charge in unpaid_charges:
            resident = charge.resident
            pending = charge.pending_amount

            if pending <= Decimal("0.00"):
                skipped_count += 1
                continue

            target_phone = test_phone if test_phone else resident.phone

            if not target_phone:
                self.stdout.write(
                    self.style.WARNING(f"SKIPPED: {resident.full_name} (No phone number)")
                )
                skipped_count += 1
                continue

            amount_str = f"{pending:.0f}" if pending == pending.to_integral() else f"{pending:.2f}"
            month_year = charge.period
            due_date_str = charge.due_date.strftime("%d %b %Y")

            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] To: {resident.full_name} ({target_phone}) | "
                    f"Amount: ₹{amount_str} | Period: {month_year} | Due: {due_date_str}"
                )
                sent_count += 1
                continue

            result = send_rent_reminder(
                phone=target_phone,
                student_name=resident.full_name,
                amount=amount_str,
                month_year=month_year,
                due_date=due_date_str,
            )

            if result.get("ok"):
                sent_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"SENT: {resident.full_name} ({target_phone}) - ₹{amount_str} ({month_year})"
                    )
                )
            else:
                failed_count += 1
                err = result.get("data", {}).get("error", {}).get("message", "Unknown error")
                self.stdout.write(
                    self.style.ERROR(
                        f"FAILED: {resident.full_name} ({target_phone}) -> {err}"
                    )
                )

            time.sleep(0.5)

        self.stdout.write(
            self.style.NOTICE(
                f"\nSummary -> Sent: {sent_count} | Skipped: {skipped_count} | Failed: {failed_count}"
            )
        )