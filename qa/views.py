"""Q&A views.

Request flow:  URL (qa/urls.py)  ->  view (this file)  ->  model / form  ->  template (qa/qa.html)
"""
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import generic
from django.views.decorators.http import require_POST

# Re-use the community app's helper so the shared navbar works on this page too.
from community.views import LOGIN_URL, page_context

from .forms import AskQuestionModelForm, DeleteQuestionForm
from .models import Question

SHOW_CHOICES = ('all', 'answered', 'unanswered')


class QuestionListView(generic.ListView):
    """READ: everyone (visitors included) can see the Q&A page. FR 1.15, 2.52, 2.54, 2.55."""
    model = Question
    template_name = 'qa/qa.html'
    context_object_name = 'question_list'

    def get_queryset(self):
        # Hidden questions never reach the page.
        questions = Question.objects.filter(is_visible=True).select_related('author', 'answered_by')

        search = self.request.GET.get('q', '').strip()
        if search:
            questions = questions.filter(
                Q(title__icontains=search) | Q(details__icontains=search) | Q(answer__icontains=search)
            )

        category = self.request.GET.get('category', '')
        if category in Question.Category.values:
            questions = questions.filter(category=category)

        show = self.request.GET.get('show', 'all')
        if show == 'answered':
            questions = questions.exclude(answer='')
        elif show == 'unanswered':
            questions = questions.filter(answer='')
        return questions

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(page_context(self.request, 'qa'))
        visible = Question.objects.filter(is_visible=True)
        context['total_questions'] = visible.count()
        context['answered_count'] = visible.exclude(answer='').count()
        context['categories'] = Question.Category.choices
        context['search'] = self.request.GET.get('q', '').strip()
        context['selected_category'] = self.request.GET.get('category', '')
        context['show'] = self.request.GET.get('show', 'all')
        if context['show'] not in SHOW_CHOICES:
            context['show'] = 'all'
        # A form that was sent back with errors is passed in by ask_question().
        context.setdefault('form', AskQuestionModelForm())
        context['delete_form'] = DeleteQuestionForm()
        return context


@login_required(login_url=LOGIN_URL)
@require_POST
def ask_question(request):
    """CREATE: only logged-in users can ask. FR 2.53."""
    form = AskQuestionModelForm(request.POST, user=request.user)
    if form.is_valid():
        question = form.save(commit=False)   # build the object, don't save yet
        question.author = request.user       # set the owner on the server
        question.save()
        return HttpResponseRedirect(reverse('qa:list') + '?asked=1#question-' + str(question.id))

    # Invalid: show the same page again with the errors and the user's text kept.
    view = QuestionListView()
    view.setup(request)
    view.object_list = view.get_queryset()
    context = view.get_context_data(form=form)
    return render(request, 'qa/qa.html', context, status=400)


@login_required(login_url=LOGIN_URL)
@require_POST
def delete_question(request, pk):
    """DELETE: a user can delete ONLY their own question (FR 3.52).

    Filtering by author=request.user means someone else's question
    simply "does not exist" for this user, so they get a 404.
    """
    question = get_object_or_404(Question, pk=pk, author=request.user)
    question.delete()
    return HttpResponseRedirect(reverse('qa:list'))
