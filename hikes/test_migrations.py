from datetime import date, time

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class LegacyGuideMigrationTests(TransactionTestCase):
    def test_legacy_names_and_reservations_survive_and_incomplete_hikes_become_drafts(self):
        old_targets = [('hikes', '0001_initial'), ('bookings', '0002_booking_user')]
        executor = MigrationExecutor(connection)
        executor.migrate(old_targets)
        try:
            apps = executor.loader.project_state(old_targets).apps
            Hike = apps.get_model('hikes', 'Hike')
            fields = dict(location='Chamarel', date=date(2027, 5, 1), difficulty='easy',
                          price=100, distance_km=5, duration_minutes=60, capacity=10,
                          reserved_spots=3, guide='Legacy guide')
            complete = Hike.objects.create(title='Complete old hike', departure_time=time(8), **fields)
            draft = Hike.objects.create(title='Incomplete old hike', **fields)
            executor = MigrationExecutor(connection)
            targets = executor.loader.graph.leaf_nodes()
            executor.migrate(targets)
            apps = executor.loader.project_state(targets).apps
            MigratedHike = apps.get_model('hikes', 'Hike')
            for pk in (complete.pk, draft.pk):
                hike = MigratedHike.objects.get(pk=pk)
                self.assertEqual(list(hike.guides.values_list('name', flat=True)), ['Legacy guide'])
                self.assertEqual(hike.reserved_spots, 3)
            self.assertTrue(MigratedHike.objects.get(pk=complete.pk).is_published)
            self.assertFalse(MigratedHike.objects.get(pk=draft.pk).is_published)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
