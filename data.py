# data
from models import Exercicio

muscle_groups = [
    "Costas", "Tríceps", "Bíceps", "Peito", "Ombros",
    "Glúteos", "Quadríceps", "Posterior", "Panturrilhas"
]

predefined_exercises_by_group = {
    "Costas": [
        Exercicio("Puxada Alta", "https://youtube.com/puxada-alta", 3, "8-12", "Costas"),
        Exercicio("Remada Baixa", "https://youtube.com/remada-baixa", 3, "10-15", "Costas")
    ],
    "Tríceps": [
        Exercicio("Extensão de Tríceps", "https://youtube.com/extensao-triceps", 4, "10-12", "Tríceps"),
        Exercicio("Corda no Cabo", "https://youtube.com/corda-triceps", 3, "12-15", "Tríceps")
    ],
    "Bíceps": [
        Exercicio("Rosca Direta", "https://youtube.com/rosca-direta", 3, "8-12", "Bíceps"),
        Exercicio("Rosca Alternada", "https://youtube.com/rosca-alternada", 3, "10-12", "Bíceps")
    ],
    "Peito": [
        Exercicio("Supino Reto", "https://youtube.com/supino-reto", 4, "8-10", "Peito"),
        Exercicio("Crucifixo", "https://youtube.com/crucifixo", 3, "12-15", "Peito")
    ],
    "Ombros": [
        Exercicio("Desenvolvimento Ombro", "https://youtube.com/desenvolvimento-ombro", 3, "8-12", "Ombros"),
        Exercicio("Elevação Lateral", "https://youtube.com/elevacao-lateral", 3, "12-15", "Ombros")
    ],
    "Glúteos": [
        Exercicio("Elevação Pélvica", "https://youtube.com/elevacao-pelvica", 4, "10-15", "Glúteos"),
        Exercicio("Coice na Polia", "https://youtube.com/coice-polia", 3, "12-15", "Glúteos")
    ],
    "Quadríceps": [
        Exercicio("Agachamento Livre", "https://youtube.com/agachamento-livre", 4, "6-10", "Quadríceps"),
        Exercicio("Cadeira Extensora", "https://youtube.com/cadeira-extensora", 3, "12-15", "Quadríceps")
    ],
    "Posterior": [
        Exercicio("Stiff", "https://youtube.com/stiff", 4, "8-12", "Posterior"),
        Exercicio("Flexora Deitada", "https://youtube.com/flexora-deitada", 3, "12-15", "Posterior")
    ],
    "Panturrilhas": [
        Exercicio("Elevação Panturrilha", "https://youtube.com/elevacao-panturrilha", 4, "15-20", "Panturrilhas"),
        Exercicio("Panturrilha Sentado", "https://youtube.com/panturrilha-sentado", 3, "15-20", "Panturrilhas")
    ]
}
