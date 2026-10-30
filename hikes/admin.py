from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.template.response import TemplateResponse
from .forms import HikeAdminForm, PostponeHikesForm
from .models import Announcement, Guide, Hike, HikeChange, HikePhoto, SavedHike


class HikePhotoInline(admin.TabularInline):
    model = HikePhoto
    extra = 1
    fields = ('image', 'caption', 'position')


class HikeChangeInline(admin.TabularInline):
    model = HikeChange
    extra = 0
    can_delete = False
    fields = ('old_date', 'old_departure_time', 'new_date', 'new_departure_time',
              'old_status', 'new_status', 'reason', 'changed_by', 'created_at')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Hike)
class HikeAdmin(admin.ModelAdmin):
    form = HikeAdminForm
    readonly_fields = ('reserved_spots',)
    list_display = ('title', 'date', 'status', 'is_published', 'location', 'difficulty', 'price', 'capacity', 'reserved_spots')
    list_filter = ('status', 'is_published', 'difficulty', 'date', 'district', 'location')
    search_fields = ('title', 'location', 'district', 'guides__name')
    filter_horizontal = ('guides',)
    inlines = (HikePhotoInline, HikeChangeInline)
    actions = ('cancel_hikes', 'postpone_hikes', 'publish_hikes')
    date_hierarchy = 'date'

    def get_inlines(self, request, obj=None):
        return self.inlines if obj else (HikePhotoInline,)

    def save_model(self, request, obj, form, change):
        obj._changed_by = request.user
        if change:
            # Capacity accounting owns this column, even if the admin form
            # loaded before a concurrent reservation changed its value.
            fields = [field.name for field in obj._meta.concrete_fields
                      if not field.primary_key and field.name != 'reserved_spots']
            obj.save(update_fields=fields)
        else:
            super().save_model(request, obj, form, change)

    @admin.action(description='Cancel selected hikes and their active bookings', permissions=['change'])
    def cancel_hikes(self, request, queryset):
        for hike in queryset.order_by('pk'):
            hike.cancel(reason='Cancelled by the hiking team.', actor=request.user)
        self.message_user(request, 'Selected hikes cancelled. Customers have in-app notifications.')

    @admin.action(description='Publish selected complete hikes', permissions=['change'])
    def publish_hikes(self, request, queryset):
        for hike in queryset:
            try:
                hike.publish()
            except ValidationError as error:
                self.message_user(request, f'{hike.title}: {"; ".join(error.messages)}', messages.ERROR)

    @admin.action(description='Postpone selected hikes to a new schedule', permissions=['change'])
    def postpone_hikes(self, request, queryset):
        form = PostponeHikesForm(request.POST if 'apply' in request.POST else None)
        if 'apply' in request.POST and form.is_valid():
            for hike in queryset.order_by('pk'):
                try:
                    hike.postpone(actor=request.user, **form.cleaned_data)
                except ValidationError as error:
                    self.message_user(request, f'{hike.title}: {"; ".join(error.messages)}', messages.ERROR)
            self.message_user(request, 'Schedule changes saved. Customers have in-app notifications.')
            return None
        return TemplateResponse(request, 'admin/hikes/postpone.html', {
            **self.admin_site.each_context(request), 'title': 'Postpone hikes',
            'form': form, 'hikes': queryset, 'opts': self.model._meta,
        })


@admin.register(Guide)
class GuideAdmin(admin.ModelAdmin):
    search_fields = ('name',)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'hike', 'is_published', 'created_at')
    list_filter = ('is_published', 'hike')
    search_fields = ('title', 'body')


@admin.register(SavedHike)
class SavedHikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'hike', 'created_at')
    readonly_fields = ('created_at',)
