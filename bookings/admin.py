from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'hike', 'spots', 'total_price', 'payment_method', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('customer_name', 'hike__title')
    readonly_fields = ('total_price', 'created_at')
    actions = ('confirm_bookings', 'cancel_bookings')

    def _change_status(self, request, queryset, status):
        changed = 0
        for booking in queryset.order_by('pk'):
            try:
                booking.status = status
                booking.save(update_fields=['status'])
            except ValidationError as error:
                self.message_user(request, f'Booking #{booking.pk}: {"; ".join(error.messages)}',
                                  level=messages.ERROR)
            else:
                changed += 1
        if changed:
            self.message_user(request, f'{changed} booking(s) updated.', level=messages.SUCCESS)

    @admin.action(description='Confirm selected bookings', permissions=['change'])
    def confirm_bookings(self, request, queryset):
        self._change_status(request, queryset, Booking.Status.CONFIRMED)

    @admin.action(description='Cancel selected bookings and release spots', permissions=['change'])
    def cancel_bookings(self, request, queryset):
        self._change_status(request, queryset, Booking.Status.CANCELLED)
