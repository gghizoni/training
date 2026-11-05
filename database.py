#database
import sqlite3
from models import Exercicio, TreinoDiario

DB_NAME = "treino_app.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Permite acessar colunas por nome
    # ativar foreign keys
    try:
        conn.execute("PRAGMA foreign_keys = ON")
    except Exception:
        pass
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabela para os dias de treino
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS treinos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dia_semana TEXT NOT NULL UNIQUE,
            last_workout_seconds INTEGER DEFAULT 0,
            last_workout_finished_at TEXT
        )
    ''')

    # Tabela para os exercícios, com chave estrangeira para treinos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercicios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            treino_diario_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            youtube_link TEXT,
            series INTEGER,
            repeticoes TEXT,
            grupo_muscular TEXT,
            FOREIGN KEY (treino_diario_id) REFERENCES treinos (id) ON DELETE CASCADE
        )
    ''')

    # Tabela para histórico de treinos (múltiplos registros por dia)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            treino_diario_id INTEGER NOT NULL,
            duration_seconds INTEGER NOT NULL,
            finished_at TEXT NOT NULL,
            FOREIGN KEY (treino_diario_id) REFERENCES treinos (id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()

    # Caso o banco exista sem as novas colunas (migração simples), tente adicioná-las
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE treinos ADD COLUMN last_workout_seconds INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE treinos ADD COLUMN last_workout_finished_at TEXT")
        # criar tabela de histórico se não existir (migração segura)
        cursor.execute('''CREATE TABLE IF NOT EXISTS workout_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            treino_diario_id INTEGER NOT NULL,
            duration_seconds INTEGER NOT NULL,
            finished_at TEXT NOT NULL,
            FOREIGN KEY (treino_diario_id) REFERENCES treinos (id) ON DELETE CASCADE
        )''')
        conn.commit()
    except Exception:
        # colunas já existem ou não é possível alterar - ignorar
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

def save_all_treinos(treinos_semana: list[TreinoDiario]):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Upsert treinos: preserva histórico e atualiza registros existentes
    cursor.execute("SELECT id, dia_semana FROM treinos")
    existing = {row["dia_semana"]: row["id"] for row in cursor.fetchall()}

    incoming_names = [t.dia_semana for t in treinos_semana]
    # deletar treinos removidos
    to_delete_ids = [tid for name, tid in existing.items() if name not in incoming_names]
    for tid in to_delete_ids:
        cursor.execute("DELETE FROM treinos WHERE id = ?", (tid,))

    # refresh mapping after deletions
    cursor.execute("SELECT id, dia_semana FROM treinos")
    existing = {row["dia_semana"]: row["id"] for row in cursor.fetchall()}

    for treino_diario in treinos_semana:
        if treino_diario.dia_semana in existing:
            treino_diario_id = existing[treino_diario.dia_semana]
            cursor.execute(
                "UPDATE treinos SET last_workout_seconds = ?, last_workout_finished_at = ? WHERE id = ?",
                (getattr(treino_diario, 'last_workout_seconds', 0), getattr(treino_diario, 'last_workout_finished_at', None), treino_diario_id)
            )
        else:
            cursor.execute(
                "INSERT INTO treinos (dia_semana, last_workout_seconds, last_workout_finished_at) VALUES (?, ?, ?)",
                (treino_diario.dia_semana, getattr(treino_diario, 'last_workout_seconds', 0), getattr(treino_diario, 'last_workout_finished_at', None))
            )
            treino_diario_id = cursor.lastrowid
            existing[treino_diario.dia_semana] = treino_diario_id

        # clear exercises for this treino and reinsert
        cursor.execute("DELETE FROM exercicios WHERE treino_diario_id = ?", (treino_diario_id,))
        for exercicio in treino_diario.exercicios:
            cursor.execute(
                "INSERT INTO exercicios (treino_diario_id, nome, youtube_link, series, repeticoes, grupo_muscular) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    treino_diario_id,
                    exercicio.nome,
                    exercicio.youtube_link,
                    exercicio.series,
                    exercicio.repeticoes,
                    exercicio.grupo_muscular,
                )
            )
    conn.commit()
    conn.close()

