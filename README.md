# Monitor.ia — Gestão

V1 de gestão de projetos, tarefas, prazos e relatórios. Backend Flask com API JWT e SQLite local por padrão; MySQL opcional no Docker. O Flask também serve o frontend, então não é preciso iniciar o Live Server.

## Executar

### Protótipo local (sem Docker ou MySQL)

Na raiz do projeto, execute:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
python backend/run.py
```

Abra http://127.0.0.1:5000. O banco SQLite é criado automaticamente em `backend/monitoria.sqlite3`. O primeiro acesso cadastra a conta administradora. Também é possível abrir `backend/templates/index.html` com Live Server: o frontend já envia as chamadas da API e carrega seus arquivos estáticos de `http://127.0.0.1:5000`.

### Docker com MySQL

Copie `.env.example` para `.env`, ajuste os segredos e rode `docker compose up --build`. Abra http://localhost:5000.

## API

Rotas em `/api/auth`, `/api/dashboard`, `/api/projects`, `/api/tasks`, `/api/reports`. Todas as consultas usam parâmetros. JWT é enviado no header `Authorization: Bearer ...`. O protótipo usa as datas locais do sistema para abertura e cálculo de atraso.

## Importar tarefas de um TXT

Use **Importar TXT** na navegação para selecionar um arquivo ou colar texto. A prévia permite revisar os projetos, tarefas, status e prazos antes de gravar. Linhas iniciadas por hífen ou numeração viram tarefas; seções `A fazer`, `Em andamento`, `Aguardando terceiros`, `Finalizado` e `Cancelado` definem o status das tarefas seguintes. Para prazo, inclua `Prazo: AAAA-MM-DD` na mesma linha ou na linha imediatamente abaixo.

## Escopo

O prompt recebido foi truncado no início da descrição das tabelas do banco de dados. A V1 implementa usuários, projetos, tarefas, comentários e histórico; dashboard, Kanban com arrastar e soltar, calendário mensal e relatórios com exportação XLSX. O calendário mostra prazos de entrega; início/conclusão e visões semanais/diárias do FullCalendar ainda não estão incluídos.
