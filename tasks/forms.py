from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Task, Category


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']


class TaskForm(forms.ModelForm):
    due_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = Task
        fields = ['title', 'due_date', 'is_completed']


class CompletedTaskForm(forms.ModelForm):
    completed_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = Task
        fields = ['title', 'completed_date', 'time_spent', 'reflection', 'category', 'attachment']


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']