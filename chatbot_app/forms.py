from django import forms
from .models import FAQ, CompanyInformation, Project, ProductService, PageContent

class FAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ['question', 'answer', 'keywords', 'category']
        widgets = {
            'question': forms.TextInput(attrs={'class': 'form-control'}),
            'answer': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'keywords': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Comma-separated keywords'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CompanyInformationForm(forms.ModelForm):
    class Meta:
        model = CompanyInformation
        fields = ['title', 'content', 'keywords']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'keywords': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Comma-separated keywords'}),
        }

class PageContentForm(forms.ModelForm):
    class Meta:
        model = PageContent
        fields = ['title', 'page_path', 'section', 'content', 'keywords', 'page_category']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'page_path': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '/page/subpage'}),
            'section': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'keywords': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Comma-separated keywords'}),
            'page_category': forms.TextInput(attrs={'class': 'form-control'}),
        } 