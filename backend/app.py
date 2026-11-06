import os
import re
import sqlite3
from datetime import date, datetime
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

DATABASE_MODE = os.getenv('DATABASE_MODE', 'sqlite').lower()
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_PATH = os.getenv('SQLITE_PATH', os.path.join('backend', 'monitoria.sqlite3'))
if not os.path.isabs(SQLITE_PATH):
    SQLITE_PATH = os.path.join(PROJECT_ROOT, SQLITE_PATH)

def db():
    if DATABASE_MODE == 'mysql':
        import mysql.connector
        return mysql.connector.connect(host=os.getenv('MYSQL_HOST','localhost'), port=int(os.getenv('MYSQL_PORT','3306')),
            user=os.getenv('MYSQL_USER','monitoria'), password=os.getenv('MYSQL_PASSWORD','monitoria_dev'),
            database=os.getenv('MYSQL_DATABASE','monitoria'), charset='utf8mb4')
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def sql_for_db(sql):
    if DATABASE_MODE == 'mysql':
        return sql
    return (sql.replace('%s', '?')
        .replace("DATE_FORMAT(data_conclusao,'%Y-%m')", "strftime('%Y-%m',data_conclusao)")
        .replace("DATE_SUB(CURDATE(),INTERVAL 6 MONTH)", "date('now','-6 months','localtime')")
        .replace('CURDATE()', "date('now','localtime')"))

