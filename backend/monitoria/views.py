import calendar
from datetime import date, datetime, timedelta
from io import BytesIO

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import Workbook

from .forms import ImportTextForm, ProjectForm, TaskForm
from .importer import parse_text
from .models import Project, Task, TaskComment, TaskHistory

def landing(request):
    if not User.objects.exists(): return redirect('setup')
    return redirect('dashboard' if request.user.is_authenticated else 'login')

def setup(request):
    if User.objects.exists(): return redirect('login')
    if request.method=='POST':
        name=request.POST.get('name','').strip(); email=request.POST.get('email','').strip().lower(); password=request.POST.get('password','')
        if not name or '@' not in email or len(password)<8:
            messages.error(request,'Informe nome, e-mail válido e senha com pelo menos 8 caracteres.')
        elif User.objects.filter(username=email).exists():
            messages.error(request,'Este e-mail já está cadastrado.')
        else:
            user=User.objects.create_user(username=email,email=email,first_name=name,password=password,is_staff=True,is_superuser=True)
            login(request,user); return redirect('dashboard')
    return render(request,'monitoria/setup.html')

def login_view(request):
    if not User.objects.exists(): return redirect('setup')
    if request.user.is_authenticated: return redirect('dashboard')
    if request.method=='POST':
        email=request.POST.get('email','').strip().lower(); password=request.POST.get('password','')
        user=authenticate(request,username=email,password=password)
        if user: login(request,user); return redirect(request.GET.get('next') or 'dashboard')
        messages.error(request,'E-mail ou senha inválidos.')
    return render(request,'monitoria/login.html')

@require_POST
def logout_view(request):
    logout(request); return redirect('login')

