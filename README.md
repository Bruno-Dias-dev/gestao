# Gestão

Aplicação Django de gestão de projetos, tarefas, prazos e relatórios. O frontend usa Django Templates, HTML, CSS e JavaScript para gráficos e arrastar cartões no Kanban. SQLite é o banco padrão para desenvolvimento local.

## Rodar no Windows

Na raiz do projeto, instale as dependências e crie as tabelas:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe backend/manage.py migrate
.\.venv\Scripts\python.exe backend/manage.py runserver 127.0.0.1:8000
```

Abra http://127.0.0.1:8000. No primeiro acesso, o Django pede para criar a conta administradora. O banco novo fica em `backend/monitoria_django.sqlite3`; o banco Flask antigo (`backend/monitoria.sqlite3`) é preservado e não é alterado automaticamente.

## Docker

Copie `.env.example` para `.env`, altere `SECRET_KEY` e execute `docker compose up --build`. A aplicação ficará em http://127.0.0.1:8000 e gravará o SQLite em `data/`.

## Funcionalidades

- Dashboard com contadores e gráficos.
- Projetos, tarefas, responsáveis, prazos, comentários e histórico.
- Kanban com mudança de status por arrastar e soltar.
- Calendário mensal de prazos.
- Relatórios com filtros e exportação `.xlsx`.
- Importação TXT com prévia e confirmação; datas no formato `Início: AAAA-MM-DD` e `Prazo: AAAA-MM-DD`.
- Administração Django em `/admin/`.

O projeto não usa mais Flask. As páginas ficam em `backend/templates/monitoria/`, os modelos e rotas no app `backend/monitoria/`, e os estilos compartilhados em `backend/static/app.css`.
