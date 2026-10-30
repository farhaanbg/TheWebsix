from django.db.models import F, Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from django.urls import reverse
from .forms import HikeFilterForm
from .models import Announcement, Guide, Hike, SavedHike


def hike_context(request):
    return {
        'active_class': 'hikes',
        'community_nav': {
            'home': reverse('home'),
            'hikes': reverse('hikes:list'),
            'profile': reverse('accounts:account_detail' if request.user.is_authenticated else 'accounts:login'),
        },
    }

def hike_list(request):
    hikes = Hike.objects.public().prefetch_related('guides')
    if request.GET.get('scope') != 'all':
        hikes = hikes.upcoming()
    # The home dropdown sends difficulty="" for "Any difficulty".
    # The listing checkboxes send no value when nothing is selected.
    # Treat both cases as no difficulty restriction.
    filter_data = request.GET.copy()
    filter_data.setlist(
        "difficulty",
        [
            value
            for value in filter_data.getlist("difficulty")
            if value != ""
        ],
    )

    if not filter_data.get('scope'):
        filter_data['scope'] = 'upcoming'
    form = HikeFilterForm(filter_data, hikes=hikes)
    context = hike_context(request)
    context['has_hikes'] = hikes.exists()
    if form.is_valid():
        filters = form.cleaned_data
        if filters['q']:
            hikes = hikes.filter(Q(title__icontains=filters['q']) | Q(location__icontains=filters['q']) | Q(district__icontains=filters['q']))
        if filters['location']:
            hikes = hikes.filter(location=filters['location'])
        if filters['date']:
            hikes = hikes.filter(date=filters['date'])
        if filters['max_price'] is not None:
            hikes = hikes.filter(price__lte=filters['max_price'])
        if filters['difficulty']:
            hikes = hikes.filter(difficulty__in=filters['difficulty'])
        hikes = hikes.order_by(filters['sort'] or 'date', 'pk')
    else:
        hikes = hikes.none()
    context.update({
        'hikes': hikes, 'form': form,
        'available_count': hikes.exclude(status=Hike.Status.CANCELLED).filter(reserved_spots__lt=F('capacity')).count(),
        'guide_count': Guide.objects.filter(hikes__in=hikes).distinct().count(),
        'district_count': hikes.exclude(district='').values('district').distinct().count(),
    })
    return render(request, 'hikes/list.html', context)


def hike_detail(request, pk):
    context = hike_context(request)
    source = Hike.objects.all() if request.user.is_staff else Hike.objects.public()
    context['hike'] = get_object_or_404(source.prefetch_related('guides', 'photos'), pk=pk)
    hike = context['hike']
    context['gallery'] = ([{'url': hike.image.url, 'caption': hike.title}] if hike.image else []) + [
        {'url': photo.image.url, 'caption': photo.caption or hike.title} for photo in hike.photos.all()
    ]
    context['is_saved'] = request.user.is_authenticated and SavedHike.objects.filter(user=request.user, hike_id=pk).exists()
    context['announcements'] = Announcement.objects.filter(is_published=True).filter(Q(hike_id=pk) | Q(hike__isnull=True))
    context['changes'] = context['hike'].changes.all()[:10]
    return render(request, 'hikes/detail.html', context)


@login_required
def saved_hikes(request):
    context = hike_context(request)
    context['saved_hikes'] = SavedHike.objects.filter(user=request.user).select_related('hike')
    context['visible_ids'] = set(Hike.objects.public().values_list('pk', flat=True))
    return render(request, 'hikes/saved.html', context)


@login_required
@require_POST
def save_hike(request, pk):
    hike = get_object_or_404(Hike.objects.public(), pk=pk)
    SavedHike.objects.get_or_create(user=request.user, hike=hike)
    return redirect('hikes:detail', pk=pk)


@login_required
@require_POST
def remove_saved_hike(request, pk):
    SavedHike.objects.filter(user=request.user, hike_id=pk).delete()
    return redirect('hikes:saved')


def announcements(request):
    context = hike_context(request)
    context['announcements'] = Announcement.objects.filter(is_published=True).filter(
        Q(hike__isnull=True) | Q(hike__in=Hike.objects.public())
    ).select_related('hike')
    return render(request, 'hikes/announcements.html', context)
