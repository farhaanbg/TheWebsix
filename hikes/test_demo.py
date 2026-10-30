import tempfile
import json
from datetime import timedelta
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from bookings.models import Booking, BookingNotification
from .models import Announcement, Guide, Hike, SavedHike
from .testing import published_hike


@override_settings(DEBUG=True)
class HikeDemoTests(TestCase):
    def setUp(self):
        test_root = (Path(settings.BASE_DIR) / 'media').resolve()
        test_root.mkdir(exist_ok=True)
        self.files = tempfile.TemporaryDirectory(prefix='demo-test-', dir=test_root)
        self.assertTrue(Path(self.files.name).resolve().is_relative_to(test_root))
        self.settings_override = override_settings(MEDIA_ROOT=self.files.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.files.cleanup)

    def command(self, *args):
        call_command('hike_demo', *args, stdout=StringIO())

    def test_seed_has_complete_scenarios_and_repeated_run_is_unchanged(self):
        self.command()
        self.assertEqual(Hike.objects.count(), 8)
        self.assertEqual(Hike.objects.public().count(), 7)
        self.assertEqual(Guide.objects.count(), 3)
        self.assertEqual(Booking.objects.count(), 6)
        self.assertEqual(BookingNotification.objects.count(), 2)
        self.assertEqual(SavedHike.objects.count(), 3)
        self.assertEqual(Announcement.objects.count(), 3)
        full = Hike.objects.get(title__contains='Fully Booked')
        self.assertEqual(full.spots_remaining, 0)
        self.assertTrue(Hike.objects.filter(status='cancelled', reserved_spots=0).exists())
        self.assertTrue(Hike.objects.filter(status='postponed').exists())
        for hike in Hike.objects.all():
            self.assertEqual(hike.reserved_spots, sum(b.spots for b in hike.bookings.exclude(status='cancelled')))
        admin = get_user_model().objects.get(username='demo_admin')
        self.assertTrue(admin.check_password('TrailDemo!2026'))
        self.assertTrue(admin.has_perm('hikes.change_hike'))
        self.assertFalse(admin.is_superuser)
        self.assertFalse(admin.has_perm('auth.change_user'))
        self.command()
        self.assertEqual(Hike.objects.count(), 8)
        self.assertEqual(Booking.objects.count(), 6)

    def test_cleanup_preserves_real_records_and_releases_demo_users_real_reservation(self):
        real_user = get_user_model().objects.create_user(username='original-user')
        real_hike = published_hike(title='Original hike', location='Chamarel',
                                   date=timezone.localdate() + timedelta(days=7), difficulty='easy',
                                   price=100, capacity=10, reserved_spots=3,
                                   distance_km=5, duration_minutes=90)
        original = Booking.objects.create(user=real_user, hike=real_hike, customer_name='Original Hiker',
                                           spots=2, payment_method='cash')
        real_notice = Announcement.objects.create(title='Original announcement', body='Keep this')
        unrelated_file = Path(self.files.name) / 'keep.txt'
        unrelated_file.write_text('Keep this', encoding='utf-8')
        self.command()
        demo_user = get_user_model().objects.get(username='demo_hiker')
        Booking.objects.create(user=demo_user, hike=real_hike, customer_name='Demo Hiker', spots=1, payment_method='cash')
        self.command('--clear')
        real_hike.refresh_from_db()
        self.assertEqual(real_hike.reserved_spots, 5)
        self.assertTrue(Booking.objects.filter(pk=original.pk).exists())
        self.assertTrue(Announcement.objects.filter(pk=real_notice.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=real_user.pk).exists())
        self.assertFalse(get_user_model().objects.filter(username__startswith='demo_').exists())
        self.assertFalse(Hike.objects.filter(title__startswith='[DEMO]').exists())
        self.assertEqual(unrelated_file.read_text(encoding='utf-8'), 'Keep this')
        self.assertFalse((Path(self.files.name) / 'temporary-hike-demo').exists())
        self.command('--clear')
        self.assertEqual(Hike.objects.count(), 1)

    def test_existing_username_is_never_reused_or_overwritten(self):
        user = get_user_model().objects.create_user(username='demo_hiker', first_name='Original')
        with self.assertRaises(CommandError):
            self.command()
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Original')
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertFalse(Hike.objects.exists())

    def test_cleanup_stops_if_tracked_record_loses_demo_label(self):
        self.command()
        hike = Hike.objects.first()
        hike.title = 'Unmarked hike'
        hike.save(update_fields=['title'])
        with self.assertRaises(CommandError):
            self.command('--clear')
        self.assertEqual(Hike.objects.count(), 8)
        self.assertEqual(Booking.objects.count(), 6)

    def test_cleanup_rejects_a_manifest_with_unrecognised_accounts(self):
        self.command()
        manifest = Path(self.files.name) / 'temporary-hike-demo' / 'manifest.json'
        data = json.loads(manifest.read_text(encoding='utf-8'))
        data['users']['unrelated-user'] = 99999
        manifest.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaises(CommandError):
            self.command('--clear')
        self.assertEqual(Hike.objects.count(), 8)
        self.assertEqual(Booking.objects.count(), 6)

    @override_settings(DEBUG=False)
    def test_command_is_disabled_outside_local_debug_mode(self):
        with self.assertRaises(CommandError):
            self.command()
        self.assertFalse(Hike.objects.exists())
