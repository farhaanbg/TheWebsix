"""Views adapted from the uploaded classroom application.

ListView / DetailView display records.
Function-based views process GET/POST, cleaned_data, save and redirect.
JavaScript provides responsive interactions.
"""
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.core.files.storage import default_storage
from django.http import (HttpResponseBadRequest, HttpResponseForbidden,
                         HttpResponseRedirect)
from django.shortcuts import get_object_or_404, render, resolve_url
from django.urls import reverse
from django.views import generic
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST
from django.utils.decorators import method_decorator

from .forms import (AddCommentModelForm, AddPostModelForm, AddReviewForm,
                    DeletePostForm, EditPostModelForm, LikePostForm)
from .models import Comment, Post, PostLike, Review

LOGIN_URL = getattr(settings, 'DINA_AROBI_LOGIN_URL', 'accounts:login')


def page_context(request, active_class):
    login_path = resolve_url(LOGIN_URL)
    separator = '&' if '?' in login_path else '?'
    context = {
        'active_class': active_class,
        'base_template': getattr(settings, 'DINA_AROBI_BASE_TEMPLATE', 'base.html'),
        'community_nav': getattr(settings, 'DINA_AROBI_NAV_URLS', {}),
        'login_url': login_path + separator + urlencode({'next': request.get_full_path()}),
    }
    return context


@method_decorator(never_cache, name='dispatch')
class ReviewListView(generic.ListView):
    # Equivalent to HouseListView: model, template, list in the context.
    model = Review
    template_name = 'community/reviews.html'
    context_object_name = 'review_list'

    def get_context_data(self, **kwargs):
        context = super(ReviewListView, self).get_context_data(**kwargs)
        context.update(page_context(self.request, 'reviews'))
        context['num_reviews'] = Review.objects.count()
        # Avg is used by TopHouseListView. Here aggregate returns ONE overall average.
        result = Review.objects.aggregate(average_rating=Avg('rating'))
        context['average_rating'] = result['average_rating'] or 0
        initial_name = ''
        if self.request.user.is_authenticated:
            initial_name = (self.request.user.get_full_name().strip()
                            or self.request.user.get_username())
        context['form'] = AddReviewForm(initial={'name': initial_name, 'rating': 5})
        context['star_values'] = range(1, 6)
        context['selected_rating'] = 5
        return context


@method_decorator(never_cache, name='dispatch')
class PostListView(generic.ListView):
    model = Post
    template_name = 'community/community.html'
    context_object_name = 'post_list'

    def get_queryset(self):
        # Same annotate(...=Count(...)).order_by(...) pattern as MostRentedHouseListView.
        # distinct=True avoids bigger counts when the two joins are combined.
        post_queryset = Post.objects.annotate(
            num_likes=Count('likes', distinct=True),
            num_comments=Count('comments', distinct=True),
        ).order_by('-created_at', '-pk')
        return post_queryset

    def get_context_data(self, **kwargs):
        context = super(PostListView, self).get_context_data(**kwargs)
        context.update(page_context(self.request, 'community'))
        context['post_form'] = AddPostModelForm()
        context['comment_form'] = AddCommentModelForm()
        liked_post_ids = []
        if self.request.user.is_authenticated:
            for like in PostLike.objects.filter(user=self.request.user):
                liked_post_ids.append(like.post_id)
        context['liked_post_ids'] = liked_post_ids
        return context


@method_decorator(never_cache, name='dispatch')
class PostDetailView(generic.DetailView):
    # Like HouseDetailView; pk comes from the URL and the template receives post.
    model = Post
    template_name = 'community/post_detail.html'
    context_object_name = 'post'

    def get_context_data(self, **kwargs):
        context = super(PostDetailView, self).get_context_data(**kwargs)
        context.update(page_context(self.request, 'community'))
        return context


@login_required(login_url=LOGIN_URL)
@require_http_methods(['GET', 'POST'])
def add_review(request):
    # Same sequence as add_owner(): bind, validate, construct, save, redirect.
    if request.method == 'POST':
        form = AddReviewForm(request.POST)
        if form.is_valid():
            review = Review(
                author=request.user,
                name=form.cleaned_data['name'],
                rating=form.cleaned_data['rating'],
                text=form.cleaned_data['text'],
            )
            review.save()
            return HttpResponseRedirect(reverse('community:reviews'))
    else:
        initial_name = request.user.get_full_name().strip() or request.user.get_username()
        form = AddReviewForm(initial={'name': initial_name, 'rating': 5})

    context = page_context(request, 'reviews')
    context['form'] = form
    return render(request, 'community/addreview.html', context)