def add_workout_history_by_dia(dia_semana: str, duration_seconds: int, finished_at_iso: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    # find treino id
    cursor.execute("SELECT id FROM treinos WHERE dia_semana = ?", (dia_semana,))
    row = cursor.fetchone()
    if row:
        treino_id = row["id"]
    else:
        # create the treino if missing
        cursor.execute("INSERT INTO treinos (dia_semana, last_workout_seconds, last_workout_finished_at) VALUES (?, ?, ?)", (dia_semana, duration_seconds, finished_at_iso))
        treino_id = cursor.lastrowid

    cursor.execute("INSERT INTO workout_history (treino_diario_id, duration_seconds, finished_at) VALUES (?, ?, ?)", (treino_id, int(duration_seconds), finished_at_iso))
    # update last_workout fields on treinos table
    cursor.execute("UPDATE treinos SET last_workout_seconds = ?, last_workout_finished_at = ? WHERE id = ?", (int(duration_seconds), finished_at_iso, treino_id))
    conn.commit()
    conn.close()

def count_completed_workouts() -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM workout_history")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def clear_all_training_data():
    conn = get_db_connection()
    try:
        conn.execute("BEGIN")
        conn.execute("DELETE FROM workout_history")
        conn.execute("DELETE FROM exercicios")
        conn.execute("DELETE FROM treinos")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def load_all_treinos() -> list[TreinoDiario]:
    conn = get_db_connection()
    cursor = conn.cursor()

    treinos = []
    cursor.execute("SELECT id, dia_semana, last_workout_seconds, last_workout_finished_at FROM treinos ORDER BY id")
    treino_rows = cursor.fetchall()

    for treino_row in treino_rows:
        treino_diario = TreinoDiario(
            treino_row["dia_semana"],
            exercicios=None,
            last_workout_seconds=treino_row["last_workout_seconds"] if "last_workout_seconds" in treino_row.keys() else 0,
            last_workout_finished_at=treino_row["last_workout_finished_at"] if "last_workout_finished_at" in treino_row.keys() else None,
            history=[],
        )

        cursor.execute(
            "SELECT nome, youtube_link, series, repeticoes, grupo_muscular FROM exercicios WHERE treino_diario_id = ?",
            (treino_row["id"],)
        )
        exercicio_rows = cursor.fetchall()

        for ex_row in exercicio_rows:
            exercicio = Exercicio(
                ex_row["nome"],
                ex_row["youtube_link"],
                ex_row["series"],
                ex_row["repeticoes"],
                ex_row["grupo_muscular"],
            )
            treino_diario.adicionar_exercicio(exercicio)

        treinos.append(treino_diario)

    # Attach history entries for the current ISO week
    from datetime import datetime
    now = datetime.now()
    for treino_row, treino_diario in zip(treino_rows, treinos):
        cursor.execute("SELECT duration_seconds, finished_at FROM workout_history WHERE treino_diario_id = ? ORDER BY finished_at DESC", (treino_row["id"],))
        hist_rows = cursor.fetchall()
        for hr in hist_rows:
            try:
                dt = datetime.fromisoformat(hr["finished_at"])
            except Exception:
                continue
            # include only entries from current ISO week
            if dt.isocalendar()[0:2] == now.isocalendar()[0:2]:
                treino_diario.history.append({"seconds": hr["duration_seconds"], "finished_at": hr["finished_at"]})

    conn.close()
    return treinos

if __name__ == "__main__":
    create_tables()
    print("Tabelas criadas ou já existentes no banco de dados.")

    # Exemplo de salvamento
    # from models import Exercicio, TreinoDiario # Necessário se rodar este arquivo sozinho
    # treino1 = TreinoDiario("Dia Teste")
    # treino1.adicionar_exercicio(Exercicio("Flexão", "link_flexao", 3, "10", "Peito"))
    # save_all_treinos([treino1])
    # print("Treino de teste salvo.")

    # # Exemplo de carregamento
    # loaded_treinos = load_all_treinos()
    # if loaded_treinos:
    #     print(f"Treinos carregados: {len(loaded_treinos)}")
    #     for t in loaded_treinos:
    #         print(t)
    #         for e in t.exercicios:
    #             print(f"  - {e}")
    # else:
    #     print("Nenhum treino carregado.")