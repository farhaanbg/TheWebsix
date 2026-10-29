from django.db.models import F, Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from .forms import HikeFilterForm
from .models import Hike


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
    hikes = Hike.objects.all()
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

    form = HikeFilterForm(filter_data)
    context = hike_context(request)
    context.update({
        'available_count': hikes.filter(reserved_spots__lt=F('capacity')).count(),
        'guide_count': hikes.exclude(guide='').values('guide').distinct().count(),
        'district_count': hikes.exclude(district='').values('district').distinct().count(),
        'has_hikes': hikes.exists(),
    })
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
    context.update({'hikes': hikes, 'form': form})
    return render(request, 'hikes/list.html', context)


def hike_detail(request, pk):
    context = hike_context(request)
    context['hike'] = get_object_or_404(Hike, pk=pk)
    return render(request, 'hikes/detail.html', context)