def init_sqlite():
    if DATABASE_MODE == 'mysql':
        return
    conn = db()
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS usuarios (
      id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
      senha_hash TEXT NOT NULL, perfil TEXT NOT NULL DEFAULT 'usuario', ativo INTEGER NOT NULL DEFAULT 1,
      criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS projetos (
      id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, descricao TEXT, responsavel_id INTEGER,
      data_inicio TEXT, prazo_entrega TEXT, data_conclusao TEXT,
      status TEXT NOT NULL DEFAULT 'Não iniciado', prioridade TEXT NOT NULL DEFAULT 'Média', ativo INTEGER NOT NULL DEFAULT 1,
      criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(responsavel_id) REFERENCES usuarios(id));
    CREATE TABLE IF NOT EXISTS tarefas (
      id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, descricao TEXT, projeto_id INTEGER, responsavel_id INTEGER,
      prioridade TEXT NOT NULL DEFAULT 'Média', status TEXT NOT NULL DEFAULT 'A fazer', data_abertura TEXT NOT NULL,
      data_inicio TEXT, prazo_entrega TEXT, data_conclusao TEXT, excluido INTEGER NOT NULL DEFAULT 0, criado_por INTEGER,
      criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(projeto_id) REFERENCES projetos(id), FOREIGN KEY(responsavel_id) REFERENCES usuarios(id),
      FOREIGN KEY(criado_por) REFERENCES usuarios(id));
    CREATE INDEX IF NOT EXISTS idx_tarefas_prazo_status ON tarefas(prazo_entrega,status);
    CREATE INDEX IF NOT EXISTS idx_tarefas_projeto ON tarefas(projeto_id);
    CREATE TABLE IF NOT EXISTS historico_tarefas (
      id INTEGER PRIMARY KEY AUTOINCREMENT, tarefa_id INTEGER NOT NULL, usuario_id INTEGER, acao TEXT NOT NULL,
      detalhes TEXT, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(tarefa_id) REFERENCES tarefas(id), FOREIGN KEY(usuario_id) REFERENCES usuarios(id));
    CREATE TABLE IF NOT EXISTS comentarios_tarefas (
      id INTEGER PRIMARY KEY AUTOINCREMENT, tarefa_id INTEGER NOT NULL, usuario_id INTEGER,
      comentario TEXT NOT NULL, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(tarefa_id) REFERENCES tarefas(id), FOREIGN KEY(usuario_id) REFERENCES usuarios(id));
    CREATE TRIGGER IF NOT EXISTS trg_tarefa_updated AFTER UPDATE ON tarefas BEGIN
      UPDATE tarefas SET atualizado_em=CURRENT_TIMESTAMP WHERE id=NEW.id; END;
    CREATE TRIGGER IF NOT EXISTS trg_projeto_updated AFTER UPDATE ON projetos BEGIN
      UPDATE projetos SET atualizado_em=CURRENT_TIMESTAMP WHERE id=NEW.id; END;
    ''')
    conn.close()

def query(sql, params=(), one=False, write=False):
    conn = db()
    try:
        cur = conn.cursor(dictionary=True) if DATABASE_MODE == 'mysql' else conn.cursor()
        cur.execute(sql_for_db(sql), params)
        if write:
            conn.commit()
            return cur.lastrowid
        if DATABASE_MODE == 'mysql':
            return cur.fetchone() if one else cur.fetchall()
        row = cur.fetchone() if one else cur.fetchall()
        return dict(row) if one and row else ([dict(item) for item in row] if row is not None and not one else None)
    finally:
        conn.close()

def auth(fn):
    @wraps(fn)
    @jwt_required()
    def inner(*args, **kwargs):
        return fn(*args, **kwargs)
    return inner

def payload():
    return request.get_json(silent=True) or {}

def parse_txt(text):
    projects=[]; current=None; current_project_number=0; current_status='A fazer'; organized=False; last_task=None
    task_pattern=re.compile(r'^\s*(?:[-*]\s+|\d+(?:\.\d+)*[.)]?\s+)(.+?)\s*$')
    project_pattern=re.compile(r'^\s*(\d+)\.\s+(.+?)\s*$')
    date_pattern=re.compile(r'(?:Prazo|Data|Entrega)\s*:\s*(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})',re.I)
    status_names={'a fazer':'A fazer','em andamento':'Em andamento','aguardando terceiros':'Aguardando terceiros','finalizado':'Finalizado','finalizados':'Finalizado','concluído':'Finalizado','concluidos':'Finalizado','cancelado':'Cancelado'}
    lines=text.splitlines()
    for line_index, raw in enumerate(lines):
        line=raw.strip()
        if not line: continue
        if line.lower().startswith('organização das tarefas'):
            organized=True; last_task=None; continue
        clean_status=line.lstrip('-* ').strip().lower().rstrip(':')
        if clean_status in status_names:
            current_status=status_names[clean_status]; last_task=None; continue
        date_match=date_pattern.search(line)
        if date_match and last_task is not None:
            value=date_match.group(1)
            try:
                last_task['prazo_entrega']=date.fromisoformat(value).isoformat() if '-' in value else datetime.strptime(value,'%d/%m/%Y').date().isoformat()
            except ValueError:
                last_task['erro_data']=value
            if line.lower().startswith(('prazo:', 'data:', 'entrega:')): continue
        match_project=project_pattern.match(line)
        if match_project:
            number=int(match_project.group(1)); name=match_project.group(2).strip()
            following=next((item.strip() for item in lines[line_index+1:] if item.strip()),'')
            starts_subsection=bool(re.match(r'^\d+\.\d+\s+',following))
            if current is None or (not organized and number>current_project_number and starts_subsection):
                current={'nome':name,'tarefas':[]}; projects.append(current); current_project_number=number; last_task=None; continue
        match=task_pattern.match(line)
        if match:
            title=match.group(1).strip()
            if title.startswith('['): title=re.sub(r'^\[[ xX]?\]\s*','',title)
            inline_date=date_pattern.search(title); due=None; invalid=None
            if inline_date:
                value=inline_date.group(1); title=date_pattern.sub('',title).strip(' |-')
                try: due=date.fromisoformat(value).isoformat() if '-' in value else datetime.strptime(value,'%d/%m/%Y').date().isoformat()
                except ValueError: invalid=value
            if title:
                if current is None:
                    current={'nome':'Importação TXT','tarefas':[]}; projects.append(current)
                task={'titulo':title,'descricao':'','status':current_status,'prioridade':'Média','prazo_entrega':due}
                if invalid: task['erro_data']=invalid
                current['tarefas'].append(task); last_task=task
            continue
        if date_match and last_task is not None:
            continue
        if last_task is not None and not line.lower().startswith('features'):
            last_task['descricao']=(last_task.get('descricao','')+'\n'+line).strip()
        last_task=None
    return projects

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.update(SECRET_KEY=os.getenv('SECRET_KEY','dev-only-change-me'), JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY','dev-only-change-me-too'), DEBUG=os.getenv('FLASK_DEBUG')=='1')
    CORS(app, resources={r'/api/*': {'origins': '*'}})
    JWTManager(app)
    init_sqlite()

    @app.get('/')
    def home(): return send_from_directory('templates', 'index.html')
    @app.get('/static/<path:path>')
    def static_files(path): return send_from_directory('static', path)

    @app.post('/api/auth/register')
    def register():
        d=payload(); name=(d.get('nome') or '').strip(); email=(d.get('email') or '').strip().lower(); password=d.get('senha') or ''
        if not name or '@' not in email or len(password)<8: return jsonify(error='Informe nome, e-mail válido e senha com pelo menos 8 caracteres.'),400
        if query('SELECT id FROM usuarios LIMIT 1',one=True): return jsonify(error='O cadastro inicial já foi realizado.'),403
        try:
            uid=query('INSERT INTO usuarios (nome,email,senha_hash,perfil) VALUES (%s,%s,%s,%s)',(name,email,generate_password_hash(password),'admin'),write=True)
            return jsonify(access_token=create_access_token(identity=str(uid)), nome=name),201
        except Exception as exc:
            if isinstance(exc, sqlite3.IntegrityError) or (DATABASE_MODE == 'mysql' and exc.__class__.__name__ == 'IntegrityError'):
                return jsonify(error='E-mail já cadastrado.'),409
            raise

    @app.post('/api/auth/login')
    def login():
        d=payload(); user=query('SELECT id,nome,email,senha_hash,perfil FROM usuarios WHERE email=%s AND ativo=TRUE',(str(d.get('email','')).lower(),),one=True)
        if not user or not check_password_hash(user['senha_hash'],d.get('senha','')): return jsonify(error='E-mail ou senha inválidos.'),401
        return jsonify(access_token=create_access_token(identity=str(user['id'])), nome=user['nome'], perfil=user['perfil'])
    @app.get('/api/auth/me')
    @auth
    def me(): return jsonify(query('SELECT id,nome,email,perfil FROM usuarios WHERE id=%s',(int(get_jwt_identity()),),one=True))

    @app.get('/api/users')
    @auth
    def users(): return jsonify(query('SELECT id,nome,email FROM usuarios WHERE ativo=TRUE ORDER BY nome'))

    @app.get('/api/projects')
    @auth
    def projects():
        search=request.args.get('q',''); status=request.args.get('status','')
        rows=query("SELECT p.*,u.nome AS responsavel,(SELECT COUNT(*) FROM tarefas t WHERE t.projeto_id=p.id AND t.excluido=FALSE) total_tarefas,(SELECT COUNT(*) FROM tarefas t WHERE t.projeto_id=p.id AND t.status='Finalizado' AND t.excluido=FALSE) concluidas FROM projetos p LEFT JOIN usuarios u ON u.id=p.responsavel_id WHERE p.ativo=TRUE AND p.nome LIKE %s AND (%s='' OR p.status=%s) ORDER BY p.atualizado_em DESC",('%'+search+'%',status,status))
        for p in rows: p['progresso']=round(p['concluidas']*100/p['total_tarefas']) if p['total_tarefas'] else 0
        return jsonify(rows)
    @app.post('/api/projects')
    @auth
    def project_create():
        d=payload()
        if not (d.get('nome') or '').strip(): return jsonify(error='Nome do projeto obrigatório.'),400
        pid=query('INSERT INTO projetos(nome,descricao,responsavel_id,data_inicio,prazo_entrega,status,prioridade) VALUES(%s,%s,%s,%s,%s,%s,%s)',(d['nome'].strip(),d.get('descricao'),d.get('responsavel_id') or None,d.get('data_inicio') or None,d.get('prazo_entrega') or None,d.get('status','Não iniciado'),d.get('prioridade','Média')),write=True)
        return jsonify(id=pid),201
    @app.patch('/api/projects/<int:pid>')
    @auth
    def project_update(pid):
        d=payload(); allowed={'nome','descricao','responsavel_id','data_inicio','prazo_entrega','data_conclusao','status','prioridade'}
        fields=[k for k in d if k in allowed]
        if not fields: return jsonify(error='Nenhum campo válido.'),400
        query('UPDATE projetos SET '+','.join(f'{k}=%s' for k in fields)+' WHERE id=%s',tuple((d[k] or None) if k=='responsavel_id' else d[k] for k in fields)+(pid,),write=True)
        return jsonify(ok=True)
    @app.delete('/api/projects/<int:pid>')
    @auth
    def project_archive(pid): query('UPDATE projetos SET ativo=FALSE WHERE id=%s',(pid,),write=True); return jsonify(ok=True)

    @app.get('/api/tasks')
    @auth
    def tasks():
        clauses=['t.excluido=FALSE']; params=[]
        for key,col in [('status','t.status'),('projeto_id','t.projeto_id'),('responsavel_id','t.responsavel_id')]:
            val=request.args.get(key)
            if val: clauses.append(col+'=%s'); params.append(val)
        if request.args.get('q'): clauses.append('(t.titulo LIKE %s OR t.descricao LIKE %s)'); params += ['%'+request.args['q']+'%']*2
        if request.args.get('inicio'): clauses.append('COALESCE(t.prazo_entrega,t.data_abertura)>=%s'); params.append(request.args['inicio'])
        if request.args.get('fim'): clauses.append('COALESCE(t.prazo_entrega,t.data_abertura)<=%s'); params.append(request.args['fim'])
        rows=query("SELECT t.*,p.nome AS projeto,u.nome AS responsavel,(t.status NOT IN ('Finalizado','Cancelado') AND t.prazo_entrega<CURDATE()) AS atrasada,(t.status='Finalizado' AND t.data_conclusao>t.prazo_entrega) AS concluida_com_atraso FROM tarefas t LEFT JOIN projetos p ON p.id=t.projeto_id LEFT JOIN usuarios u ON u.id=t.responsavel_id WHERE "+' AND '.join(clauses)+' ORDER BY t.prazo_entrega IS NULL,t.prazo_entrega,t.atualizado_em DESC',tuple(params))
        return jsonify(rows)
    @app.post('/api/tasks')
    @auth
    def task_create():
        d=payload(); title=(d.get('titulo') or '').strip()
        if not title: return jsonify(error='Título obrigatório.'),400
        uid=int(get_jwt_identity()); tid=query('INSERT INTO tarefas(titulo,descricao,projeto_id,responsavel_id,prioridade,status,data_abertura,data_inicio,prazo_entrega,data_conclusao,criado_por) VALUES(%s,%s,%s,%s,%s,%s,CURDATE(),%s,%s,%s,%s)',(title,d.get('descricao'),d.get('projeto_id') or None,d.get('responsavel_id') or None,d.get('prioridade','Média'),d.get('status','A fazer'),date.today() if d.get('status')=='Em andamento' else None,d.get('prazo_entrega') or None,date.today() if d.get('status')=='Finalizado' else None,uid),write=True)
        query('INSERT INTO historico_tarefas(tarefa_id,usuario_id,acao,detalhes) VALUES(%s,%s,%s,%s)',(tid,uid,'Criação','Tarefa criada'),write=True)
        return jsonify(id=tid),201
    @app.patch('/api/tasks/<int:tid>')
    @auth
    def task_update(tid):
        d=payload(); allowed={'titulo','descricao','projeto_id','responsavel_id','prioridade','status','prazo_entrega'}; fields=[k for k in d if k in allowed]
        if not fields: return jsonify(error='Nenhum campo válido.'),400
        uid=int(get_jwt_identity()); old=query('SELECT status FROM tarefas WHERE id=%s AND excluido=FALSE',(tid,),one=True)
        if not old: return jsonify(error='Tarefa não encontrada.'),404
        vals=[(d[k] or None) if k in ('projeto_id','responsavel_id','prazo_entrega') else d[k] for k in fields]
        sql='UPDATE tarefas SET '+','.join(f'{k}=%s' for k in fields)
        if d.get('status')=='Em andamento' and old['status']!='Em andamento': sql+=',data_inicio=COALESCE(data_inicio,CURDATE())'
        if d.get('status')=='Finalizado' and old['status']!='Finalizado': sql+=',data_conclusao=CURDATE()'
        if d.get('status') and d['status']!='Finalizado' and old['status']=='Finalizado': sql+=',data_conclusao=NULL'
        query(sql+' WHERE id=%s',tuple(vals)+(tid,),write=True)
        query('INSERT INTO historico_tarefas(tarefa_id,usuario_id,acao,detalhes) VALUES(%s,%s,%s,%s)',(tid,uid,'Atualização',', '.join(fields)),write=True)
        return jsonify(ok=True)
    @app.delete('/api/tasks/<int:tid>')
    @auth
    def task_delete(tid): query('UPDATE tarefas SET excluido=TRUE WHERE id=%s',(tid,),write=True); return jsonify(ok=True)
    @app.get('/api/tasks/<int:tid>')
    @auth
    def task_detail(tid):
        task=query("SELECT t.*,p.nome AS projeto,u.nome AS responsavel,(t.status NOT IN ('Finalizado','Cancelado') AND t.prazo_entrega<CURDATE()) AS atrasada FROM tarefas t LEFT JOIN projetos p ON p.id=t.projeto_id LEFT JOIN usuarios u ON u.id=t.responsavel_id WHERE t.id=%s AND t.excluido=FALSE",(tid,),one=True)
        if not task: return jsonify(error='Tarefa não encontrada.'),404
        task['historico']=query('SELECT h.*,u.nome AS usuario FROM historico_tarefas h LEFT JOIN usuarios u ON u.id=h.usuario_id WHERE tarefa_id=%s ORDER BY criado_em DESC',(tid,))
        task['comentarios']=query('SELECT c.*,u.nome AS usuario FROM comentarios_tarefas c LEFT JOIN usuarios u ON u.id=c.usuario_id WHERE tarefa_id=%s ORDER BY criado_em DESC',(tid,))
        return jsonify(task)
    @app.post('/api/tasks/<int:tid>/comments')
    @auth
    def comment(tid):
        body=(payload().get('comentario') or '').strip()
        if not body: return jsonify(error='Comentário vazio.'),400
        query('INSERT INTO comentarios_tarefas(tarefa_id,usuario_id,comentario) SELECT id,%s,%s FROM tarefas WHERE id=%s AND excluido=FALSE',(int(get_jwt_identity()),body,tid),write=True)
        return jsonify(ok=True),201

    @app.post('/api/import/preview')
    @auth
    def import_preview():
        text=payload().get('texto','')
        if not isinstance(text,str) or not text.strip(): return jsonify(error='Envie o conteúdo do arquivo TXT.'),400
        parsed=parse_txt(text); count=sum(len(project['tarefas']) for project in parsed)
        if not count: return jsonify(error='Não encontrei tarefas. Use listas iniciadas por hífen ou numeração.'),400
        errors=[task['erro_data'] for project in parsed for task in project['tarefas'] if task.get('erro_data')]
        return jsonify(projetos=parsed,total_tarefas=count,erros_data=errors)

    @app.post('/api/import/txt')
    @auth
    def import_txt():
        text=payload().get('texto','')
        if not isinstance(text,str) or not text.strip(): return jsonify(error='Envie o conteúdo do arquivo TXT.'),400
        parsed=parse_txt(text); count=sum(len(project['tarefas']) for project in parsed)
        if not count: return jsonify(error='Não encontrei tarefas para importar.'),400
        if any(task.get('erro_data') for project in parsed for task in project['tarefas']):
            return jsonify(error='Corrija as datas inválidas antes de importar. Use AAAA-MM-DD.'),400
        uid=int(get_jwt_identity()); imported=0
        for project in parsed:
            if not project['tarefas']: continue
            project_id=query('INSERT INTO projetos(nome,status,prioridade) VALUES(%s,%s,%s)',(project['nome'],'Não iniciado','Média'),write=True)
            for task in project['tarefas']:
                task_id=query('INSERT INTO tarefas(titulo,descricao,projeto_id,prioridade,status,data_abertura,prazo_entrega,criado_por) VALUES(%s,%s,%s,%s,%s,CURDATE(),%s,%s)',(task['titulo'],task.get('descricao') or None,project_id,task['prioridade'],task['status'],task.get('prazo_entrega'),uid),write=True)
                query('INSERT INTO historico_tarefas(tarefa_id,usuario_id,acao,detalhes) VALUES(%s,%s,%s,%s)',(task_id,uid,'Importação TXT','Importada de arquivo de texto'),write=True)
                imported+=1
        return jsonify(ok=True,projetos=len([p for p in parsed if p['tarefas']]),tarefas=imported),201

    @app.get('/api/dashboard')
    @auth
    def dashboard():
        d={'cards':query("SELECT COUNT(*) total, SUM(status='A fazer') a_fazer, SUM(status='Em andamento') andamento, SUM(status='Aguardando terceiros') aguardando, SUM(status='Finalizado') finalizadas, SUM(status NOT IN ('Finalizado','Cancelado') AND prazo_entrega<CURDATE()) atrasadas FROM tarefas WHERE excluido=FALSE",one=True),
           'projetos_ativos':query("SELECT COUNT(*) n FROM projetos WHERE ativo=TRUE AND status='Em andamento'",one=True)['n'],
           'status':query('SELECT status,COUNT(*) total FROM tarefas WHERE excluido=FALSE GROUP BY status'),
           'projetos':query("SELECT p.id,p.nome,COUNT(t.id) total,SUM(t.status='Finalizado') concluidas FROM projetos p LEFT JOIN tarefas t ON t.projeto_id=p.id AND t.excluido=FALSE WHERE p.ativo=TRUE GROUP BY p.id ORDER BY total DESC LIMIT 6"),
           'proximas':query("SELECT t.id,t.titulo,t.prazo_entrega,t.status,p.nome AS projeto FROM tarefas t LEFT JOIN projetos p ON p.id=t.projeto_id WHERE t.excluido=FALSE AND t.status NOT IN ('Finalizado','Cancelado') AND t.prazo_entrega>=CURDATE() ORDER BY t.prazo_entrega LIMIT 6"),
           'recentes':query('SELECT id,titulo,status,atualizado_em FROM tarefas WHERE excluido=FALSE ORDER BY atualizado_em DESC LIMIT 6'),
           'concluidas_mes':query("SELECT DATE_FORMAT(data_conclusao,'%Y-%m') mes,COUNT(*) total FROM tarefas WHERE status='Finalizado' AND data_conclusao>=DATE_SUB(CURDATE(),INTERVAL 6 MONTH) GROUP BY mes ORDER BY mes")}
        return jsonify(d)

    @app.get('/api/reports')
    @auth
    def reports():
        where=['t.excluido=FALSE']; args=[]
        for k,col in [('inicio','t.data_abertura'),('fim','t.data_abertura'),('projeto_id','t.projeto_id'),('responsavel_id','t.responsavel_id'),('status','t.status')]:
            if request.args.get(k): where.append(col+('>=' if k=='inicio' else '<=' if k=='fim' else '=%s')); args.append(request.args[k])
        rows=query('SELECT t.id,t.titulo,t.status,t.data_abertura,t.prazo_entrega,t.data_conclusao,t.prioridade,p.nome projeto,u.nome responsavel FROM tarefas t LEFT JOIN projetos p ON p.id=t.projeto_id LEFT JOIN usuarios u ON u.id=t.responsavel_id WHERE '+' AND '.join(where)+' ORDER BY t.data_abertura DESC',tuple(args))
        today=date.today().isoformat()
        done=[r for r in rows if r['status']=='Finalizado']; late=[r for r in rows if (r['status'] not in ('Finalizado','Cancelado') and r['prazo_entrega'] and str(r['prazo_entrega'])<today) or (r['data_conclusao'] and r['prazo_entrega'] and str(r['data_conclusao'])>str(r['prazo_entrega']))]
        durations=[(date.fromisoformat(str(r['data_conclusao'])[:10])-date.fromisoformat(str(r['data_abertura'])[:10])).days for r in done if r['data_conclusao'] and r['data_abertura']]
        return jsonify(resumo={'abertas':len(rows)-len(done),'concluidas':len(done),'atrasadas':len(late),'percentual':round(len(done)*100/len(rows)) if rows else 0,'media_dias':round(sum(durations)/len(durations),1) if durations else 0,'no_prazo':sum(1 for r in done if not r['prazo_entrega'] or str(r['data_conclusao'])<=str(r['prazo_entrega'])),'fora_prazo':sum(1 for r in done if r['prazo_entrega'] and str(r['data_conclusao'])>str(r['prazo_entrega']))}, tarefas=rows)
    @app.get('/api/reports/export')
    @auth
    def export():
        import io
        from flask import Response
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        rows=reports().get_json()['tarefas']; fields=['id','titulo','status','data_abertura','prazo_entrega','data_conclusao','prioridade','projeto','responsavel']
        book=Workbook(); sheet=book.active; sheet.title='Tarefas'; sheet.append(['ID','Título','Status','Abertura','Prazo','Conclusão','Prioridade','Projeto','Responsável'])
        for cell in sheet[1]: cell.font=Font(color='FFFFFF',bold=True); cell.fill=PatternFill('solid',fgColor='26282D')
        for row in rows: sheet.append([row.get(k) for k in fields])
        sheet.freeze_panes='A2'; sheet.auto_filter.ref=sheet.dimensions
        for col,width in zip('ABCDEFGHI',[10,38,24,16,16,16,16,30,24]): sheet.column_dimensions[col].width=width
        stream=io.BytesIO(); book.save(stream); stream.seek(0)
        return Response(stream.getvalue(),mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':'attachment; filename=monitoria-relatorio.xlsx'})

    return app
