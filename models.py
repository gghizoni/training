#models

# Definindo a estrutura de dados para um exercício
class Exercicio:
    def __init__(self, nome: str, youtube_link: str, series: int, repeticoes: str, grupo_muscular: str):
        self.nome = nome
        self.youtube_link = youtube_link
        self.series = series
        self.repeticoes = repeticoes  # Ex: '8-12', '10'
        self.grupo_muscular = grupo_muscular

    def __repr__(self):
        return f"Exercicio(Nome: {self.nome}, Grupo: {self.grupo_muscular}, Séries: {self.series}x{self.repeticoes})"


# Definindo a estrutura de dados para um dia de treino
class TreinoDiario:
    def __init__(self, dia_semana: str, exercicios: list = None, last_workout_seconds: int = 0,
                 last_workout_finished_at: str | None = None, history: list = None):
        self.dia_semana = dia_semana
        self.exercicios = exercicios if exercicios is not None else []
        self.last_workout_seconds = int(last_workout_seconds or 0)
        self.last_workout_finished_at = last_workout_finished_at
        self.history = history if history is not None else []

    def adicionar_exercicio(self, exercicio: Exercicio):
        self.exercicios.append(exercicio)

    def __repr__(self):
        return f"TreinoDiario(Dia: {self.dia_semana}, Exercícios: {len(self.exercicios)}, LastSec: {self.last_workout_seconds}, LastAt: {self.last_workout_finished_at})"


if __name__ == "__main__":
    supino_reto = Exercicio("Supino Reto", "https://www.youtube.com/watch?v=supino", 3, "8-12", "Peito")
    agachamento = Exercicio("Agachamento", "https://www.youtube.com/watch?v=agachamento", 4, "6-10", "Quadríceps")

    treino_segunda = TreinoDiario("Segunda-feira")
    treino_segunda.adicionar_exercicio(supino_reto)
    treino_segunda.adicionar_exercicio(agachamento)

    print(supino_reto)
    print(treino_segunda)
    for ex in treino_segunda.exercicios:
        print(f"  - {ex.nome} ({ex.grupo_muscular}): {ex.series} séries de {ex.repeticoes} repetições")
