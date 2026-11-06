from django import forms
from django.contrib.auth.models import User
from .models import Project, Task

class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control' if not isinstance(field.widget, forms.Select) else 'form-select'

class ProjectForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name','description','owner','start_date','due_date','status','priority']
        widgets = {
            'start_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'due_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs); self.fields['owner'].queryset=User.objects.filter(is_active=True); self.fields['owner'].required=False

class TaskForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model=Task
        fields=['title','description','project','owner','status','priority','start_date','due_date']
        widgets={
            'description': forms.Textarea(attrs={'rows': 3}),
            'start_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'due_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs); self.fields['project'].queryset=Project.objects.filter(archived=False); self.fields['owner'].queryset=User.objects.filter(is_active=True); self.fields['project'].required=False; self.fields['owner'].required=False

class ImportTextForm(forms.Form):
    text = forms.CharField(label='Conteúdo do TXT', widget=forms.Textarea(attrs={'rows':17,'class':'form-control','placeholder':'Selecione um .txt ou cole aqui o conteúdo'}))
    file = forms.FileField(label='Arquivo .txt', required=False, widget=forms.ClearableFileInput(attrs={'class':'form-control','accept':'.txt,text/plain'}))
