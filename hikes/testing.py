from datetime import time
from .models import Guide, Hike


def published_hike(**fields):
    """Create a complete, public hike for application tests."""
    fields.setdefault('departure_time', time(8))
    hike = Hike.objects.create(**fields)
    guide, _ = Guide.objects.get_or_create(name='Test guide')
    hike.guides.add(guide)
    hike.publish()
    return hike
