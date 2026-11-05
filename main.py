#main
from datetime import datetime, timedelta
from math import cos, radians, sin
import webbrowser

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle, Triangle
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.utils import platform

from models import Exercicio, TreinoDiario
from data import muscle_groups, predefined_exercises_by_group
from database import (
    add_workout_history_by_dia,
    clear_all_training_data,
    count_completed_workouts,
    create_tables,
    load_all_treinos,
    save_all_treinos,
)

# ---------------------------------------------------------------------------
# Paleta de cores: mesmos tons "Blue Grey" usados no app original em Flet
# (ft.Colors.BLUE_GREY_900 / 800 / 700 / 600, ft.Colors.WHITE, etc.)
# ---------------------------------------------------------------------------
BLUE_GREY_900 = (0.149, 0.196, 0.220, 1)   # fundo da página
BLUE_GREY_800 = (0.216, 0.278, 0.310, 1)   # cards principais
BLUE_GREY_700 = (0.271, 0.353, 0.392, 1)   # cards secundários / linhas
BLUE_GREY_600 = (0.329, 0.431, 0.478, 1)   # divisores / bordas
BLUE_GREY_200 = (0.690, 0.745, 0.773, 1)   # texto esmaecido
BLUE_GREY_100 = (0.812, 0.847, 0.863, 1)   # texto esmaecido claro
WHITE = (1, 1, 1, 1)
ACCENT = (0.129, 0.588, 0.953, 1)          # azul "primary" (equivalente ao FilledButton do Flet)
GREEN_700 = (0.180, 0.490, 0.196, 1)       # dia já treinado na semana
YOUTUBE_RED = (0.93, 0.08, 0.08, 1)

BACKGROUND = BLUE_GREY_900
CARD_BG = BLUE_GREY_800
CARD_BG_ALT = BLUE_GREY_700
DIVIDER_COLOR = BLUE_GREY_600
TEXT_COLOR = WHITE
MUTED_COLOR = BLUE_GREY_200
Window.clearcolor = BACKGROUND


