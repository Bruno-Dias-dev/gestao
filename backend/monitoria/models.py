from django.conf import settings
from django.db import models
from django.utils import timezone

class Project(models.Model):
    STATUS = [('Planejamento','Planejamento'),('Não iniciado','Não iniciado'),('Em andamento','Em andamento'),('Pausado','Pausado'),('Concluído','Concluído'),('Cancelado','Cancelado')]
    PRIORITY = [('Baixa','Baixa'),('Média','Média'),('Alta','Alta'),('Crítica','Crítica')]
    name = models.CharField('nome', max_length=180)
    description = models.TextField('descrição', blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='projects')
    start_date = models.DateField('data de início', null=True, blank=True)
    due_date = models.DateField('prazo de entrega', null=True, blank=True)
    completed_date = models.DateField('data de conclusão', null=True, blank=True)
    status = models.CharField('status', max_length=30, choices=STATUS, default='Não iniciado')
    priority = models.CharField('prioridade', max_length=20, choices=PRIORITY, default='Média')
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self): return self.name
    @property
    def owner_label(self): return (self.owner.get_full_name() or self.owner.username) if self.owner else 'Sem responsável'
    @property
    def progress(self):
        total = self.tasks.filter(deleted=False).count()
        return round(self.tasks.filter(deleted=False, status='Finalizado').count() * 100 / total) if total else 0

class Task(models.Model):
    STATUS = [('A fazer','A fazer'),('Em andamento','Em andamento'),('Aguardando terceiros','Aguardando terceiros'),('Finalizado','Finalizado'),('Cancelado','Cancelado')]
    PRIORITY = Project.PRIORITY
    title = models.CharField('título', max_length=220)
    description = models.TextField('descrição', blank=True)
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name='tasks')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_tasks')
    priority = models.CharField('prioridade', max_length=20, choices=PRIORITY, default='Média')
    status = models.CharField('status', max_length=30, choices=STATUS, default='A fazer')
    opened_date = models.DateField('data de abertura', default=timezone.localdate)
    start_date = models.DateField('data de início', null=True, blank=True)
    due_date = models.DateField('prazo de entrega', null=True, blank=True)
    completed_date = models.DateField('data de conclusão', null=True, blank=True)
    deleted = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='created_tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self): return self.title
    @property
    def owner_label(self): return (self.owner.get_full_name() or self.owner.username) if self.owner else 'Sem responsável'
    @property
    def overdue(self): return bool(self.due_date and self.due_date < timezone.localdate() and self.status not in ('Finalizado','Cancelado'))
    @property
    def late_completion(self): return bool(self.due_date and self.completed_date and self.completed_date > self.due_date)

class TaskHistory(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='history')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
