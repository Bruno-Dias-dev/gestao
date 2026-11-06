from django.contrib import admin
from .models import Project, Task, TaskComment, TaskHistory

admin.site.register(Project)
admin.site.register(Task)
admin.site.register(TaskHistory)
admin.site.register(TaskComment)
