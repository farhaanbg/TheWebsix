"""Create or remove an isolated set of local, temporary test records."""
import json
import shutil
from datetime import time, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import UserProfile
from bookings.models import Booking, BookingNotification, BookingParticipant
from hikes.models import Announcement, Guide, Hike, SavedHike


MARKER = '[DEMO]'
PASSWORD = 'TrailDemo!2026'
USERNAMES = ('demo_hiker', 'demo_admin')


class Command(BaseCommand):
    help = 'Add temporary local hikes data, or remove it with --clear.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Remove this command\'s demo data.')

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('This temporary-data command is only available with DEBUG=True.')
        self.directory = Path(settings.MEDIA_ROOT) / 'temporary-hike-demo'
        self.manifest = self.directory / 'manifest.json'
        if options['clear']:
            self.clear()
            return
        if self.manifest.exists():
            self.stdout.write('Demo data already exists. No records changed. Use --clear before reseeding.')
            return
        User = get_user_model()
        if User.objects.filter(username__in=USERNAMES).exists():
            raise CommandError('A demo username already exists without a manifest; existing accounts were left unchanged.')
        if self.directory.exists() and any(self.directory.iterdir()):
            raise CommandError('The demo media folder is not empty. Existing files were left unchanged.')
        with transaction.atomic():
            users = []
            for username in USERNAMES:
                user = User.objects.create_user(username=username, email=f'{username}@example.invalid',
                                                password=PASSWORD, first_name='Demo',
                                                last_name='Hiker' if username == 'demo_hiker' else 'Administrator',
                                                is_staff=username == 'demo_admin')
                UserProfile.objects.create(user=user, handle=username)
                users.append(user)
            hiker, admin = users
            admin.user_permissions.set(Permission.objects.filter(content_type__app_label__in=['hikes', 'bookings']))
            guides = [Guide.objects.create(name=f'{MARKER} Guide {letter}',
                                           biography='Fictional guide for temporary local testing.')
                      for letter in ('A', 'B', 'C')]
            self.directory.mkdir(parents=True, exist_ok=True)
            files = []
            for source, name in [('hikes/static/hikes/images/trail-banner.jpg', 'valley.jpg'),
                                 ('home/static/home/images/hero.png', 'landscape.png')]:
                shutil.copyfile(Path(settings.BASE_DIR) / source, self.directory / name)
                files.append(name)
            specs = [
                ('Free Intro Trail', 2, 'easy', 0, 8, 'Chamarel', 'Black River'),
                ('Tamarin Falls', 3, 'moderate', 300, 12, 'Henrietta', 'Plaines Wilhems'),
                ('Le Morne Summit - Fully Booked', 5, 'hard', 500, 4, 'Le Morne', 'Black River'),
                ('Black River Peak', 8, 'expert', 650, 10, 'Black River', 'Black River'),
                ('Coastal Walk - Postponed', 10, 'easy', 200, 10, 'Gris Gris', 'Savanne'),
                ('Forest Trail - Cancelled', 12, 'moderate', 350, 8, 'Plaine Champagne', 'Black River'),
                ('Past Nature Walk', -7, 'easy', 150, 10, 'Curepipe', 'Plaines Wilhems'),
            ]
            hikes = []
            for index, (title, days, difficulty, price, capacity, location, district) in enumerate(specs):
                hike = Hike.objects.create(
                    title=f'{MARKER} {title}', location=location, district=district,
                    date=timezone.localdate() + timedelta(days=days), departure_time=time(8),
                    difficulty=difficulty, price=price, capacity=capacity, distance_km=5 + index,
                    elevation_m=100 + index * 50, duration_minutes=120 + index * 20,
                    description=f'{MARKER} Temporary dummy event for local testing, not a real advertised hike.',
                    tags='Demo, Temporary', image=f'temporary-hike-demo/{files[index % len(files)]}',
                )
                hike.guides.add(guides[index % 3])
                if index in (1, 3):
                    hike.guides.add(guides[(index + 1) % 3])
                hike.publish()
                hikes.append(hike)

            def reserve(hike, spots, status=Booking.Status.PENDING):
                booking = Booking.objects.create(user=hiker, hike=hike, customer_name='Demo Hiker',
                                                 spots=spots, payment_method=Booking.PaymentMethod.CASH,
                                                 status=status)
                for index in range(spots):
                    BookingParticipant.objects.create(booking=booking, full_name=f'Demo Participant {index + 1}',
                                                      contact_number='00000000')
                return booking

            reserve(hikes[1], 2)
            reserve(hikes[2], 4, Booking.Status.CONFIRMED)
            reserve(hikes[3], 1, Booking.Status.CONFIRMED)
            reserve(hikes[4], 2)
            hikes[4].postpone(hikes[4].date + timedelta(days=2), time(9),
                              f'{MARKER} Sample schedule change to test customer notifications.', actor=admin)
            reserve(hikes[5], 3)
            hikes[5].cancel(f'{MARKER} Sample weather cancellation.', actor=admin)
            reserve(hikes[6], 1, Booking.Status.CANCELLED)
            draft = Hike.objects.create(title=f'{MARKER} Incomplete Draft Trail', location='Chamarel',
                                         date=timezone.localdate() + timedelta(days=9), difficulty='easy',
                                         price=250, capacity=10, distance_km=4, duration_minutes=90,
                                         description=f'{MARKER} Intentionally missing guides and departure time.')
            hikes.append(draft)
            for hike in (hikes[0], hikes[3], hikes[4]):
                SavedHike.objects.create(user=hiker, hike=hike)
            announcements = [
                Announcement.objects.create(title=f'{MARKER} General trail preparation',
                    body='Temporary sample announcement: bring water and suitable shoes.', is_published=True),
                Announcement.objects.create(title=f'{MARKER} Tamarin meeting point', hike=hikes[1],
                    body='Temporary sample meeting instructions for this hike.', is_published=True),
                Announcement.objects.create(title=f'{MARKER} Unpublished announcement',
                    body='This draft should only appear in admin.', is_published=False),
            ]
            registry = dict(version=1, users={u.username: u.pk for u in users},
                            hikes=[h.pk for h in hikes], guides=[g.pk for g in guides],
                            announcements=[a.pk for a in announcements], files=files)
            self.manifest.write_text(json.dumps(registry, indent=2), encoding='utf-8')
        self.stdout.write(self.style.SUCCESS('Added 8 demo hikes, 3 guides, 6 bookings, 3 saved hikes, 3 announcements and 2 notifications.'))
        self.stdout.write(f'Customer: demo_hiker | Admin: demo_admin | Password for both: {PASSWORD}')
        self.stdout.write('Remove the temporary data later: python manage.py hike_demo --clear')

    def clear(self):
        if not self.manifest.exists():
            self.stdout.write('No demo manifest found. No records changed.')
            return
        data = json.loads(self.manifest.read_text(encoding='utf-8'))
        if data.get('version') != 1 or set(data.get('users', {})) != set(USERNAMES):
            raise CommandError('The demo manifest is not recognised. Cleanup stopped without changing records.')
        User = get_user_model()
        with transaction.atomic():
            if Hike.objects.filter(pk__in=data['hikes']).exclude(title__startswith=MARKER).exists():
                raise CommandError('A tracked hike no longer has its demo label. Cleanup stopped for review.')
            for username, pk in data['users'].items():
                if User.objects.filter(pk=pk).exclude(username=username).exists():
                    raise CommandError('A tracked account was renamed. Cleanup stopped for review.')
            user_ids = list(data['users'].values())
            bookings = Booking.objects.filter(Q(hike_id__in=data['hikes']) | Q(user_id__in=user_ids))
            BookingNotification.objects.filter(Q(booking__in=bookings) | Q(user_id__in=user_ids)
                                               | Q(change__hike_id__in=data['hikes'])).delete()
            bookings.delete()
            Hike.objects.filter(pk__in=data['hikes']).delete()
            Announcement.objects.filter(pk__in=data['announcements'], title__startswith=MARKER).delete()
            Guide.objects.filter(pk__in=data['guides'], name__startswith=MARKER, hikes__isnull=True).delete()
            User.objects.filter(pk__in=user_ids, username__in=USERNAMES).delete()
        # Delete only the two copied assets; never uploaded images or unrelated files.
        for name in data['files']:
            if name not in ('valley.jpg', 'landscape.png'):
                continue
            if not Hike.objects.filter(image=f'temporary-hike-demo/{name}').exists():
                (self.directory / name).unlink(missing_ok=True)
        self.manifest.unlink()
        if not any(self.directory.iterdir()):
            self.directory.rmdir()
        self.stdout.write(self.style.SUCCESS('Temporary demo records removed. Other records were preserved.'))
