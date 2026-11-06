import re
import unicodedata
from datetime import date, datetime

DATE_VALUE = r'(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})'
START_RE = re.compile(
    r'(?:prazo\s+(?:inicial|de\s+inicio)|data\s+(?:de\s+)?inicio|inicio|comeco)\s*:\s*' + DATE_VALUE,
    re.IGNORECASE,
)
DUE_RE = re.compile(
    r'(?:prazo\s+(?:final|de\s+entrega)|data\s+(?:final|de\s+fim|de\s+entrega)|prazo|fim|final|entrega|data)\s*:\s*' + DATE_VALUE,
    re.IGNORECASE,
)
TASK_RE = re.compile(r'^\s*(?:[-*]\s+|\d+(?:\.\d+)*[.)]?\s+)(.+?)\s*$')
PROJECT_RE = re.compile(r'^\s*(\d+)\.\s+(.+?)\s*$')
STATUSES = {
    'a fazer': 'A fazer',
    'em andamento': 'Em andamento',
    'aguardando terceiros': 'Aguardando terceiros',
    'finalizado': 'Finalizado',
    'finalizados': 'Finalizado',
    'concluido': 'Finalizado',
    'concluidos': 'Finalizado',
    'cancelado': 'Cancelado',
}


def _ascii(text):
    """Remove acentos preservando offsets para recortar o texto original."""
    return ''.join(char for char in unicodedata.normalize('NFD', text)
                   if unicodedata.category(char) != 'Mn')


def parse_date(value):
    if '-' in value:
        return date.fromisoformat(value)
    return datetime.strptime(value, '%d/%m/%Y').date()


def extract_dates(text, task):
    comparable = _ascii(text)
    found = []
    for key, pattern in (('start_date', START_RE), ('due_date', DUE_RE)):
        for match in pattern.finditer(comparable):
            found.append(match)
            try:
                task[key] = parse_date(match.group(1))
            except ValueError:
                task['invalid_date'] = match.group(1)
    cleaned = text
    for match in reversed(found):
        cleaned = cleaned[:match.start()] + cleaned[match.end():]
    return cleaned.strip(' |-|')


def parse_text(text):
    projects = []
    current = None
    project_number = 0
    status = 'A fazer'
    last = None
    lines = text.splitlines()

    for index, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        normalized = _ascii(line).lower()
        if normalized.startswith('organizacao das tarefas'):
            last = None
            continue
        clean = _ascii(line.lstrip('-* ').strip()).lower().rstrip(':')
        if clean in STATUSES:
            status = STATUSES[clean]
            last = None
            continue

        if last:
            comparable = _ascii(line)
            before = len(START_RE.findall(comparable)) + len(DUE_RE.findall(comparable))
            if before:
                extract_dates(line, last)
                if START_RE.match(comparable) or DUE_RE.match(comparable):
                    continue

        heading = PROJECT_RE.match(line)
        if heading:
            number = int(heading.group(1))
            following = next((x.strip() for x in lines[index + 1:] if x.strip()), '')
            if current is None or (number > project_number and bool(re.match(r'^\d+\.\d+\s+', following))):
                current = {'name': heading.group(2).strip(), 'tasks': []}
                projects.append(current)
                project_number = number
                last = None
                continue

        item = TASK_RE.match(line)
        if item:
            title = item.group(1).strip()
            title = re.sub(r'^\[[ xX]?\]\s*', '', title)
            task = {
                'title': title,
                'description': '',
                'status': status,
                'priority': 'Média',
                'start_date': None,
                'due_date': None,
            }
            title = extract_dates(title, task)
            if title:
                if current is None:
                    current = {'name': 'Importação TXT', 'tasks': []}
                    projects.append(current)
                task['title'] = title
                current['tasks'].append(task)
                last = task
            continue

        if last and not normalized.startswith('features'):
            last['description'] = (last['description'] + '\n' + line).strip()

    return projects