# ---------------------------------------------------------------------------
# Componentes visuais reutilizáveis (cantos arredondados, ao estilo Material
# usado pelo Flet: ft.FilledButton, ft.OutlinedButton e ft.Container/ft.Card)
# ---------------------------------------------------------------------------
class RoundedButton(Button):
    """Equivalente ao ft.FilledButton: fundo preenchido e cantos arredondados."""

    def __init__(self, fill_color=CARD_BG, radius=12, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)  # some, o preenchimento é desenhado manualmente
        self.color = kwargs.get("color", TEXT_COLOR)
        self._fill_color = fill_color
        self._radius = radius
        with self.canvas.before:
            self._bg_color = Color(*self._cor_atual())
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self._radius])
        self.bind(pos=self._sync, size=self._sync, state=self._sync, disabled=self._sync)

    def _cor_atual(self):
        r, g, b, a = self._fill_color
        if self.disabled:
            return (r, g, b, 0.35)
        if self.state == "down":
            return (r * 0.85, g * 0.85, b * 0.85, a)
        return (r, g, b, a)

    def _sync(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._bg_color.rgba = self._cor_atual()


class YouTubeButton(RoundedButton):
    def __init__(self, **kwargs):
        super().__init__(fill_color=YOUTUBE_RED, radius=7, **kwargs)
        with self.canvas.after:
            Color(*WHITE)
            self._play_icon = Triangle(points=self._play_points())
        self.bind(pos=self._sync_play_icon, size=self._sync_play_icon)

    def _play_points(self):
        return [
            self.center_x - self.width * 0.12, self.center_y - self.height * 0.24,
            self.center_x - self.width * 0.12, self.center_y + self.height * 0.24,
            self.center_x + self.width * 0.24, self.center_y,
        ]

    def _sync_play_icon(self, *_):
        self._play_icon.points = self._play_points()


class RoundedOutlineButton(Button):
    """Equivalente ao ft.OutlinedButton: só a borda colorida, fundo transparente."""

    def __init__(self, border_color=BLUE_GREY_600, radius=12, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = kwargs.get("color", TEXT_COLOR)
        self._border_color = border_color
        self._radius = radius
        with self.canvas.before:
            self._border_color_inst = Color(*self._cor_atual())
            self._border_line = Line(rounded_rectangle=(0, 0, 0, 0, self._radius), width=1.4)
        self.bind(pos=self._sync, size=self._sync, state=self._sync, disabled=self._sync)

    def _cor_atual(self):
        r, g, b, a = self._border_color
        if self.disabled:
            return (r, g, b, 0.35)
        if self.state == "down":
            return (r, g, b, 0.6)
        return (r, g, b, a)

    def _sync(self, *_):
        x, y = self.pos
        w, h = self.size
        self._border_line.rounded_rectangle = (x, y, w, h, self._radius)
        self._border_color_inst.rgba = self._cor_atual()


class GearButton(RoundedOutlineButton):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        center_x, center_y = self.center
        radius = min(self.width, self.height) * 0.19
        with self.canvas.after:
            self._gear_color = Color(*WHITE)
            self._outer_ring = Line(
                points=self._circle_points(center_x, center_y, radius),
                close=True,
                width=2.2,
            )
            self._inner_ring = Line(
                points=self._circle_points(center_x, center_y, radius * 0.34),
                close=True,
                width=2.0,
            )
            self._teeth = [Line(points=(0, 0, 0, 0), width=2.4) for _ in range(8)]
        self.bind(pos=self._sync_gear, size=self._sync_gear, disabled=self._sync_gear)
        self._sync_gear()

    def _circle_points(self, center_x, center_y, radius):
        return [
            coordinate
            for step in range(32)
            for coordinate in (
                center_x + cos(radians(step * 360 / 32)) * radius,
                center_y + sin(radians(step * 360 / 32)) * radius,
            )
        ]

    def _sync_gear(self, *_):
        center_x, center_y = self.center
        radius = min(self.width, self.height) * 0.19
        tooth_inner = radius * 0.9
        tooth_outer = radius * 1.42

        self._gear_color.rgba = WHITE if not self.disabled else (*WHITE[:3], 0.35)
        self._outer_ring.points = self._circle_points(center_x, center_y, radius)
        self._inner_ring.points = self._circle_points(center_x, center_y, radius * 0.34)
        for index, tooth in enumerate(self._teeth):
            angle = radians(index * 45)
            tooth.points = (
                center_x + cos(angle) * tooth_inner,
                center_y + sin(angle) * tooth_inner,
                center_x + cos(angle) * tooth_outer,
                center_y + sin(angle) * tooth_outer,
            )


def make_button(text, primary=False, **kwargs):
    """Fábrica de botão: primary=True vira um botão preenchido (accent);
    primary=False vira um botão só com borda, igual ao par Filled/Outlined do Flet."""
    if primary:
        return RoundedButton(text=text, fill_color=ACCENT, bold=True, **kwargs)
    return RoundedOutlineButton(text=text, border_color=BLUE_GREY_600, **kwargs)


def make_spinner(text, values, **kwargs):
    return Spinner(
        text=text,
        values=values,
        background_normal="",
        background_color=CARD_BG_ALT,
        color=TEXT_COLOR,
        **kwargs,
    )


def make_input(**kwargs):
    return TextInput(
        multiline=False,
        background_normal="",
        background_active="",
        background_color=CARD_BG_ALT,
        foreground_color=TEXT_COLOR,
        cursor_color=ACCENT,
        padding=(10, 10),
        **kwargs,
    )


class Card(BoxLayout):
    """Equivalente ao ft.Container(bgcolor=..., border_radius=...) do Flet:
    um bloco com fundo colorido e cantos arredondados agrupando outros widgets."""

    def __init__(self, bg_color=CARD_BG, radius=16, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("padding", 16)
        kwargs.setdefault("spacing", 10)
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            Color(*bg_color)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size


class Divider(Widget):
    """Linha fina separadora, equivalente ao ft.Divider do Flet."""

    def __init__(self, color=DIVIDER_COLOR, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", 1)
        super().__init__(**kwargs)
        with self.canvas:
            Color(*color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[0])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


def secao_titulo(texto, **kwargs):
    kwargs.setdefault("size_hint_y", None)
    kwargs.setdefault("height", 24)
    kwargs.setdefault("bold", True)
    kwargs.setdefault("color", TEXT_COLOR)
    kwargs.setdefault("halign", "left")
    kwargs.setdefault("font_size", 14)
    label = Label(text=texto, **kwargs)
    label.bind(size=lambda lbl, _: setattr(lbl, "text_size", lbl.size))
    return label


def get_current_week_workout_dates(treinos, today=None):
    today = today or datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    trained_dates = set()

    for treino in treinos:
        for workout in treino.history:
            try:
                workout_date = datetime.fromisoformat(workout["finished_at"]).date()
            except (KeyError, TypeError, ValueError):
                continue
            if week_start <= workout_date < week_start + timedelta(days=7):
                trained_dates.add(workout_date)

    return week_start, trained_dates


class WeekdayTile(BoxLayout):
    def __init__(self, day_name, day_number, trained, is_today, **kwargs):
        fill = GREEN_700 if trained else (CARD_BG_ALT if not is_today else ACCENT)
        super().__init__(
            orientation="vertical",
            padding=(2, 5),
            spacing=1,
            size_hint_y=None,
            height=66,
            **kwargs,
        )
        with self.canvas.before:
            Color(*fill)
            self.tile_background = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
        self.bind(pos=self._sync_background, size=self._sync_background)

        self.add_widget(Label(text=day_name, color=BLUE_GREY_100, font_size=9,
                               size_hint_y=None, height=14))
        self.add_widget(Label(text=str(day_number), color=TEXT_COLOR, font_size=17,
                               bold=True, size_hint_y=None, height=23))
        self.add_widget(Label(text="OK" if trained else ("HOJE" if is_today else ""),
                               color=TEXT_COLOR, font_size=8, bold=True,
                               size_hint_y=None, height=13))

    def _sync_background(self, *_):
        self.tile_background.pos = self.pos
        self.tile_background.size = self.size


def build_week_calendar(treinos):
    week_start, trained_dates = get_current_week_workout_dates(treinos)
    today = datetime.now().date()
    day_names = ("SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM")
    week_end = week_start + timedelta(days=6)

    calendar = BoxLayout(orientation="vertical", size_hint_y=None, height=126, spacing=5)
    calendar.add_widget(secao_titulo("Semana atual", font_size=16, height=22))
    calendar.add_widget(Label(
        text=f"{week_start.strftime('%d/%m')} a {week_end.strftime('%d/%m')}",
        font_size=11, color=MUTED_COLOR, size_hint_y=None, height=18,
    ))

    days = BoxLayout(size_hint_y=None, height=66, spacing=5)
    for offset, day_name in enumerate(day_names):
        day_date = week_start + timedelta(days=offset)
        days.add_widget(WeekdayTile(
            day_name, day_date.day, day_date in trained_dates, day_date == today,
        ))
    calendar.add_widget(days)
    return calendar


# ---------------------------------------------------------------------------
# Tela 1: Menu principal
# ---------------------------------------------------------------------------
class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=(24, 36), spacing=18)

        cabecalho = BoxLayout(size_hint_y=None, height=54, spacing=8)
        cabecalho.add_widget(secao_titulo("Meu treino", font_size=26, height=54))
        btn_configuracoes = GearButton(text="", size_hint_x=None, width=48)
        btn_configuracoes.bind(on_release=lambda *_: self.abrir_configuracoes())
        cabecalho.add_widget(btn_configuracoes)
        layout.add_widget(cabecalho)

        layout.add_widget(Label(text="Escolha uma opção abaixo para começar.",
                                 color=MUTED_COLOR, size_hint_y=None, height=30))

        btn_planejamento = make_button("Planejamento de Treino", primary=True,
                                        size_hint_y=None, height=54)
        btn_planejamento.bind(on_release=lambda *_: self.ir_para("planning"))
        layout.add_widget(btn_planejamento)

        btn_semanal = make_button("Treino Semanal", size_hint_y=None, height=54)
        btn_semanal.bind(on_release=lambda *_: self.ir_para("weekly"))
        layout.add_widget(btn_semanal)

        btn_historico = make_button("Histórico da semana", size_hint_y=None, height=54)
        btn_historico.bind(on_release=lambda *_: self.ir_para("history"))
        layout.add_widget(btn_historico)

        layout.add_widget(BoxLayout())  # espaço vazio para empurrar os botões para cima
        self.add_widget(layout)

    def ir_para(self, nome_tela):
        self.manager.current = nome_tela

    def abrir_configuracoes(self):
        app = App.get_running_app()
        conteudo = BoxLayout(orientation="vertical", padding=16, spacing=12)
        conteudo.add_widget(Label(text="Configurações", color=TEXT_COLOR,
                                   size_hint_y=None, height=32))
        btn_limpar = make_button("Limpar histórico", size_hint_y=None, height=46)
        popup = Popup(title="", content=conteudo, size_hint=(0.82, 0.30),
                      background_color=BLUE_GREY_900, separator_color=DIVIDER_COLOR)
        btn_limpar.bind(on_release=lambda *_: (popup.dismiss(), app.confirmar_limpeza_completa()))
        conteudo.add_widget(btn_limpar)
        popup.open()


# ---------------------------------------------------------------------------
# Tela 2: Planejamento de treino (configura dias e exercícios)
# ---------------------------------------------------------------------------
class PlanningScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.exercicios_area = None
        self.lista_dia = None

    def on_pre_enter(self, *args):
        self.rebuild()

    def rebuild(self):
        app = App.get_running_app()
        self.clear_widgets()

        root = BoxLayout(orientation="vertical", padding=15, spacing=16, size_hint_y=None)
        root.bind(minimum_height=root.setter("height"))

        cabecalho = BoxLayout(size_hint_y=None, height=40)
        cabecalho.add_widget(secao_titulo("Planejamento de Treino", font_size=22, height=40))
        btn_voltar = make_button("Voltar", size_hint_x=None, width=100)
        btn_voltar.bind(on_release=lambda *_: setattr(self.manager, "current", "menu"))
        cabecalho.add_widget(btn_voltar)
        root.add_widget(cabecalho)

        # --- card com as configurações (dias / dia atual / grupo muscular) ---
        card_config = Card(bg_color=CARD_BG)

        card_config.add_widget(secao_titulo("Quantos dias por semana você vai treinar?"))
        texto_total = (f"{app.num_dias_treino_selecionados} dias"
                        if app.num_dias_treino_selecionados else "Selecione")
        total_dias_spinner = make_spinner(texto_total, [f"{i} dias" for i in range(1, 6)],
                                           size_hint_y=None, height=42)
        total_dias_spinner.bind(text=self.on_total_dias_changed)
        card_config.add_widget(total_dias_spinner)

        card_config.add_widget(Divider())

        card_config.add_widget(secao_titulo("Qual dia deseja configurar?"))
        dias_labels = [t.dia_semana for t in app.treinos_semana]
        if 0 <= app.current_selected_day_index < len(app.treinos_semana):
            dia_atual = app.treinos_semana[app.current_selected_day_index].dia_semana
        else:
            dia_atual = "Selecione"
        dia_spinner = make_spinner(dia_atual, dias_labels, size_hint_y=None, height=42)
        dia_spinner.bind(text=self.on_dia_changed)
        card_config.add_widget(dia_spinner)

        card_config.add_widget(Divider())

        card_config.add_widget(secao_titulo("Grupo muscular:"))
        grupo_spinner = make_spinner(app.current_selected_muscle_group or "Selecione",
                                      muscle_groups, size_hint_y=None, height=42)
        grupo_spinner.bind(text=self.on_grupo_changed)
        card_config.add_widget(grupo_spinner)

        root.add_widget(card_config)

        # --- card com os exercícios disponíveis do grupo escolhido ---
        card_exercicios = Card(bg_color=CARD_BG)
        card_exercicios.add_widget(secao_titulo("Exercícios Disponíveis"))
        self.exercicios_area = BoxLayout(orientation="vertical", size_hint_y=None, spacing=8)
        self.exercicios_area.bind(minimum_height=self.exercicios_area.setter("height"))
        self.build_exercicios_disponiveis()
        card_exercicios.add_widget(self.exercicios_area)
        root.add_widget(card_exercicios)

        # --- card (tom mais claro) com os exercícios já adicionados ao dia ---
        card_lista = Card(bg_color=CARD_BG_ALT)
        card_lista.add_widget(secao_titulo("Treinos adicionados"))
        self.lista_dia = BoxLayout(orientation="vertical", size_hint_y=None, spacing=6)
        self.lista_dia.bind(minimum_height=self.lista_dia.setter("height"))
        self.build_lista_dia()
        card_lista.add_widget(self.lista_dia)
        root.add_widget(card_lista)

        scroll = ScrollView()
        scroll.add_widget(root)
        self.add_widget(scroll)

    def on_total_dias_changed(self, spinner, texto):
        app = App.get_running_app()
        novo_total = int(texto.split(" ")[0])
        if novo_total != app.num_dias_treino_selecionados:
            app.sync_training_days(novo_total)
            self.rebuild()

    def on_dia_changed(self, spinner, texto):
        app = App.get_running_app()
        app.set_selected_day_by_label(texto)
        self.build_lista_dia()
        self.build_exercicios_disponiveis()

    def on_grupo_changed(self, spinner, texto):
        app = App.get_running_app()
        app.current_selected_muscle_group = texto
        self.build_exercicios_disponiveis()

    def build_exercicios_disponiveis(self):
        app = App.get_running_app()
        self.exercicios_area.clear_widgets()
        grupo = app.current_selected_muscle_group

        if not grupo or grupo not in predefined_exercises_by_group:
            self.exercicios_area.add_widget(
                Label(text="Selecione um grupo muscular.", color=MUTED_COLOR,
                      size_hint_y=None, height=25))
            return

        exercises = predefined_exercises_by_group[grupo]
        if 0 <= app.current_selected_day_index < len(app.treinos_semana):
            nomes_no_dia = {
                exercicio.nome
                for exercicio in app.treinos_semana[app.current_selected_day_index].exercicios
            }
            disponiveis = [ex for ex in exercises if ex.nome not in nomes_no_dia]
        else:
            disponiveis = exercises

        if not disponiveis:
            self.exercicios_area.add_widget(Label(
                text="Todos os exercícios deste grupo já estão no dia.",
                size_hint_y=None, height=30, color=MUTED_COLOR))
            return

        exercicio_spinner = make_spinner(disponiveis[0].nome, [ex.nome for ex in disponiveis],
                                          size_hint_y=None, height=40)
        series_input = make_input(text="3", input_filter="int", size_hint_y=None, height=40)
        reps_input = make_input(text="10", size_hint_y=None, height=40)

        linha_inputs = BoxLayout(size_hint_y=None, height=40, spacing=8)
        linha_inputs.add_widget(Label(text="Séries", size_hint_x=None, width=50, color=MUTED_COLOR))
        linha_inputs.add_widget(series_input)
        linha_inputs.add_widget(Label(text="Reps", size_hint_x=None, width=50, color=MUTED_COLOR))
        linha_inputs.add_widget(reps_input)

        def confirmar(*_):
            nome_escolhido = exercicio_spinner.text
            ex = next((item for item in disponiveis if item.nome == nome_escolhido), None)
            if ex is None:
                return
            app.add_predefined_exercise_to_day(ex, series_input.text, reps_input.text)
            self.build_lista_dia()
            self.build_exercicios_disponiveis()

        btn_confirmar = make_button("Adicionar exercício", primary=True,
                                     size_hint_y=None, height=42)
        btn_confirmar.bind(on_release=confirmar)

        self.exercicios_area.add_widget(exercicio_spinner)
        self.exercicios_area.add_widget(linha_inputs)
        self.exercicios_area.add_widget(btn_confirmar)

    def build_lista_dia(self):
        app = App.get_running_app()
        self.lista_dia.clear_widgets()

        if not (0 <= app.current_selected_day_index < len(app.treinos_semana)):
            self.lista_dia.add_widget(
                Label(text="Selecione um dia para ver os exercícios.", color=MUTED_COLOR,
                      size_hint_y=None, height=25))
            return

        dia = app.treinos_semana[app.current_selected_day_index]
        if not dia.exercicios:
            self.lista_dia.add_widget(
                Label(text="Nenhum exercício adicionado ainda.", color=MUTED_COLOR,
                      size_hint_y=None, height=25))
            return

        for index, ex in enumerate(dia.exercicios):
            linha = BoxLayout(size_hint_y=None, height=35, spacing=8)
            linha.add_widget(Label(text=f"{ex.nome} ({ex.grupo_muscular}): {ex.series}x{ex.repeticoes}",
                                    color=TEXT_COLOR))
            btn_remover = make_button("Remover", size_hint_x=None, width=90, height=32)

            def remover(_botao, idx=index):
                app.remove_exercicio_do_dia(idx)
                self.build_lista_dia()
                self.build_exercicios_disponiveis()

            btn_remover.bind(on_release=remover)
            linha.add_widget(btn_remover)
            self.lista_dia.add_widget(linha)


# ---------------------------------------------------------------------------
# Tela 3: Treino semanal (iniciar/finalizar treino)
# ---------------------------------------------------------------------------
class WeeklyScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.duracao_label = None

    def on_pre_enter(self, *args):
        self.rebuild()

    def rebuild(self):
        app = App.get_running_app()
        app.normalize_day_index()
        self.clear_widgets()

        root = BoxLayout(orientation="vertical", padding=15, spacing=16, size_hint_y=None)
        root.bind(minimum_height=root.setter("height"))

        cabecalho = BoxLayout(size_hint_y=None, height=40)
        cabecalho.add_widget(secao_titulo("Treino Semanal", font_size=22, height=40))
        btn_voltar = make_button("Voltar", size_hint_x=None, width=100)
        btn_voltar.bind(on_release=lambda *_: setattr(self.manager, "current", "menu"))
        cabecalho.add_widget(btn_voltar)
        root.add_widget(cabecalho)

        if not app.treinos_semana:
            aviso = Card(bg_color=CARD_BG)
            aviso.add_widget(Label(text="Nenhum treino planejado ainda.", color=MUTED_COLOR,
                                    size_hint_y=None, height=30))
            btn_planejar = make_button("Ir para Planejamento", primary=True,
                                        size_hint_y=None, height=42)
            btn_planejar.bind(on_release=lambda *_: setattr(self.manager, "current", "planning"))
            aviso.add_widget(btn_planejar)
            root.add_widget(aviso)
            scroll = ScrollView()
            scroll.add_widget(root)
            self.add_widget(scroll)
            return

        # --- seletor de dia ---
        dias_labels = [t.dia_semana for t in app.treinos_semana]
        dia_atual = app.treinos_semana[app.current_selected_day_index].dia_semana
        dia_spinner = make_spinner(dia_atual, dias_labels, size_hint_y=None, height=42)

        def on_dia_changed(spinner, texto):
            app.set_selected_day_by_label(texto)
            self.rebuild()

        dia_spinner.bind(text=on_dia_changed)
        root.add_widget(dia_spinner)

        # --- marcadores com a última duração de cada dia (estilo "chip") ---
        root.add_widget(secao_titulo("Última duração por plano", height=20))
        marcadores = BoxLayout(size_hint_y=None, height=54, spacing=8)
        for d in app.treinos_semana:
            concluido = bool(d.last_workout_seconds)
            duracao_txt = app.format_duration(d.last_workout_seconds) if concluido else "-"
            marcador = Card(bg_color=(GREEN_700 if concluido else CARD_BG_ALT), radius=10,
                             padding=6, spacing=1)
            marcador.add_widget(Label(text=d.dia_semana, font_size=11, color=BLUE_GREY_100,
                                       size_hint_y=None, height=16))
            marcador.add_widget(Label(text=duracao_txt, font_size=11, bold=True, color=TEXT_COLOR,
                                       size_hint_y=None, height=16))
            marcadores.add_widget(marcador)
        root.add_widget(marcadores)

        dia = app.treinos_semana[app.current_selected_day_index]

        # --- card principal: duração atual + botões + lista de exercícios ---
        card_principal = Card(bg_color=CARD_BG, padding=18, spacing=12)

        segundos = app.get_current_workout_elapsed_seconds()
        self.duracao_label = Label(text=f"Duração: {app.format_duration(segundos)}",
                                    font_size=20, bold=True, color=ACCENT,
                                    size_hint_y=None, height=36)
        card_principal.add_widget(self.duracao_label)

        botoes = BoxLayout(size_hint_y=None, height=44, spacing=10)
        btn_iniciar = make_button("Iniciar treino", primary=True,
                                   disabled=app.workout_session_running)
        btn_iniciar.bind(on_release=lambda *_: (app.start_workout_session(), self.rebuild()))
        btn_finalizar = make_button("Finalizar treino",
                                     disabled=not app.workout_session_running)
        btn_finalizar.bind(on_release=lambda *_: app.finish_workout_session())
        botoes.add_widget(btn_iniciar)
        botoes.add_widget(btn_finalizar)
        card_principal.add_widget(botoes)

        btn_resetar = make_button("Limpar resumo da semana", size_hint_y=None, height=38)
        btn_resetar.bind(on_release=lambda *_: (app.reset_week_markers(), self.rebuild()))
        card_principal.add_widget(btn_resetar)

        card_principal.add_widget(Divider())

        card_principal.add_widget(secao_titulo(f"Exercícios de {dia.dia_semana}:"))
        if not dia.exercicios:
            card_principal.add_widget(Label(text="Nenhum exercício adicionado.", color=MUTED_COLOR,
                                             size_hint_y=None, height=25))
        else:
            for ex in dia.exercicios:
                linha_exercicio = BoxLayout(size_hint_y=None, height=38, spacing=8)
                linha_exercicio.add_widget(Label(
                    text=f"{ex.nome} ({ex.grupo_muscular}) - {ex.series}x{ex.repeticoes}",
                    color=TEXT_COLOR, halign="left", valign="middle"))
                btn_video = YouTubeButton(text="", size_hint_x=None, width=42,
                                           size_hint_y=None, height=32,
                                           disabled=not ex.youtube_link)
                btn_video.bind(on_release=lambda _b, url=ex.youtube_link: app.open_exercise_video(url))
                linha_exercicio.add_widget(btn_video)
                card_principal.add_widget(linha_exercicio)

        root.add_widget(card_principal)

        scroll = ScrollView()
        scroll.add_widget(root)
        self.add_widget(scroll)

    def atualizar_duracao(self, *_):
        """Chamado a cada segundo pelo Clock enquanto o treino está em andamento."""
        app = App.get_running_app()
        if self.duracao_label is not None:
            segundos = app.get_current_workout_elapsed_seconds()
            self.duracao_label.text = f"Duração: {app.format_duration(segundos)}"


# ---------------------------------------------------------------------------
# Tela 4: Histórico da semana
# ---------------------------------------------------------------------------
class HistoryScreen(Screen):
    def on_pre_enter(self, *args):
        self.rebuild()

    def rebuild(self):
        app = App.get_running_app()
        self.clear_widgets()

        root = BoxLayout(orientation="vertical", padding=15, spacing=16, size_hint_y=None)
        root.bind(minimum_height=root.setter("height"))

        cabecalho = BoxLayout(size_hint_y=None, height=42, spacing=8)
        cabecalho.add_widget(secao_titulo("Histórico da semana", font_size=21, height=42))
        btn_voltar = make_button("Voltar", size_hint_x=None, width=88)
        btn_voltar.bind(on_release=lambda *_: setattr(self.manager, "current", "menu"))
        cabecalho.add_widget(btn_voltar)
        root.add_widget(cabecalho)

        card_calendario = Card(bg_color=CARD_BG)
        card_calendario.add_widget(build_week_calendar(app.treinos_semana))
        card_calendario.add_widget(Label(
            text=f"Treinos concluídos desde a última limpeza: {count_completed_workouts()}",
            color=ACCENT, bold=True, size_hint_y=None, height=28))
        root.add_widget(card_calendario)

        sessoes = []
        for treino in app.treinos_semana:
            for registro in treino.history:
                sessoes.append((registro["finished_at"], treino.dia_semana, registro["seconds"]))
        sessoes.sort(key=lambda sessao: sessao[0], reverse=True)

        card_sessoes = Card(bg_color=CARD_BG_ALT)
        card_sessoes.add_widget(secao_titulo("Sessões finalizadas"))
        if not sessoes:
            card_sessoes.add_widget(Label(text="Nenhum treino finalizado nesta semana.",
                                           color=MUTED_COLOR, size_hint_y=None, height=32))
        else:
            for finished_at, day_name, seconds in sessoes:
                card_sessoes.add_widget(Label(
                    text=f"{day_name}  |  {app.format_iso_to_ddmm_hhmm(finished_at)}  |  {app.format_duration(seconds)}",
                    color=TEXT_COLOR, halign="left", size_hint_y=None, height=30))
        root.add_widget(card_sessoes)

        scroll = ScrollView()
        scroll.add_widget(root)
        self.add_widget(scroll)


# ---------------------------------------------------------------------------
# Aplicativo principal
# ---------------------------------------------------------------------------
class GymApp(App):
    def build(self):
        # estado global do app
        self.treinos_semana = []
        self.num_dias_treino_selecionados = 0
        self.current_selected_day_index = -1
        self.current_selected_muscle_group = ""
        self.workout_session_started = None
        self.workout_session_finished = None
        self.workout_session_running = False
        self.timer_event = None

        create_tables()
        carregados = load_all_treinos()
        if carregados:
            self.treinos_semana = carregados
            mudou = False
            for t in self.treinos_semana:
                if t.last_workout_finished_at and not self.is_same_iso_week(t.last_workout_finished_at):
                    t.last_workout_finished_at = None
                    t.last_workout_seconds = 0
                    mudou = True
            if mudou:
                save_all_treinos(self.treinos_semana)
            self.num_dias_treino_selecionados = len(self.treinos_semana)
            self.current_selected_day_index = 0

        self.screen_manager = ScreenManager(transition=NoTransition())
        self.weekly_screen = WeeklyScreen(name="weekly")
        self.history_screen = HistoryScreen(name="history")
        self.screen_manager.add_widget(MenuScreen(name="menu"))
        self.screen_manager.add_widget(PlanningScreen(name="planning"))
        self.screen_manager.add_widget(self.weekly_screen)
        self.screen_manager.add_widget(self.history_screen)
        return self.screen_manager

    def on_stop(self):
        save_all_treinos(self.treinos_semana)

    # ---- funções auxiliares ----

    def normalize_day_index(self):
        if not self.treinos_semana:
            self.current_selected_day_index = -1
            return
        if self.current_selected_day_index < 0:
            self.current_selected_day_index = 0
        if self.current_selected_day_index >= len(self.treinos_semana):
            self.current_selected_day_index = len(self.treinos_semana) - 1

    def set_selected_day_by_label(self, day_label):
        if not day_label or not self.treinos_semana:
            self.current_selected_day_index = -1
            return
        for idx, treino in enumerate(self.treinos_semana):
            if treino.dia_semana == day_label:
                self.current_selected_day_index = idx
                return
        self.current_selected_day_index = 0

    def sync_training_days(self, new_count):
        if new_count <= 0:
            self.treinos_semana = []
            self.num_dias_treino_selecionados = 0
            self.current_selected_day_index = -1
            save_all_treinos(self.treinos_semana)
            return

        new_count = min(new_count, 5)
        while len(self.treinos_semana) < new_count:
            self.treinos_semana.append(TreinoDiario(f"Dia {len(self.treinos_semana) + 1}"))
        while len(self.treinos_semana) > new_count:
            self.treinos_semana.pop()
        for idx, treino in enumerate(self.treinos_semana):
            treino.dia_semana = f"Dia {idx + 1}"

        self.num_dias_treino_selecionados = len(self.treinos_semana)
        self.current_selected_day_index = 0
        save_all_treinos(self.treinos_semana)

    def add_predefined_exercise_to_day(self, exercicio_instance, series, repeticoes):
        if self.current_selected_day_index == -1 or not self.treinos_semana:
            self.show_message("Selecione um dia de treino antes de adicionar o exercício.")
            return

        series_val = str(series or "3").strip() or "3"
        reps_val = str(repeticoes or "10").strip() or "10"

        novo = Exercicio(
            exercicio_instance.nome,
            exercicio_instance.youtube_link,
            int(series_val),
            reps_val,
            exercicio_instance.grupo_muscular,
        )
        self.treinos_semana[self.current_selected_day_index].adicionar_exercicio(novo)
        save_all_treinos(self.treinos_semana)
        self.show_message(f"Exercício '{novo.nome}' adicionado.")

    def remove_exercicio_do_dia(self, index):
        if self.current_selected_day_index == -1 or not self.treinos_semana:
            return
        dia = self.treinos_semana[self.current_selected_day_index]
        if 0 <= index < len(dia.exercicios):
            del dia.exercicios[index]
            save_all_treinos(self.treinos_semana)

    def format_duration(self, total_seconds):
        total_seconds = max(0, int(total_seconds))
        horas, resto = divmod(total_seconds, 3600)
        minutos, segundos = divmod(resto, 60)
        return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

    def format_iso_to_ddmm_hhmm(self, iso_ts):
        if not iso_ts:
            return "-"
        try:
            dt = datetime.fromisoformat(iso_ts)
            return dt.strftime("%d/%m -- %H:%M")
        except ValueError:
            return iso_ts

    def is_same_iso_week(self, iso_ts):
        if not iso_ts:
            return False
        try:
            dt = datetime.fromisoformat(iso_ts)
            agora = datetime.now()
            return dt.isocalendar()[0:2] == agora.isocalendar()[0:2]
        except ValueError:
            return False

    def get_current_workout_elapsed_seconds(self):
        if self.workout_session_started is None:
            return 0
        if self.workout_session_running:
            return int((datetime.now() - self.workout_session_started).total_seconds())
        if self.workout_session_finished is None:
            return 0
        return int((self.workout_session_finished - self.workout_session_started).total_seconds())

    def start_workout_session(self):
        if self.current_selected_day_index < 0 or not self.treinos_semana:
            self.show_message("Selecione um dia para iniciar o treino.")
            return
        if self.workout_session_running:
            return
        self.workout_session_started = datetime.now()
        self.workout_session_finished = None
        self.workout_session_running = True
        self.timer_event = Clock.schedule_interval(self.weekly_screen.atualizar_duracao, 1)

    def finish_workout_session(self):
        if self.workout_session_started is None or not self.workout_session_running:
            return
        self.workout_session_running = False
        self.workout_session_finished = datetime.now()
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None

        duracao_segundos = self.get_current_workout_elapsed_seconds()
        if 0 <= self.current_selected_day_index < len(self.treinos_semana):
            dia = self.treinos_semana[self.current_selected_day_index]
            dia.last_workout_seconds = duracao_segundos
            dia.last_workout_finished_at = self.workout_session_finished.isoformat()
            dia.history.insert(0, {"seconds": duracao_segundos, "finished_at": dia.last_workout_finished_at})
            add_workout_history_by_dia(dia.dia_semana, duracao_segundos, dia.last_workout_finished_at)

        self.screen_manager.current = "history"

    def reset_week_markers(self):
        mudou = False
        for t in self.treinos_semana:
            if t.last_workout_finished_at or t.last_workout_seconds:
                t.last_workout_finished_at = None
                t.last_workout_seconds = 0
                mudou = True
        if mudou:
            save_all_treinos(self.treinos_semana)

    def show_message(self, texto):
        """Equivalente ao page.snack_bar do Flet: um popup simples que some sozinho."""
        popup = Popup(title="", content=Label(text=texto, color=TEXT_COLOR),
                      size_hint=(0.8, 0.2), background_color=BLUE_GREY_900,
                      separator_color=DIVIDER_COLOR)
        popup.open()
        Clock.schedule_once(lambda *_: popup.dismiss(), 2)

    def confirmar_limpeza_completa(self):
        conteudo = BoxLayout(orientation="vertical", padding=16, spacing=12)
        conteudo.add_widget(Label(
            text="A limpeza completa apagará todos os treinos adicionados e todo o histórico. Deseja continuar?",
            color=TEXT_COLOR, halign="center"))
        botoes = BoxLayout(size_hint_y=None, height=44, spacing=10)
        popup = Popup(title="Confirmar limpeza completa", content=conteudo,
                      size_hint=(0.88, 0.40), auto_dismiss=False,
                      background_color=BLUE_GREY_900, separator_color=DIVIDER_COLOR,
                      title_color=TEXT_COLOR)
        btn_cancelar = make_button("Cancelar")
        btn_limpar = make_button("Limpar tudo", primary=True)
        btn_cancelar.bind(on_release=lambda *_: popup.dismiss())
        btn_limpar.bind(on_release=lambda *_: (popup.dismiss(), self.limpar_todos_os_dados()))
        botoes.add_widget(btn_cancelar)
        botoes.add_widget(btn_limpar)
        conteudo.add_widget(botoes)
        popup.open()

    def limpar_todos_os_dados(self):
        try:
            clear_all_training_data()
        except Exception as error:
            self.show_message(f"Não foi possível limpar os dados: {error}")
            return

        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
        self.treinos_semana = []
        self.num_dias_treino_selecionados = 0
        self.current_selected_day_index = -1
        self.current_selected_muscle_group = ""
        self.workout_session_started = None
        self.workout_session_finished = None
        self.workout_session_running = False
        self.screen_manager.current = "menu"
        self.show_message("Limpeza completa: histórico e treinos apagados.")

    def open_exercise_video(self, url):
        if not url:
            return
        try:
            if platform == "android":
                from jnius import autoclass

                intent = autoclass("android.content.Intent")
                uri = autoclass("android.net.Uri")
                activity = autoclass("org.kivy.android.PythonActivity").mActivity
                activity.startActivity(intent(intent.ACTION_VIEW, uri.parse(url)))
            else:
                webbrowser.open(url)
        except Exception as error:
            self.show_message(f"Não foi possível abrir o vídeo: {error}")


if __name__ == "__main__":
    GymApp().run()
