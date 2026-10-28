from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from hikes.views import home

urlpatterns = [
    path('', home, name='home'),
    path('hikes/', include('hikes.urls')),
    path('admin/', admin.site.urls),

    # Registration, login and profiles
    path('accounts/', include('accounts.urls')),

    # Community and reviews
    path('', include('community.urls')),
]

# Serve uploaded media during local development.
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
