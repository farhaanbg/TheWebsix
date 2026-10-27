from io import BytesIO

from django import forms
from django.core.files.base import ContentFile
from django.forms import ModelForm
from PIL import Image, UnidentifiedImageError

from .models import Comment, Post, RATING_CHOICES


class AddReviewForm(forms.Form):
    # Like AddOwnerForm: declare each field explicitly.
    name = forms.CharField(max_length=100, required=True, label='Name',
                           widget=forms.TextInput(attrs={'class': 'da-input'}))
    rating = forms.IntegerField(
        min_value=1, max_value=5, initial=5, required=True, label='Rating',
        widget=forms.RadioSelect(choices=RATING_CHOICES),
    )
    text = forms.CharField(
        max_length=2000, required=True, label='Feedback',
        widget=forms.Textarea(attrs={'class': 'da-input', 'rows': 3}),
    )


class AddPostModelForm(ModelForm):
    # Like AddRenterModelForm: model, fields and widgets belong in class Meta.
    image = forms.ImageField(required=False, label='Your Photo (Optional)', widget=forms.FileInput(attrs={
        'class': 'da-input da-file-input',
        'accept': 'image/jpeg,image/png,image/webp',
    }))

    class Meta:
        model = Post
        # author is intentionally excluded: views.py sets it to request.user.
        fields = ['caption', 'image']
        labels = {'caption': 'Caption', 'image': 'Your Photo (Optional)'}
        widgets = {
            'caption': forms.Textarea(attrs={'class': 'da-input', 'rows': 3}),
            'image': forms.FileInput(attrs={
                'class': 'da-input da-file-input',
                'accept': 'image/jpeg,image/png,image/webp',
            }),
        }

    def clean_image(self):
        # Clean the image field, ensuring it's a valid image file.
        data = self.cleaned_data.get('image')
        if not data:
            return data
        # Existing stored files are not fresh uploads (important for admin edits).
        if not hasattr(data, 'content_type'):
            return data
        if data.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Choose a photo of 5 MB or less.')

        # Additional upload safety from the previous app
        # Check the actual image, then re-encode rather than trusting its filename.
        try:
            data.seek(0)
            with Image.open(data) as photo:
                image_format = photo.format
                if image_format not in ('JPEG', 'PNG', 'WEBP'):
                    raise forms.ValidationError('Use a JPEG, PNG or WebP photo.')
                if photo.width * photo.height > 20_000_000:
                    raise forms.ValidationError('Choose a photo of 20 megapixels or less.')
                photo.load()
                converted = photo.convert('RGB' if image_format == 'JPEG' else 'RGBA')
                output = BytesIO()
                converted.save(output, format=image_format)
                payload = output.getvalue()
                if len(payload) > 5 * 1024 * 1024:
                    raise forms.ValidationError('The processed photo must be 5 MB or less.')
            extension = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}[image_format]
            return ContentFile(payload, name='photo' + extension)
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as error:
            raise forms.ValidationError('The photo could not be read. Choose another image.') from error


class AddCommentModelForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        labels = {'text': 'Comment'}
        widgets = {'text': forms.Textarea(attrs={
            'class': 'da-input', 'rows': 3, 'placeholder': 'Write your comment...',
        })}


class LikePostForm(forms.Form):
    liked = forms.ChoiceField(choices=(('1', 'Like'), ('0', 'Unlike')),
                             widget=forms.HiddenInput)


class DeletePostForm(forms.Form):
    confirm = forms.BooleanField(
        required=True,
        label='I understand that this post, its comments and its likes will be deleted.',
    )


class PostAdminForm(AddPostModelForm):
    # Admin staff can choose an author; the public AddPostModelForm cannot.
    # Inherit clean_image() so admin uploads get the same checks.
    class Meta(AddPostModelForm.Meta):
        fields = ['author', 'caption', 'image']
