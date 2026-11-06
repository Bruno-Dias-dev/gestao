import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
                ('name',models.CharField(max_length=180,verbose_name='nome')),
                ('description',models.TextField(blank=True,verbose_name='descrição')),
                ('start_date',models.DateField(blank=True,null=True,verbose_name='data de início')),
                ('due_date',models.DateField(blank=True,null=True,verbose_name='prazo de entrega')),
                ('completed_date',models.DateField(blank=True,null=True,verbose_name='data de conclusão')),
                ('status',models.CharField(choices=[('Planejamento','Planejamento'),('Não iniciado','Não iniciado'),('Em andamento','Em andamento'),('Pausado','Pausado'),('Concluído','Concluído'),('Cancelado','Cancelado')],default='Não iniciado',max_length=30,verbose_name='status')),
                ('priority',models.CharField(choices=[('Baixa','Baixa'),('Média','Média'),('Alta','Alta'),('Crítica','Crítica')],default='Média',max_length=20,verbose_name='prioridade')),
                ('archived',models.BooleanField(default=False)),
                ('created_at',models.DateTimeField(auto_now_add=True)),
                ('updated_at',models.DateTimeField(auto_now=True)),
                ('owner',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='projects',to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
                ('title',models.CharField(max_length=220,verbose_name='título')),
                ('description',models.TextField(blank=True,verbose_name='descrição')),
                ('priority',models.CharField(choices=[('Baixa','Baixa'),('Média','Média'),('Alta','Alta'),('Crítica','Crítica')],default='Média',max_length=20,verbose_name='prioridade')),
                ('status',models.CharField(choices=[('A fazer','A fazer'),('Em andamento','Em andamento'),('Aguardando terceiros','Aguardando terceiros'),('Finalizado','Finalizado'),('Cancelado','Cancelado')],default='A fazer',max_length=30,verbose_name='status')),
                ('opened_date',models.DateField(default=django.utils.timezone.localdate,verbose_name='data de abertura')),
                ('start_date',models.DateField(blank=True,null=True,verbose_name='data de início')),
                ('due_date',models.DateField(blank=True,null=True,verbose_name='prazo de entrega')),
                ('completed_date',models.DateField(blank=True,null=True,verbose_name='data de conclusão')),
                ('deleted',models.BooleanField(default=False)),
                ('created_at',models.DateTimeField(auto_now_add=True)),
                ('updated_at',models.DateTimeField(auto_now=True)),
                ('created_by',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='created_tasks',to=settings.AUTH_USER_MODEL)),
                ('owner',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='assigned_tasks',to=settings.AUTH_USER_MODEL)),
                ('project',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='tasks',to='monitoria.project')),
            ],
        ),
        migrations.CreateModel(
            name='TaskComment',
            fields=[
                ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
                ('comment',models.TextField()),
                ('created_at',models.DateTimeField(auto_now_add=True)),
                ('task',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='comments',to='monitoria.task')),
                ('user',models.ForeignKey(null=True,on_delete=django.db.models.deletion.SET_NULL,to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='TaskHistory',
            fields=[
                ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
                ('action',models.CharField(max_length=80)),
                ('details',models.TextField(blank=True)),
                ('created_at',models.DateTimeField(auto_now_add=True)),
                ('task',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='history',to='monitoria.task')),
                ('user',models.ForeignKey(null=True,on_delete=django.db.models.deletion.SET_NULL,to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