@login_required(login_url=LOGIN_URL)
@require_http_methods(['GET', 'POST'])
def edit_review(request, pk):
    review = get_object_or_404(Review, pk=pk)
    if review.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden('You may only edit your own reviews.')

    if request.method == 'POST':
        form = AddReviewForm(request.POST)
        if form.is_valid():
            review.name = form.cleaned_data['name']
            review.rating = form.cleaned_data['rating']
            review.text = form.cleaned_data['text']
            review.save(update_fields=['name', 'rating', 'text'])
            return HttpResponseRedirect(reverse('community:reviews'))
    else:
        form = AddReviewForm(instance=review)

    context = page_context(request, 'reviews')
    context['form'] = form
    context['review'] = review
    return render(request, 'community/editreview.html', context)


@login_required(login_url=LOGIN_URL)
@require_http_methods(['GET', 'POST'])
def delete_review(request, pk):
    review = get_object_or_404(Review, pk=pk)
    if review.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden('You may only delete your own reviews.')

    if request.method == 'POST':
        review.delete()
        return HttpResponseRedirect(reverse('community:reviews'))

    context = page_context(request, 'reviews')
    context['review'] = review
    return render(request, 'community/deletereview.html', context)


@login_required(login_url=LOGIN_URL)
@require_http_methods(['GET', 'POST'])
def add_post(request):
    # Same explicit object creation as add_renter(); no form.save(commit=False).
    if request.method == 'POST':
        form = AddPostModelForm(request.POST, request.FILES)
        if form.is_valid():
            post = Post(author=request.user,
                        caption=form.cleaned_data['caption'],
                        image=form.cleaned_data['image'])
            post.save()
            return HttpResponseRedirect(reverse('community:community'))
    else:
        form = AddPostModelForm()

    context = page_context(request, 'community')
    context['form'] = form
    return render(request, 'community/addpost.html', context)


@login_required(login_url=LOGIN_URL)
@require_http_methods(['GET', 'POST'])
def edit_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden('You may only edit your own posts.')

    if request.method == 'POST':
        form = EditPostModelForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            old_image_name = post.image.name
            updated_post = form.save(commit=False)
            if form.cleaned_data['remove_image']:
                updated_post.image.delete(save=False)
                updated_post.image = ''
            updated_post.save()
            if old_image_name and old_image_name != updated_post.image.name:
                default_storage.delete(old_image_name)
            return HttpResponseRedirect(post.get_absolute_url())
    else:
        form = EditPostModelForm(instance=post)

    context = page_context(request, 'community')
    context['form'] = form
    context['post'] = post
    return render(request, 'community/editpost.html', context)


@login_required(login_url=LOGIN_URL)
@require_http_methods(['GET', 'POST'])
def add_comment(request, pk):
    # The post comes from the URL, not an editable hidden author/post field.
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        form = AddCommentModelForm(request.POST)
        if form.is_valid():
            comment = Comment(post=post, author=request.user,
                              text=form.cleaned_data['text'])
            comment.save()
            if request.POST.get('next') == 'community':
                return HttpResponseRedirect(reverse('community:community'))
            return HttpResponseRedirect(post.get_absolute_url())
    else:
        form = AddCommentModelForm()

    context = page_context(request, 'community')
    context['post'] = post
    context['form'] = form
    return render(request, 'community/addcomment.html', context)


@login_required(login_url=LOGIN_URL)
@require_POST
def like_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    form = LikePostForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest('Choose either like or unlike.')
    if form.cleaned_data['liked'] == '1':
        # Writes the intermediate model, just as a rental writes the Rental model.
        # get_or_create plus the unique constraint makes repeated submissions safe.
        PostLike.objects.get_or_create(post=post, user=request.user)
    else:
        PostLike.objects.filter(post=post, user=request.user).delete()
    if request.POST.get('next') == 'detail':
        return HttpResponseRedirect(post.get_absolute_url())
    return HttpResponseRedirect(reverse('community:community'))


@login_required(login_url=LOGIN_URL)
@require_http_methods(['GET', 'POST'])
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden('You may only delete your own posts.')

    if request.method == 'POST':
        form = DeletePostForm(request.POST)
        if form.is_valid():
            post.delete()
            return HttpResponseRedirect(reverse('community:community'))
    else:
        form = DeletePostForm()

    context = page_context(request, 'community')
    context['post'] = post
    context['form'] = form
    return render(request, 'community/deletepost.html', context)


class CommunityLoginView(generic.RedirectView):
    """Keep older sign-in links working through the shared accounts login."""

    pattern_name = 'accounts:login'
    query_string = True
    permanent = False
