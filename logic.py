"""Funções puras (sem Kivy e sem banco de dados) usadas pelo app.
Ficam separadas para poderem ser testadas sem abrir a interface.
"""
from datetime import datetime, timedelta
DEFAULT_SERIES = 3
DEFAULT_REPS = "10"
MAX_SERIES = 99
MAX_REPS_LENGTH = 20
def format_duration(total_seconds):
    """Formata segundos como HH:MM:SS."""
    total_seconds = max(0, int(total_seconds))
    horas, resto = divmod(total_seconds, 3600)
    minutos, segundos = divmod(resto, 60)
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"
def parse_iso(ts):
    """Converte texto ISO 8601 em datetime. Devolve None se vazio ou inválido."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None
def is_same_iso_week(ts, reference=None):
    """True se o timestamp cair na mesma semana ISO da data de referência (padrão: agora)."""
    dt = parse_iso(ts)
    if dt is None:
        return False
    reference = reference or datetime.now()
    return dt.isocalendar()[:2] == reference.isocalendar()[:2]
def week_start_of(day):
    """Segunda-feira da semana que contém `day`."""
    return day - timedelta(days=day.weekday())
def get_current_week_workout_dates(treinos, today=None):
    """Retorna (segunda-feira da semana, conjunto de datas com treino nessa semana)."""
    today = today or datetime.now().date()
    week_start = week_start_of(today)
    week_end = week_start + timedelta(days=7)
    trained_dates = set()
    for treino in treinos:
        for workout in treino.history:
            dt = parse_iso(workout.get("finished_at"))
            if dt is None:
                continue
            if week_start <= dt.date() < week_end:
                trained_dates.add(dt.date())
    return week_start, trained_dates
def parse_series(text):
    """Valida o número de séries digitado. Vazio usa o padrão; inválido gera ValueError."""
    texto = (text or "").strip()
    if not texto:
        return DEFAULT_SERIES
    if not (texto.isascii() and texto.isdigit()):
        raise ValueError("As séries devem ser um número inteiro.")
    valor = int(texto)
    if not 1 <= valor <= MAX_SERIES:
        raise ValueError(f"As séries devem estar entre 1 e {MAX_SERIES}.")
    return valor
def parse_reps(text):
    """Valida as repetições (ex.: '10' ou '8-12'). Vazio usa o padrão; inválido gera ValueError."""
    texto = (text or "").strip()
    if not texto:
        return DEFAULT_REPS
    if len(texto) > MAX_REPS_LENGTH:
        raise ValueError(f"As repetições devem ter no máximo {MAX_REPS_LENGTH} caracteres.")
    return texto