@login_required
def dashboard(request):
    tasks=Task.objects.filter(deleted=False); today=timezone.localdate()
    cards={'total':tasks.count(),'a_fazer':tasks.filter(status='A fazer').count(),'andamento':tasks.filter(status='Em andamento').count(),'aguardando':tasks.filter(status='Aguardando terceiros').count(),'finalizadas':tasks.filter(status='Finalizado').count(),'atrasadas':tasks.filter(due_date__lt=today).exclude(status__in=['Finalizado','Cancelado']).count()}
    projects=Project.objects.filter(archived=False,status='Em andamento').annotate(task_count=Count('tasks',filter=Q(tasks__deleted=False),distinct=True),done_count=Count('tasks',filter=Q(tasks__deleted=False,tasks__status='Finalizado'),distinct=True)).order_by('-updated_at')[:6]
    upcoming=tasks.filter(due_date__gte=today).exclude(status__in=['Finalizado','Cancelado']).select_related('project').order_by('due_date')[:6]
    recent=tasks.select_related('project').order_by('-updated_at')[:6]
    status_data=[{'label':label,'value':tasks.filter(status=value).count()} for value,label in Task.STATUS]
    month_labels=[]; month_values=[]
    for offset in range(5,-1,-1):
        month_index=today.year*12+today.month-1-offset
        month=date(month_index//12,month_index%12+1,1)
        next_month=(month.replace(day=28)+timedelta(days=4)).replace(day=1)
        month_labels.append(month.strftime('%b %Y')); month_values.append(tasks.filter(status='Finalizado',completed_date__gte=month,completed_date__lt=next_month).count())
    return render(request,'monitoria/dashboard.html',{'cards':cards,'projects':projects,'upcoming':upcoming,'recent':recent,'status_data':status_data,'month_labels':month_labels,'month_values':month_values,'active':'dashboard','project_count':Project.objects.filter(archived=False,status='Em andamento').count()})

@login_required
def projects(request):
    rows=Project.objects.filter(archived=False).select_related('owner').annotate(task_count=Count('tasks',filter=Q(tasks__deleted=False))).order_by('-updated_at')
    query=request.GET.get('q','').strip(); status=request.GET.get('status','')
    if query: rows=rows.filter(name__icontains=query)
    if status: rows=rows.filter(status=status)
    return render(request,'monitoria/projects.html',{'projects':rows,'statuses':Project.STATUS,'active':'projects','query':query,'selected_status':status})

@login_required
def project_form(request,pk=None):
    instance=get_object_or_404(Project,pk=pk,archived=False) if pk else None
    form=ProjectForm(request.POST or None,instance=instance)
    if request.method=='POST' and form.is_valid():
        project=form.save(); messages.success(request,'Projeto salvo.'); return redirect('projects')
    return render(request,'monitoria/project_form.html',{'form':form,'project':instance,'active':'projects'})

@login_required
@require_POST
def project_archive(request,pk):
    project=get_object_or_404(Project,pk=pk); project.archived=True; project.save(update_fields=['archived','updated_at']); messages.success(request,'Projeto arquivado.'); return redirect('projects')

def filtered_tasks(request):
    rows=Task.objects.filter(deleted=False).select_related('project','owner')
    if request.GET.get('q'): rows=rows.filter(Q(title__icontains=request.GET['q'])|Q(description__icontains=request.GET['q']))
    for key,field in [('status','status'),('project','project_id'),('owner','owner_id')]:
        if request.GET.get(key): rows=rows.filter(**{field:request.GET[key]})
    return rows.order_by('due_date','-updated_at')

@login_required
def tasks(request):
    return render(request,'monitoria/tasks.html',{'tasks':filtered_tasks(request),'projects':Project.objects.filter(archived=False),'users':User.objects.filter(is_active=True),'statuses':Task.STATUS,'active':'tasks','filters':request.GET})

@login_required
def task_form(request,pk=None):
    instance=get_object_or_404(Task,pk=pk,deleted=False) if pk else None
    prior_status=instance.status if instance else None
    form=TaskForm(request.POST or None,instance=instance)
    if request.method=='POST' and request.POST.get('action')=='comment' and instance:
        comment=request.POST.get('comment','').strip()
        if comment: TaskComment.objects.create(task=instance,user=request.user,comment=comment)
        return redirect('task_edit',pk=instance.pk)
    if request.method=='POST' and form.is_valid():
        task=form.save(commit=False); task.created_by=task.created_by or request.user
        if task.status=='Em andamento' and not task.start_date: task.start_date=timezone.localdate()
        if task.status=='Finalizado' and prior_status!='Finalizado': task.completed_date=timezone.localdate()
        elif task.status!='Finalizado' and prior_status=='Finalizado': task.completed_date=None
        task.save(); TaskHistory.objects.create(task=task,user=request.user,action='Atualização' if prior_status else 'Criação',details='Dados da tarefa salvos')
        messages.success(request,'Tarefa salva.'); return redirect('tasks')
    return render(request,'monitoria/task_form.html',{'form':form,'task':instance,'active':'tasks'})

@login_required
@require_POST
def task_status(request,pk):
    task=get_object_or_404(Task,pk=pk,deleted=False); new_status=request.POST.get('status')
    if new_status not in dict(Task.STATUS):
        if request.headers.get('x-requested-with')=='XMLHttpRequest': return JsonResponse({'ok':False,'error':'Status inválido.'},status=400)
        return redirect('tasks')
    if new_status=='Em andamento' and not task.start_date: task.start_date=timezone.localdate()
    if new_status=='Finalizado' and task.status!='Finalizado': task.completed_date=timezone.localdate()
    if new_status!='Finalizado' and task.status=='Finalizado': task.completed_date=None
    old=task.status; task.status=new_status; task.save(); TaskHistory.objects.create(task=task,user=request.user,action='Status alterado',details=f'{old} → {new_status}')
    if request.headers.get('x-requested-with')=='XMLHttpRequest': return JsonResponse({'ok':True,'status':new_status})
    return redirect(request.POST.get('next') or 'tasks')

@login_required
@require_POST
def task_delete(request,pk):
    task=get_object_or_404(Task,pk=pk); task.deleted=True; task.save(update_fields=['deleted','updated_at']); messages.success(request,'Tarefa arquivada.'); return redirect('tasks')

@login_required
def calendar_view(request):
    today=timezone.localdate()
    try: year,month=map(int,request.GET.get('month',today.strftime('%Y-%m')).split('-'))
    except (ValueError,TypeError): year,month=today.year,today.month
    cal=calendar.Calendar(firstweekday=6); weeks=cal.monthdatescalendar(year,month)
    low,high=weeks[0][0],weeks[-1][-1]
    events={}
    for task in Task.objects.filter(deleted=False,due_date__range=(low,high)).exclude(status='Cancelado'):
        events.setdefault(task.due_date,[]).append(task)
    prev=(date(year,month,1)-timedelta(days=1)).strftime('%Y-%m'); nxt=(date(year,month,28)+timedelta(days=4)).replace(day=1).strftime('%Y-%m')
    calendar_weeks=[[{'date':day,'events':events.get(day,[])} for day in week] for week in weeks]
    labels=['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro']
    return render(request,'monitoria/calendar.html',{'weeks':calendar_weeks,'weekdays':['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'],'month_label':f'{labels[month-1]} de {year}','prev_month':prev,'next_month':nxt,'current_month':month,'active':'calendar'})

def report_data(request):
    rows=Task.objects.filter(deleted=False).select_related('project','owner')
    start=request.GET.get('start'); end=request.GET.get('end')
    if start: rows=rows.filter(opened_date__gte=start)
    if end: rows=rows.filter(opened_date__lte=end)
    for key,field in [('project','project_id'),('owner','owner_id'),('status','status')]:
        if request.GET.get(key): rows=rows.filter(**{field:request.GET[key]})
    all_rows=list(rows); done=[x for x in all_rows if x.status=='Finalizado']; late=[x for x in all_rows if x.overdue or x.late_completion]
    durations=[(x.completed_date-x.opened_date).days for x in done if x.completed_date and x.opened_date]
    stats={'Abertas':len(all_rows)-len(done),'Concluídas':len(done),'Atrasadas':len(late),'Conclusão (%)':round(len(done)*100/len(all_rows)) if all_rows else 0,'Tempo médio (dias)':round(sum(durations)/len(durations),1) if durations else 0,'No prazo':sum(not x.late_completion for x in done),'Fora do prazo':sum(x.late_completion for x in done)}
    return all_rows,stats

@login_required
def reports(request):
    rows,stats=report_data(request)
    return render(request,'monitoria/reports.html',{'tasks':rows,'stats':stats,'projects':Project.objects.filter(archived=False),'users':User.objects.filter(is_active=True),'statuses':Task.STATUS,'filters':request.GET,'active':'reports'})

@login_required
def report_export(request):
    rows,_=report_data(request); book=Workbook(); sheet=book.active; sheet.title='Tarefas'
    sheet.append(['ID','Título','Status','Abertura','Prazo','Conclusão','Prioridade','Projeto','Responsável'])
    for task in rows: sheet.append([task.pk,task.title,task.status,task.opened_date,task.due_date,task.completed_date,task.priority,task.project.name if task.project else '',task.owner.get_full_name() or task.owner.username if task.owner else ''])
    sheet.freeze_panes='A2'; sheet.auto_filter.ref=sheet.dimensions
    stream=BytesIO(); book.save(stream); response=HttpResponse(stream.getvalue(),content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'); response['Content-Disposition']='attachment; filename="monitoria-relatorio.xlsx"'; return response

@login_required
def import_txt(request):
    parsed=None; form=ImportTextForm(request.POST or None,request.FILES or None)
    if request.method=='POST':
        text=request.POST.get('text','')
        uploaded=request.FILES.get('file')
        if uploaded:
            try: text=uploaded.read().decode('utf-8-sig')
            except UnicodeDecodeError: messages.error(request,'O TXT deve estar salvo em UTF-8.'); text=''
        if request.POST.get('confirm')=='1':
            parsed=parse_text(text); tasks_count=sum(len(p['tasks']) for p in parsed)
            if not tasks_count: messages.error(request,'Não encontrei tarefas no texto enviado.')
            elif any(t.get('invalid_date') for p in parsed for t in p['tasks']): messages.error(request,'Corrija as datas inválidas para AAAA-MM-DD antes de importar.')
            else:
                for project_data in parsed:
                    if not project_data['tasks']: continue
                    project=Project.objects.create(name=project_data['name'])
                    for item in project_data['tasks']:
                        start_date=item['start_date'] or (timezone.localdate() if item['status']=='Em andamento' else None)
                        task=Task.objects.create(title=item['title'],description=item['description'],project=project,status=item['status'],priority=item['priority'],start_date=start_date,due_date=item['due_date'],created_by=request.user)
                        TaskHistory.objects.create(task=task,user=request.user,action='Importação TXT',details='Importada de arquivo de texto')
                messages.success(request,f'{tasks_count} tarefas importadas em {len(parsed)} projetos.'); return redirect('tasks')
        elif text.strip(): parsed=parse_text(text)
        else: messages.error(request,'Selecione um arquivo TXT ou cole o conteúdo.')
        form=ImportTextForm(initial={'text':text})
    total=sum(len(p['tasks']) for p in parsed) if parsed else 0
    errors=[t['invalid_date'] for p in parsed or [] for t in p['tasks'] if t.get('invalid_date')]
    return render(request,'monitoria/import_txt.html',{'form':form,'parsed':parsed,'total':total,'date_errors':errors,'active':'import'})
