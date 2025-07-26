from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('', views.daily_tasks, name='daily_tasks'),
    path('update-task-status/<int:task_id>/', views.update_task_status, name='update_task_status'),

    path('completed/', views.completed_tasks, name='completed_tasks'),
    path('completed/edit/<int:task_id>/', views.edit_completed_task, name='edit_completed_task'),

    path('recycle-bin/', views.recycle_bin, name='recycle_bin'),

    path('export/pdf/', views.export_tasks_pdf, name='export_pdf'),

    path('categories/', views.manage_categories, name='manage_categories'),
]