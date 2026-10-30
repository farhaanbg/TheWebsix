from datetime import timedelta
from io import BytesIO

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import inlineformset_factory
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .admin import HikePhotoInline
from .models import Hike, HikePhoto
from .testing import published_hike


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class HikeGalleryTests(TestCase):
    def setUp(self):
        self.hike = published_hike(title='Gallery trail', location='Chamarel',
            date=timezone.localdate() + timedelta(days=7), difficulty='easy', price=200,
            distance_km=8, duration_minutes=120, capacity=10)

    def photo(self, name):
        output = BytesIO()
        Image.new('RGB', (20, 10), 'green').save(output, format='PNG')
        return SimpleUploadedFile(name, output.getvalue(), content_type='image/png')

    def test_cover_is_preserved_and_additional_photos_are_ordered(self):
        self.hike.image = self.photo('cover.png')
        self.hike.save()
        later = HikePhoto.objects.create(hike=self.hike, image=self.photo('later.png'), position=2)
        first = HikePhoto.objects.create(hike=self.hike, image=self.photo('first.png'),
                                         position=1, caption='River <view>')
        response = self.client.get(self.hike.get_absolute_url())
        self.assertEqual([p['url'] for p in response.context['gallery']],
                         [self.hike.image.url, first.image.url, later.image.url])
        self.assertContains(response, 'River &lt;view&gt;')
        self.assertContains(response, 'data-gallery-photo', count=3)

    def test_empty_and_single_photo_states(self):
        self.assertContains(self.client.get(self.hike.get_absolute_url()), 'Trail photos coming soon')
        photo = HikePhoto.objects.create(hike=self.hike, image=self.photo('only.png'))
        response = self.client.get(self.hike.get_absolute_url())
        self.assertEqual(response.context['gallery'][0]['url'], photo.image.url)
        self.assertNotContains(response, 'data-gallery-photo')
        self.assertNotContains(response, 'Trail photos coming soon')

    def test_optional_details_are_escaped_and_empty_lines_ignored(self):
        self.hike.highlights = 'River views\n\n<script>example</script>'
        self.hike.what_to_bring = 'Water\nWalking shoes'
        self.hike.meeting_point = 'Meet at the entrance'
        self.hike.save()
        response = self.client.get(self.hike.get_absolute_url())
        self.assertContains(response, '&lt;script&gt;example&lt;/script&gt;')
        self.assertContains(response, 'Walking shoes')
        self.assertContains(response, 'Meet at the entrance')
        self.hike.is_published = False
        self.hike.save()
        self.assertEqual(self.client.get(self.hike.get_absolute_url()).status_code, 404)

    def test_admin_can_upload_multiple_photos_and_remove_one(self):
        user = get_user_model().objects.create_superuser(username='gallery-admin')
        self.client.force_login(user)
        data = dict(title=self.hike.title, location=self.hike.location, date=self.hike.date,
            difficulty='easy', price='200', distance_km='8', duration_minutes='120',
            capacity='10', elevation_m='0', departure_time='08:00', status='scheduled',
            is_published='on', guides=[self.hike.guides.first().pk],
            **{'photos-TOTAL_FORMS': '2', 'photos-INITIAL_FORMS': '0',
               'photos-0-image': self.photo('one.png'), 'photos-0-position': '0',
               'photos-1-image': self.photo('two.png'), 'photos-1-position': '1',
               'changes-TOTAL_FORMS': '0', 'changes-INITIAL_FORMS': '0'})
        response = self.client.post(reverse('admin:hikes_hike_change', args=[self.hike.pk]), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.hike.photos.count(), 2)
        one, two = self.hike.photos.all()
        for key in ['photos-0-image', 'photos-1-image']:
            data.pop(key)
        data.update({'photos-INITIAL_FORMS': '2', 'photos-0-id': one.pk,
                     'photos-1-id': two.pk, 'photos-0-DELETE': 'on'})
        self.assertEqual(self.client.post(reverse('admin:hikes_hike_change', args=[self.hike.pk]), data).status_code, 302)
        self.assertEqual(list(self.hike.photos.values_list('pk', flat=True)), [two.pk])

    def test_gallery_upload_rejects_non_images(self):
        FormSet = inlineformset_factory(Hike, HikePhoto, fields=HikePhotoInline.fields, extra=1)
        formset = FormSet(data={'photos-TOTAL_FORMS': '1', 'photos-INITIAL_FORMS': '0',
                                'photos-0-position': '0'},
                         files={'photos-0-image': SimpleUploadedFile('bad.png', b'not an image')},
                         instance=self.hike)
        self.assertFalse(formset.is_valid())
        self.assertIn('image', formset.errors[0])
