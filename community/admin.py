from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .forms import PostAdminForm
from .models import Comment, Post, PostLike, Review


class ReviewAdmin(admin.ModelAdmin):
    # Like OwnerAdmin: columns shown in the change-list page.
    list_display = ('name', 'rating', 'author', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('name', 'text')
    readonly_fields = ('created_at',)



admin.site.register(Review, ReviewAdmin)


class CommentsInstanceInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('created_at',)


class LikesInstanceInline(admin.TabularInline):
    # Same technique as RentalsInstanceInline(model=Rental).
    model = PostLike
    extra = 0
    readonly_fields = ('created_at',)



@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm
    list_display = ('id', 'author', 'caption', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('caption',)
    readonly_fields = ('created_at',)
    inlines = [CommentsInstanceInline, LikesInstanceInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'author', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('text',)
    readonly_fields = ('created_at',)


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'created_at')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)
