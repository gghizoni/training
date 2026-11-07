#database
"""Persistência em SQLite.
Dias de treino removidos não são apagados: são marcados como inativos
(`treinos.ativo = 0`) para que o histórico de treinos seja preservado.
"""
import os
import sqlite3
from contextlib import contextmanager
from logic import is_same_iso_week
from models import Exercicio, TreinoDiario
_DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "treino_app.db")
_db_path = _DEFAULT_DB_PATH
def configure_database(path):
    """Define o arquivo do banco. Deve ser chamado antes de qualquer outra função."""
    global _db_path
    _db_path = path
def get_db_connection():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row  # permite acessar colunas por nome
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
@contextmanager
def _connection():
    """Faz commit ao sair sem erro, rollback em caso de erro, e sempre fecha a conexão."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS treinos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dia_semana TEXT NOT NULL UNIQUE,
        last_workout_seconds INTEGER DEFAULT 0,
        last_workout_finished_at TEXT,
        ativo INTEGER NOT NULL DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS exercicios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        treino_diario_id INTEGER NOT NULL,
        nome TEXT NOT NULL,
        youtube_link TEXT,
        series INTEGER,
        repeticoes TEXT,
        grupo_muscular TEXT,
        FOREIGN KEY (treino_diario_id) REFERENCES treinos (id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS workout_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        treino_diario_id INTEGER NOT NULL,
        duration_seconds INTEGER NOT NULL,
        finished_at TEXT NOT NULL,
        FOREIGN KEY (treino_diario_id) REFERENCES treinos (id) ON DELETE CASCADE
    )""",
)
# Colunas que podem faltar em bancos criados por versões antigas: (nome, definição)
_TREINOS_COLUMNS = (
    ("last_workout_seconds", "INTEGER DEFAULT 0"),
    ("last_workout_finished_at", "TEXT"),
    ("ativo", "INTEGER NOT NULL DEFAULT 1"),
)
def create_tables():
    with _connection() as conn:
        for ddl in _SCHEMA:
            conn.execute(ddl)
        # Migração: adiciona apenas as colunas que realmente faltam.
        existentes = {row["name"] for row in conn.execute("PRAGMA table_info(treinos)")}
        for nome, definicao in _TREINOS_COLUMNS:
            if nome not in existentes:
                conn.execute(f"ALTER TABLE treinos ADD COLUMN {nome} {definicao}")
def _ids_por_dia(conn):
    return {row["dia_semana"]: row["id"]
            for row in conn.execute("SELECT id, dia_semana FROM treinos")}
def _sync_exercicios(conn, treino_id, exercicios):
    """Regrava os exercícios do dia somente se eles mudaram."""
    novos = [(e.nome, e.youtube_link, e.series, e.repeticoes, e.grupo_muscular)
             for e in exercicios]
    atuais = [tuple(row) for row in conn.execute(
        "SELECT nome, youtube_link, series, repeticoes, grupo_muscular "
        "FROM exercicios WHERE treino_diario_id = ? ORDER BY id",
        (treino_id,),
    )]
    if atuais == novos:
        return
    conn.execute("DELETE FROM exercicios WHERE treino_diario_id = ?", (treino_id,))
    conn.executemany(
        "INSERT INTO exercicios (treino_diario_id, nome, youtube_link, series, repeticoes, grupo_muscular) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [(treino_id, *n) for n in novos],
    )
def save_all_treinos(treinos_semana: list[TreinoDiario]):
    with _connection() as conn:
        existentes = _ids_por_dia(conn)
        nomes_recebidos = {t.dia_semana for t in treinos_semana}
        # Dias removidos são desativados, não apagados: o histórico continua no banco.
        for nome, treino_id in existentes.items():
            if nome not in nomes_recebidos:
                conn.execute("UPDATE treinos SET ativo = 0 WHERE id = ?", (treino_id,))
        for treino in treinos_semana:
            treino_id = existentes.get(treino.dia_semana)
            if treino_id is None:
                cursor = conn.execute(
                    "INSERT INTO treinos (dia_semana, last_workout_seconds, last_workout_finished_at, ativo) "
                    "VALUES (?, ?, ?, 1)",
                    (treino.dia_semana, treino.last_workout_seconds, treino.last_workout_finished_at),
                )
                treino_id = cursor.lastrowid
            else:
                conn.execute(
                    "UPDATE treinos SET last_workout_seconds = ?, last_workout_finished_at = ?, ativo = 1 "
                    "WHERE id = ?",
                    (treino.last_workout_seconds, treino.last_workout_finished_at, treino_id),
                )
            _sync_exercicios(conn, treino_id, treino.exercicios)
def add_workout_history_by_dia(dia_semana: str, duration_seconds: int, finished_at_iso: str):
    segundos = int(duration_seconds)
    with _connection() as conn:
        row = conn.execute("SELECT id FROM treinos WHERE dia_semana = ?", (dia_semana,)).fetchone()
        if row:
            treino_id = row["id"]
        else:
            cursor = conn.execute(
                "INSERT INTO treinos (dia_semana, last_workout_seconds, last_workout_finished_at, ativo) "
                "VALUES (?, ?, ?, 1)",
                (dia_semana, segundos, finished_at_iso),
            )
            treino_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO workout_history (treino_diario_id, duration_seconds, finished_at) VALUES (?, ?, ?)",
            (treino_id, segundos, finished_at_iso),
        )
        conn.execute(
            "UPDATE treinos SET last_workout_seconds = ?, last_workout_finished_at = ? WHERE id = ?",
            (segundos, finished_at_iso, treino_id),
        )
def count_completed_workouts() -> int:
    with _connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM workout_history").fetchone()[0]
def clear_all_training_data():
    with _connection() as conn:
        conn.execute("DELETE FROM workout_history")
        conn.execute("DELETE FROM exercicios")
        conn.execute("DELETE FROM treinos")
def load_all_treinos() -> list[TreinoDiario]:
    """Carrega os dias ativos, seus exercícios e o histórico da semana ISO atual.
    Usa três consultas no total, independentemente do número de dias.
    """
    with _connection() as conn:
        treino_rows = conn.execute(
            "SELECT id, dia_semana, last_workout_seconds, last_workout_finished_at "
            "FROM treinos WHERE ativo = 1 ORDER BY id"
        ).fetchall()
        if not treino_rows:
            return []
        por_id = {
            row["id"]: TreinoDiario(
                row["dia_semana"],
                last_workout_seconds=row["last_workout_seconds"],
                last_workout_finished_at=row["last_workout_finished_at"],
            )
            for row in treino_rows
        }
        for row in conn.execute(
            "SELECT treino_diario_id, nome, youtube_link, series, repeticoes, grupo_muscular "
            "FROM exercicios ORDER BY id"
        ):
            treino = por_id.get(row["treino_diario_id"])
            if treino is not None:
                treino.adicionar_exercicio(Exercicio(
                    row["nome"], row["youtube_link"], row["series"],
                    row["repeticoes"], row["grupo_muscular"],
                ))
        for row in conn.execute(
            "SELECT treino_diario_id, duration_seconds, finished_at "
            "FROM workout_history ORDER BY finished_at DESC"
        ):
            treino = por_id.get(row["treino_diario_id"])
            if treino is not None and is_same_iso_week(row["finished_at"]):
                treino.history.append({
                    "seconds": row["duration_seconds"],
                    "finished_at": row["finished_at"],
                })
        return list(por_id.values())
if __name__ == "__main__":
    create_tables()
    print(f"Tabelas criadas ou já existentes em: {_db_path}")
