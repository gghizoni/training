import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
import database
from database import (
    add_workout_history_by_dia,
    clear_all_training_data,
    count_completed_workouts,
    create_tables,
    load_all_treinos,
    save_all_treinos,
)
from models import Exercicio, TreinoDiario
def _now_iso(days_ago=0):
    return (datetime.now() - timedelta(days=days_ago)).isoformat()
class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmp.name, "test.db")
        database.configure_database(self.db_path)
        create_tables()
    def tearDown(self):
        database.configure_database(database._DEFAULT_DB_PATH)
        self._tmp.cleanup()
    @staticmethod
    def _treinos(count):
        treinos = []
        for i in range(1, count + 1):
            treino = TreinoDiario(f"Dia {i}")
            treino.adicionar_exercicio(Exercicio(f"Ex {i}A", "http://x", 3, "8-12", "Peito"))
            treino.adicionar_exercicio(Exercicio(f"Ex {i}B", "", 4, "10", "Costas"))
            treinos.append(treino)
        return treinos
class RoundTripTests(DatabaseTestCase):
    def test_save_and_load_preserves_exercises_in_order(self):
        save_all_treinos(self._treinos(2))
        carregados = load_all_treinos()
        self.assertEqual([t.dia_semana for t in carregados], ["Dia 1", "Dia 2"])
        self.assertEqual([e.nome for e in carregados[0].exercicios], ["Ex 1A", "Ex 1B"])
        self.assertEqual(carregados[1].exercicios[0].series, 3)
    def test_unchanged_exercises_are_not_rewritten(self):
        save_all_treinos(self._treinos(1))
        ids_antes = [r[0] for r in sqlite3.connect(self.db_path).execute("SELECT id FROM exercicios")]
        save_all_treinos(load_all_treinos())
        ids_depois = [r[0] for r in sqlite3.connect(self.db_path).execute("SELECT id FROM exercicios")]
        self.assertEqual(ids_antes, ids_depois)
    def test_empty_save_and_load(self):
        save_all_treinos([])
        self.assertEqual(load_all_treinos(), [])
class HistoryPreservationTests(DatabaseTestCase):
    def test_removing_a_day_keeps_its_history(self):
        treinos = self._treinos(3)
        save_all_treinos(treinos)
        add_workout_history_by_dia("Dia 3", 1800, _now_iso())
        self.assertEqual(count_completed_workouts(), 1)
        save_all_treinos(treinos[:2])  # usuário reduziu para 2 dias
        self.assertEqual(count_completed_workouts(), 1)
        self.assertEqual([t.dia_semana for t in load_all_treinos()], ["Dia 1", "Dia 2"])
    def test_readding_a_day_restores_its_week_history(self):
        treinos = self._treinos(3)
        save_all_treinos(treinos)
        add_workout_history_by_dia("Dia 3", 1800, _now_iso())
        save_all_treinos(treinos[:2])
        save_all_treinos(self._treinos(3))
        dia3 = next(t for t in load_all_treinos() if t.dia_semana == "Dia 3")
        self.assertEqual(len(dia3.history), 1)
    def test_history_outside_current_week_is_not_loaded(self):
        save_all_treinos(self._treinos(1))
        add_workout_history_by_dia("Dia 1", 600, _now_iso(days_ago=400))
        self.assertEqual(load_all_treinos()[0].history, [])
        self.assertEqual(count_completed_workouts(), 1)
class WorkoutRecordingTests(DatabaseTestCase):
    def test_history_updates_last_workout_fields(self):
        save_all_treinos(self._treinos(1))
        finished = _now_iso()
        add_workout_history_by_dia("Dia 1", 905.7, finished)
        dia = load_all_treinos()[0]
        self.assertEqual(dia.last_workout_seconds, 905)
        self.assertEqual(dia.last_workout_finished_at, finished)
        self.assertEqual(dia.history[0]["seconds"], 905)
    def test_history_creates_missing_day(self):
        add_workout_history_by_dia("Dia Novo", 120, _now_iso())
        self.assertEqual(count_completed_workouts(), 1)
    def test_clear_all_removes_everything(self):
        save_all_treinos(self._treinos(2))
        add_workout_history_by_dia("Dia 1", 120, _now_iso())
        clear_all_training_data()
        self.assertEqual(load_all_treinos(), [])
        self.assertEqual(count_completed_workouts(), 0)
class MigrationTests(unittest.TestCase):
    def test_old_schema_is_upgraded_without_losing_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "old.db")
            conn = sqlite3.connect(path)
            conn.executescript("""
                CREATE TABLE treinos (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                      dia_semana TEXT NOT NULL UNIQUE);
                CREATE TABLE exercicios (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    treino_diario_id INTEGER NOT NULL, nome TEXT NOT NULL,
                    youtube_link TEXT, series INTEGER, repeticoes TEXT, grupo_muscular TEXT);
                INSERT INTO treinos (dia_semana) VALUES ('Dia 1');
                INSERT INTO exercicios (treino_diario_id, nome, series, repeticoes)
                    VALUES (1, 'Antigo', 3, '10');
            """)
            conn.commit()
            conn.close()
            database.configure_database(path)
            try:
                create_tables()
                create_tables()  # idempotente
                carregados = load_all_treinos()
            finally:
                database.configure_database(database._DEFAULT_DB_PATH)
            self.assertEqual(len(carregados), 1)
            self.assertEqual(carregados[0].exercicios[0].nome, "Antigo")
if __name__ == "__main__":
    unittest.main()
