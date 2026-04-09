import json
import os

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import Listing, ListingOutdatedReport, ListingSuggestion


class Command(BaseCommand):
    help = 'Run recurring listing safety checks and optionally send admin alerts.'

    def add_arguments(self, parser):
        parser.add_argument('--stale-days', type=int, default=90)
        parser.add_argument('--draft-days', type=int, default=14)
        parser.add_argument('--pending-suggestion-days', type=int, default=14)
        parser.add_argument('--json', action='store_true', help='Output machine-readable JSON.')
        parser.add_argument(
            '--send-email',
            action='store_true',
            help='Send alert email when any check has non-zero results.',
        )
        parser.add_argument(
            '--fail-on-alert',
            action='store_true',
            help='Exit with non-zero status when any check has non-zero results.',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        stale_threshold = now - timezone.timedelta(days=options['stale_days'])
        draft_threshold = now - timezone.timedelta(days=options['draft_days'])
        pending_suggestion_threshold = now - timezone.timedelta(
            days=options['pending_suggestion_days']
        )

        results = {
            'checked_at': now.isoformat(),
            'thresholds': {
                'stale_days': options['stale_days'],
                'draft_days': options['draft_days'],
                'pending_suggestion_days': options['pending_suggestion_days'],
            },
            'counts': {
                'stale_published': Listing.objects.filter(
                    status=Listing.Status.PUBLISHED,
                    last_verified_at__lt=stale_threshold,
                ).count(),
                'unresolved_reports': ListingOutdatedReport.objects.filter(
                    resolved=False
                ).count(),
                'old_drafts': Listing.objects.filter(
                    status=Listing.Status.DRAFT,
                    updated_at__lt=draft_threshold,
                ).count(),
                'old_pending_suggestions': ListingSuggestion.objects.filter(
                    status=ListingSuggestion.Status.PENDING,
                    created_at__lt=pending_suggestion_threshold,
                ).count(),
            },
        }

        has_alerts = any(value > 0 for value in results['counts'].values())
        results['has_alerts'] = has_alerts

        if options['json']:
            self.stdout.write(json.dumps(results))
        else:
            self.stdout.write(
                'listing_health_check '
                f"stale_published={results['counts']['stale_published']} "
                f"unresolved_reports={results['counts']['unresolved_reports']} "
                f"old_drafts={results['counts']['old_drafts']} "
                f"old_pending_suggestions={results['counts']['old_pending_suggestions']} "
                f"has_alerts={has_alerts}"
            )

        if options['send_email'] and has_alerts:
            recipients = self._alert_recipients()
            if recipients:
                send_mail(
                    subject='Youth Sports listing health alert',
                    message=self._build_email_body(results),
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'webmaster@localhost'),
                    recipient_list=recipients,
                    fail_silently=False,
                )
                self.stdout.write(f'Alert email sent to {", ".join(recipients)}')
            else:
                self.stderr.write(
                    'OPS_ALERT_EMAIL not configured; skipping alert email.'
                )

        if options['fail_on_alert'] and has_alerts:
            raise CommandError('Listing health check detected one or more alerts.')

    def _alert_recipients(self):
        raw_recipients = os.environ.get('OPS_ALERT_EMAIL', '').strip()
        if not raw_recipients:
            return []
        return [email.strip() for email in raw_recipients.split(',') if email.strip()]

    def _build_email_body(self, results):
        counts = results['counts']
        thresholds = results['thresholds']
        return (
            'Listing health check found alerts.\n\n'
            f"Checked at: {results['checked_at']}\n"
            f"Stale threshold: {thresholds['stale_days']} days\n"
            f"Old draft threshold: {thresholds['draft_days']} days\n"
            f"Pending suggestion threshold: {thresholds['pending_suggestion_days']} days\n\n"
            f"Stale published listings: {counts['stale_published']}\n"
            f"Unresolved outdated reports: {counts['unresolved_reports']}\n"
            f"Old drafts: {counts['old_drafts']}\n"
            f"Old pending suggestions: {counts['old_pending_suggestions']}\n"
        )
