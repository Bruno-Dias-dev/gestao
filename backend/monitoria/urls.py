from django.urls import path
from . import views

urlpatterns = [
    path('',views.landing,name='home'), path('setup/',views.setup,name='setup'), path('login/',views.login_view,name='login'), path('logout/',views.logout_view,name='logout'),
    path('dashboard/',views.dashboard,name='dashboard'), path('projects/',views.projects,name='projects'), path('projects/new/',views.project_form,name='project_new'), path('projects/<int:pk>/edit/',views.project_form,name='project_edit'), path('projects/<int:pk>/archive/',views.project_archive,name='project_archive'),
    path('tasks/',views.tasks,name='tasks'), path('tasks/new/',views.task_form,name='task_new'), path('tasks/<int:pk>/edit/',views.task_form,name='task_edit'), path('tasks/<int:pk>/status/',views.task_status,name='task_status'), path('tasks/<int:pk>/delete/',views.task_delete,name='task_delete'),
    path('calendar/',views.calendar_view,name='calendar'), path('reports/',views.reports,name='reports'), path('reports/export/',views.report_export,name='report_export'), path('import-txt/',views.import_txt,name='import_txt'),
]
