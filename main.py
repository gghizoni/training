from datetime import datetime, timedelta
from math import cos, radians, sin
import os
import webbrowser

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle, Triangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import NoTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import platform

from data import muscle_groups, predefined_exercises_by_group
from database import (
    add_workout_history_by_dia,
    clear_all_training_data,
    configure_database,
    count_completed_workouts,
    create_tables,
    load_all_treinos,
    save_all_treinos,
)
from logic import (
    format_duration,
    get_current_week_workout_dates,
    is_same_iso_week,
    parse_iso,
    parse_reps,
    parse_series,
)
from models import Exercicio, TreinoDiario


BLUE_GREY_900 = (0.149, 0.196, 0.220, 1)
BLUE_GREY_800 = (0.216, 0.278, 0.310, 1)
BLUE_GREY_700 = (0.271, 0.353, 0.392, 1)
BLUE_GREY_600 = (0.329, 0.431, 0.478, 1)
BLUE_GREY_200 = (0.690, 0.745, 0.773, 1)
BLUE_GREY_100 = (0.812, 0.847, 0.863, 1)
WHITE = (1, 1, 1, 1)
ACCENT = (0.129, 0.588, 0.953, 1)
GREEN_700 = (0.180, 0.490, 0.196, 1)
YOUTUBE_RED = (0.93, 0.08, 0.08, 1)

BACKGROUND = BLUE_GREY_900
CARD_BG = BLUE_GREY_800
CARD_BG_ALT = BLUE_GREY_700
DIVIDER_COLOR = BLUE_GREY_600
TEXT_COLOR = WHITE
MUTED_COLOR = BLUE_GREY_200
DB_FILE_NAME = "treino_app.db"

Window.clearcolor = BACKGROUND


def circle_points(center_x, center_y, radius, segments=32):
    return [
        coordinate
        for step in range(segments)
        for coordinate in (
            center_x + cos(radians(step * 360 / segments)) * radius,
            center_y + sin(radians(step * 360 / segments)) * radius,
        )
    ]


def make_page_root():
    root = BoxLayout(
        orientation="vertical",
        padding=15,
        spacing=16,
        size_hint_y=None,
    )
    root.bind(minimum_height=root.setter("height"))
    return root


def make_scroll(root):
    scroll = ScrollView()
    scroll.add_widget(root)
    return scroll


def make_page_header(title, font_size, height, back_width, on_back):
    header = BoxLayout(size_hint_y=None, height=height, spacing=8)
    header.add_widget(secao_titulo(title, font_size=font_size, height=height))
    back_button = make_button(
        "Voltar",
        size_hint_x=None,
        width=back_width,
        size_hint_y=None,
        height=height,
    )
    back_button.bind(on_release=lambda *_: on_back())
    header.add_widget(back_button)
    return header


class RoundedButton(Button):
    def __init__(self, fill_color=CARD_BG, radius=12, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = kwargs.get("color", TEXT_COLOR)
        self._fill_color = fill_color
        self._radius = radius
        with self.canvas.before:
            self._background_color = Color(*self._current_color())
            self._background_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[self._radius],
            )
        self.bind(
            pos=self._sync_background,
            size=self._sync_background,
            state=self._sync_background,
            disabled=self._sync_background,
        )

    def _current_color(self):
        red, green, blue, alpha = self._fill_color
        if self.disabled:
            return red, green, blue, 0.35
        if self.state == "down":
            return red * 0.85, green * 0.85, blue * 0.85, alpha
        return self._fill_color

    def _sync_background(self, *_):
        self._background_rect.pos = self.pos
        self._background_rect.size = self.size
        self._background_color.rgba = self._current_color()


class RoundedOutlineButton(Button):
    def __init__(self, border_color=BLUE_GREY_600, radius=12, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = kwargs.get("color", TEXT_COLOR)
        self._border_color = border_color
        self._radius = radius
        with self.canvas.before:
            self._line_color = Color(*self._current_color())
            self._border_line = Line(
                rounded_rectangle=(0, 0, 0, 0, self._radius),
                width=1.4,
            )
        self.bind(
            pos=self._sync_border,
            size=self._sync_border,
            state=self._sync_border,
            disabled=self._sync_border,
        )

    def _current_color(self):
        red, green, blue, alpha = self._border_color
        if self.disabled:
            return red, green, blue, 0.35
        if self.state == "down":
            return red, green, blue, 0.6
        return self._border_color

    def _sync_border(self, *_):
        x, y = self.pos
        width, height = self.size
        self._border_line.rounded_rectangle = (
            x,
            y,
            width,
            height,
            self._radius,
        )
        self._line_color.rgba = self._current_color()


class YouTubeButton(RoundedButton):
    def __init__(self, **kwargs):
        super().__init__(fill_color=YOUTUBE_RED, radius=7, **kwargs)
        with self.canvas.after:
            Color(*WHITE)
            self._play_icon = Triangle(points=self._play_points())
        self.bind(pos=self._sync_play_icon, size=self._sync_play_icon)

    def _play_points(self):
        return [
            self.center_x - self.width * 0.12,
            self.center_y - self.height * 0.24,
            self.center_x - self.width * 0.12,
            self.center_y + self.height * 0.24,
            self.center_x + self.width * 0.24,
            self.center_y,
        ]

    def _sync_play_icon(self, *_):
        self._play_icon.points = self._play_points()


class GearButton(RoundedOutlineButton):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.after:
            self._gear_color = Color(*WHITE)
            self._outer_ring = Line(close=True, width=2.2)
            self._inner_ring = Line(close=True, width=2.0)
            self._teeth = [Line(width=2.4) for _ in range(8)]
        self.bind(
            pos=self._sync_gear,
            size=self._sync_gear,
            disabled=self._sync_gear,
        )
        self._sync_gear()

    def _sync_gear(self, *_):
        center_x, center_y = self.center
        radius = min(self.width, self.height) * 0.19
        tooth_inner = radius * 0.9
        tooth_outer = radius * 1.42

        self._gear_color.rgba = WHITE if not self.disabled else (*WHITE[:3], 0.35)
        self._outer_ring.points = circle_points(center_x, center_y, radius)
        self._inner_ring.points = circle_points(center_x, center_y, radius * 0.34)
        for index, tooth in enumerate(self._teeth):
            angle = radians(index * 45)
            tooth.points = (
                center_x + cos(angle) * tooth_inner,
                center_y + sin(angle) * tooth_inner,
                center_x + cos(angle) * tooth_outer,
                center_y + sin(angle) * tooth_outer,
            )


def make_button(text, primary=False, **kwargs):
    if primary:
        return RoundedButton(
            text=text,
            fill_color=ACCENT,
            bold=True,
            **kwargs,
        )
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
    def __init__(self, bg_color=CARD_BG, radius=16, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("padding", 16)
        kwargs.setdefault("spacing", 10)
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            Color(*bg_color)
            self._background_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[radius],
            )
        self.bind(pos=self._sync_background, size=self._sync_background)

    def _sync_background(self, *_):
        self._background_rect.pos = self.pos
        self._background_rect.size = self.size


class Divider(Widget):
    def __init__(self, color=DIVIDER_COLOR, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", 1)
        super().__init__(**kwargs)
        with self.canvas:
            Color(*color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size)
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
    label.bind(size=lambda widget, _: setattr(widget, "text_size", widget.size))
    return label


class WeekdayTile(BoxLayout):
    def __init__(self, day_name, day_number, trained, is_today, **kwargs):
        fill = GREEN_700 if trained else (ACCENT if is_today else CARD_BG_ALT)
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
            self._background_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[10],
            )
        self.bind(pos=self._sync_background, size=self._sync_background)
        self.add_widget(Label(
            text=day_name,
            color=BLUE_GREY_100,
            font_size=9,
            size_hint_y=None,
            height=14,
        ))
        self.add_widget(Label(
            text=str(day_number),
            color=TEXT_COLOR,
            font_size=17,
            bold=True,
            size_hint_y=None,
            height=23,
        ))
        self.add_widget(Label(
            text="OK" if trained else ("HOJE" if is_today else ""),
            color=TEXT_COLOR,
            font_size=8,
            bold=True,
            size_hint_y=None,
            height=13,
        ))

    def _sync_background(self, *_):
        self._background_rect.pos = self.pos
        self._background_rect.size = self.size


def build_week_calendar(treinos):
    week_start, trained_dates = get_current_week_workout_dates(treinos)
    today = datetime.now().date()
    day_names = ("SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM")
    week_end = week_start + timedelta(days=6)

    calendar = BoxLayout(
        orientation="vertical",
        size_hint_y=None,
        height=126,
        spacing=5,
    )
    calendar.add_widget(secao_titulo("Semana atual", font_size=16, height=22))
    calendar.add_widget(Label(
        text=f"{week_start:%d/%m} a {week_end:%d/%m}",
        font_size=11,
        color=MUTED_COLOR,
        size_hint_y=None,
        height=18,
    ))
    days = BoxLayout(size_hint_y=None, height=66, spacing=5)
    for offset, day_name in enumerate(day_names):
        day_date = week_start + timedelta(days=offset)
        days.add_widget(WeekdayTile(
            day_name,
            day_date.day,
            day_date in trained_dates,
            day_date == today,
        ))
    calendar.add_widget(days)
    return calendar


class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=(24, 36), spacing=18)

        header = BoxLayout(size_hint_y=None, height=54, spacing=8)
        header.add_widget(secao_titulo("Meu treino", font_size=26, height=54))
        settings_button = GearButton(text="", size_hint_x=None, width=48)
        settings_button.bind(on_release=lambda *_: self.abrir_configuracoes())
        header.add_widget(settings_button)
        layout.add_widget(header)
        layout.add_widget(Label(
            text="Escolha uma opção abaixo para começar.",
            color=MUTED_COLOR,
            size_hint_y=None,
            height=30,
        ))

        for title, screen_name, primary in (
            ("Planejamento de Treino", "planning", True),
            ("Treino Semanal", "weekly", False),
            ("Histórico da semana", "history", False),
        ):
            button = make_button(
                title,
                primary=primary,
                size_hint_y=None,
                height=54,
            )
            button.bind(
                on_release=lambda _button, target=screen_name: self.ir_para(target)
            )
            layout.add_widget(button)

        layout.add_widget(BoxLayout())
        self.add_widget(layout)

    def ir_para(self, screen_name):
        self.manager.current = screen_name

    def abrir_configuracoes(self):
        app = App.get_running_app()
        content = BoxLayout(orientation="vertical", padding=16, spacing=12)
        content.add_widget(Label(
            text="Configurações",
            color=TEXT_COLOR,
            size_hint_y=None,
            height=32,
        ))
        clear_button = make_button(
            "Limpar histórico e treinos",
            size_hint_y=None,
            height=46,
        )
        popup = Popup(
            title="",
            content=content,
            size_hint=(0.82, 0.30),
            background_color=BLUE_GREY_900,
            separator_color=DIVIDER_COLOR,
        )
        clear_button.bind(
            on_release=lambda *_: (
                popup.dismiss(),
                app.confirmar_limpeza_completa(),
            )
        )
        content.add_widget(clear_button)
        popup.open()


class PlanningScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.exercicios_area = None
        self.lista_dia = None

    def on_pre_enter(self, *_):
        self.rebuild()

    def rebuild(self):
        app = App.get_running_app()
        self.clear_widgets()
        root = make_page_root()
        root.add_widget(make_page_header(
            "Planejamento de Treino",
            22,
            40,
            100,
            lambda: setattr(self.manager, "current", "menu"),
        ))

        config_card = Card(bg_color=CARD_BG)
        config_card.add_widget(secao_titulo(
            "Quantos dias por semana você vai treinar?"
        ))
        total_text = (
            f"{app.num_dias_treino_selecionados} dias"
            if app.num_dias_treino_selecionados
            else "Selecione"
        )
        total_spinner = make_spinner(
            total_text,
            [f"{number} dias" for number in range(1, 6)],
            size_hint_y=None,
            height=42,
        )
        total_spinner.bind(text=self.on_total_dias_changed)
        config_card.add_widget(total_spinner)
        config_card.add_widget(Divider())
        config_card.add_widget(secao_titulo("Qual dia deseja configurar?"))
        day_labels = [workout.dia_semana for workout in app.treinos_semana]
        app.normalize_day_index()
        selected_day = (
            app.treinos_semana[app.current_selected_day_index].dia_semana
            if app.current_selected_day_index >= 0
            else "Selecione"
        )
        day_spinner = make_spinner(
            selected_day,
            day_labels,
            size_hint_y=None,
            height=42,
        )
        day_spinner.bind(text=self.on_dia_changed)
        config_card.add_widget(day_spinner)
        config_card.add_widget(Divider())
        config_card.add_widget(secao_titulo("Grupo muscular:"))
        group_spinner = make_spinner(
            app.current_selected_muscle_group or "Selecione",
            muscle_groups,
            size_hint_y=None,
            height=42,
        )
        group_spinner.bind(text=self.on_grupo_changed)
        config_card.add_widget(group_spinner)
        root.add_widget(config_card)

        available_card = Card(bg_color=CARD_BG)
        available_card.add_widget(secao_titulo("Exercícios disponíveis"))
        self.exercicios_area = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=8,
        )
        self.exercicios_area.bind(
            minimum_height=self.exercicios_area.setter("height")
        )
        self.build_exercicios_disponiveis()
        available_card.add_widget(self.exercicios_area)
        root.add_widget(available_card)

        list_card = Card(bg_color=CARD_BG_ALT)
        list_card.add_widget(secao_titulo("Treinos adicionados"))
        self.lista_dia = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=6,
        )
        self.lista_dia.bind(minimum_height=self.lista_dia.setter("height"))
        self.build_lista_dia()
        list_card.add_widget(self.lista_dia)
        root.add_widget(list_card)
        self.add_widget(make_scroll(root))

    def on_total_dias_changed(self, _spinner, text):
        app = App.get_running_app()
        count = int(text.split()[0])
        if count != app.num_dias_treino_selecionados:
            app.sync_training_days(count)
            self.rebuild()

    def on_dia_changed(self, _spinner, text):
        app = App.get_running_app()
        app.set_selected_day_by_label(text)
        self.build_lista_dia()
        self.build_exercicios_disponiveis()

    def on_grupo_changed(self, _spinner, text):
        app = App.get_running_app()
        app.current_selected_muscle_group = text
        self.build_exercicios_disponiveis()

    def build_exercicios_disponiveis(self):
        app = App.get_running_app()
        self.exercicios_area.clear_widgets()
        group = app.current_selected_muscle_group
        if group not in predefined_exercises_by_group:
            self.exercicios_area.add_widget(Label(
                text="Selecione um grupo muscular.",
                color=MUTED_COLOR,
                size_hint_y=None,
                height=25,
            ))
            return

        exercises = predefined_exercises_by_group[group]
        if 0 <= app.current_selected_day_index < len(app.treinos_semana):
            names_in_day = {
                exercise.nome
                for exercise in app.treinos_semana[
                    app.current_selected_day_index
                ].exercicios
            }
            available = [
                exercise for exercise in exercises
                if exercise.nome not in names_in_day
            ]
        else:
            available = exercises

        if not available:
            self.exercicios_area.add_widget(Label(
                text="Todos os exercícios deste grupo já estão no dia.",
                size_hint_y=None,
                height=30,
                color=MUTED_COLOR,
            ))
            return

        exercise_spinner = make_spinner(
            available[0].nome,
            [exercise.nome for exercise in available],
            size_hint_y=None,
            height=40,
        )
        series_input = make_input(
            text="3",
            input_filter="int",
            size_hint_y=None,
            height=40,
        )
        reps_input = make_input(
            text="10",
            size_hint_y=None,
            height=40,
        )
        inputs_row = BoxLayout(size_hint_y=None, height=40, spacing=8)
        inputs_row.add_widget(Label(
            text="Séries",
            size_hint_x=None,
            width=50,
            color=MUTED_COLOR,
        ))
        inputs_row.add_widget(series_input)
        inputs_row.add_widget(Label(
            text="Reps",
            size_hint_x=None,
            width=50,
            color=MUTED_COLOR,
        ))
        inputs_row.add_widget(reps_input)

        def confirm_add(*_):
            selected = next(
                (exercise for exercise in available
                 if exercise.nome == exercise_spinner.text),
                None,
            )
            if selected is not None and app.add_predefined_exercise_to_day(
                selected,
                series_input.text,
                reps_input.text,
            ):
                self.build_lista_dia()
                self.build_exercicios_disponiveis()

        add_button = make_button(
            "Adicionar exercício",
            primary=True,
            size_hint_y=None,
            height=42,
        )
        add_button.bind(on_release=confirm_add)
        self.exercicios_area.add_widget(exercise_spinner)
        self.exercicios_area.add_widget(inputs_row)
        self.exercicios_area.add_widget(add_button)

    def build_lista_dia(self):
        app = App.get_running_app()
        self.lista_dia.clear_widgets()
        if not 0 <= app.current_selected_day_index < len(app.treinos_semana):
            self.lista_dia.add_widget(Label(
                text="Selecione um dia para ver os exercícios.",
                color=MUTED_COLOR,
                size_hint_y=None,
                height=25,
            ))
            return

        workout = app.treinos_semana[app.current_selected_day_index]
        if not workout.exercicios:
            self.lista_dia.add_widget(Label(
                text="Nenhum exercício adicionado ainda.",
                color=MUTED_COLOR,
                size_hint_y=None,
                height=25,
            ))
            return

        for index, exercise in enumerate(workout.exercicios):
            row = BoxLayout(size_hint_y=None, height=35, spacing=8)
            row.add_widget(Label(
                text=(
                    f"{exercise.nome} ({exercise.grupo_muscular}): "
                    f"{exercise.series}x{exercise.repeticoes}"
                ),
                color=TEXT_COLOR,
            ))
            remove_button = make_button(
                "Remover",
                size_hint_x=None,
                width=90,
                size_hint_y=None,
                height=32,
            )

            def remove_exercise(_button, exercise_index=index):
                app.remove_exercicio_do_dia(exercise_index)
                self.build_lista_dia()
                self.build_exercicios_disponiveis()

            remove_button.bind(on_release=remove_exercise)
            row.add_widget(remove_button)
            self.lista_dia.add_widget(row)


class WeeklyScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.duracao_label = None

    def on_pre_enter(self, *_):
        self.rebuild()

    def rebuild(self):
        app = App.get_running_app()
        app.normalize_day_index()
        self.clear_widgets()
        self.duracao_label = None
        root = make_page_root()
        root.add_widget(make_page_header(
            "Treino Semanal",
            22,
            40,
            100,
            lambda: setattr(self.manager, "current", "menu"),
        ))
        if not app.treinos_semana:
            notice = Card(bg_color=CARD_BG)
            notice.add_widget(Label(
                text="Nenhum treino planejado ainda.",
                color=MUTED_COLOR,
                size_hint_y=None,
                height=30,
            ))
            plan_button = make_button(
                "Ir para Planejamento",
                primary=True,
                size_hint_y=None,
                height=42,
            )
            plan_button.bind(
                on_release=lambda *_: setattr(self.manager, "current", "planning")
            )
            notice.add_widget(plan_button)
            root.add_widget(notice)
            self.add_widget(make_scroll(root))
            return

        day_labels = [workout.dia_semana for workout in app.treinos_semana]
        selected_day = app.treinos_semana[app.current_selected_day_index].dia_semana
        day_spinner = make_spinner(
            selected_day,
            day_labels,
            disabled=app.workout_session_running,
            size_hint_y=None,
            height=42,
        )
        day_spinner.bind(text=self.on_dia_changed)
        root.add_widget(day_spinner)

        root.add_widget(secao_titulo("Última duração por plano", height=20))
        markers = BoxLayout(size_hint_y=None, height=54, spacing=8)
        for workout in app.treinos_semana:
            completed = bool(workout.last_workout_seconds)
            duration_text = (
                format_duration(workout.last_workout_seconds) if completed else "-"
            )
            marker = Card(
                bg_color=GREEN_700 if completed else CARD_BG_ALT,
                radius=10,
                padding=6,
                spacing=1,
            )
            marker.add_widget(Label(
                text=workout.dia_semana,
                font_size=11,
                color=BLUE_GREY_100,
                size_hint_y=None,
                height=16,
            ))
            marker.add_widget(Label(
                text=duration_text,
                font_size=11,
                bold=True,
                color=TEXT_COLOR,
                size_hint_y=None,
                height=16,
            ))
            markers.add_widget(marker)
        root.add_widget(markers)

        workout = app.treinos_semana[app.current_selected_day_index]
        main_card = Card(bg_color=CARD_BG, padding=18, spacing=12)
        elapsed = app.get_current_workout_elapsed_seconds()
        self.duracao_label = Label(
            text=f"Duração: {format_duration(elapsed)}",
            font_size=20,
            bold=True,
            color=ACCENT,
            size_hint_y=None,
            height=36,
        )
        main_card.add_widget(self.duracao_label)

        buttons = BoxLayout(size_hint_y=None, height=44, spacing=10)
        start_button = make_button(
            "Iniciar treino",
            primary=True,
            disabled=app.workout_session_running,
        )
        start_button.bind(on_release=lambda *_: self._start_workout(app))
        finish_button = make_button(
            "Finalizar treino",
            disabled=not app.workout_session_running,
        )
        finish_button.bind(on_release=lambda *_: app.finish_workout_session())
        buttons.add_widget(start_button)
        buttons.add_widget(finish_button)
        main_card.add_widget(buttons)

        reset_button = make_button(
            "Limpar resumo da semana",
            size_hint_y=None,
            height=38,
        )
        reset_button.bind(on_release=lambda *_: self._reset_week(app))
        main_card.add_widget(reset_button)
        main_card.add_widget(Divider())
        main_card.add_widget(secao_titulo(f"Exercícios de {workout.dia_semana}:"))
        if not workout.exercicios:
            main_card.add_widget(Label(
                text="Nenhum exercício adicionado.",
                color=MUTED_COLOR,
                size_hint_y=None,
                height=25,
            ))
        else:
            for exercise in workout.exercicios:
                row = BoxLayout(size_hint_y=None, height=38, spacing=8)
                row.add_widget(Label(
                    text=(
                        f"{exercise.nome} ({exercise.grupo_muscular}) - "
                        f"{exercise.series}x{exercise.repeticoes}"
                    ),
                    color=TEXT_COLOR,
                    halign="left",
                    valign="middle",
                ))
                video_button = YouTubeButton(
                    text="",
                    size_hint_x=None,
                    width=42,
                    size_hint_y=None,
                    height=32,
                    disabled=not exercise.youtube_link,
                )
                video_button.bind(
                    on_release=lambda _button, url=exercise.youtube_link:
                    app.open_exercise_video(url)
                )
                row.add_widget(video_button)
                main_card.add_widget(row)
        root.add_widget(main_card)
        self.add_widget(make_scroll(root))

    def _start_workout(self, app):
        app.start_workout_session()
        self.rebuild()

    def _reset_week(self, app):
        app.reset_week_markers()
        self.rebuild()

    def on_dia_changed(self, _spinner, text):
        app = App.get_running_app()
        app.set_selected_day_by_label(text)
        self.rebuild()

    def atualizar_duracao(self, *_):
        app = App.get_running_app()
        if self.duracao_label is not None:
            elapsed = app.get_current_workout_elapsed_seconds()
            self.duracao_label.text = f"Duração: {format_duration(elapsed)}"


class HistoryScreen(Screen):
    def on_pre_enter(self, *_):
        self.rebuild()

    def rebuild(self):
        app = App.get_running_app()
        self.clear_widgets()
        root = make_page_root()
        root.add_widget(make_page_header(
            "Histórico da semana",
            21,
            42,
            88,
            lambda: setattr(self.manager, "current", "menu"),
        ))

        calendar_card = Card(bg_color=CARD_BG)
        calendar_card.add_widget(build_week_calendar(app.treinos_semana))
        calendar_card.add_widget(Label(
            text=(
                "Treinos concluídos desde a última limpeza: "
                f"{count_completed_workouts()}"
            ),
            color=ACCENT,
            bold=True,
            size_hint_y=None,
            height=28,
        ))
        root.add_widget(calendar_card)

        sessions = [
            (
                record["finished_at"],
                workout.dia_semana,
                record["seconds"],
            )
            for workout in app.treinos_semana
            for record in workout.history
        ]
        sessions.sort(key=lambda session: session[0], reverse=True)
        sessions_card = Card(bg_color=CARD_BG_ALT)
        sessions_card.add_widget(secao_titulo("Sessões finalizadas"))
        if not sessions:
            sessions_card.add_widget(Label(
                text="Nenhum treino finalizado nesta semana.",
                color=MUTED_COLOR,
                size_hint_y=None,
                height=32,
            ))
        else:
            for finished_at, day_name, seconds in sessions:
                sessions_card.add_widget(Label(
                    text=(
                        f"{day_name}  |  "
                        f"{app.format_iso_to_ddmm_hhmm(finished_at)}  |  "
                        f"{format_duration(seconds)}"
                    ),
                    color=TEXT_COLOR,
                    halign="left",
                    size_hint_y=None,
                    height=30,
                ))
        root.add_widget(sessions_card)
        self.add_widget(make_scroll(root))


class GymApp(App):
    def build(self):
        self.treinos_semana = []
        self.num_dias_treino_selecionados = 0
        self.current_selected_day_index = -1
        self.current_selected_muscle_group = ""
        self.workout_session_started = None
        self.workout_session_finished = None
        self.workout_session_running = False
        self.workout_session_dia = None
        self.timer_event = None

        if platform == "android":
            configure_database(os.path.join(self.user_data_dir, DB_FILE_NAME))
        create_tables()
        self.treinos_semana = load_all_treinos()
        if self.treinos_semana:
            self.num_dias_treino_selecionados = len(self.treinos_semana)
            self.current_selected_day_index = 0
            changed = False
            for workout in self.treinos_semana:
                if (
                    workout.last_workout_finished_at
                    and not is_same_iso_week(workout.last_workout_finished_at)
                ):
                    workout.last_workout_finished_at = None
                    workout.last_workout_seconds = 0
                    changed = True
            if changed:
                save_all_treinos(self.treinos_semana)

        self.screen_manager = ScreenManager(transition=NoTransition())
        self.weekly_screen = WeeklyScreen(name="weekly")
        self.screen_manager.add_widget(MenuScreen(name="menu"))
        self.screen_manager.add_widget(PlanningScreen(name="planning"))
        self.screen_manager.add_widget(self.weekly_screen)
        self.screen_manager.add_widget(HistoryScreen(name="history"))
        return self.screen_manager

    def on_stop(self):
        if hasattr(self, "treinos_semana"):
            save_all_treinos(self.treinos_semana)

    def normalize_day_index(self):
        if not self.treinos_semana:
            self.current_selected_day_index = -1
        elif self.current_selected_day_index < 0:
            self.current_selected_day_index = 0
        elif self.current_selected_day_index >= len(self.treinos_semana):
            self.current_selected_day_index = len(self.treinos_semana) - 1

    def set_selected_day_by_label(self, day_label):
        if not day_label or not self.treinos_semana:
            self.current_selected_day_index = -1
            return
        for index, workout in enumerate(self.treinos_semana):
            if workout.dia_semana == day_label:
                self.current_selected_day_index = index
                return
        self.current_selected_day_index = 0

    def sync_training_days(self, new_count):
        new_count = min(max(int(new_count), 0), 5)
        while len(self.treinos_semana) < new_count:
            self.treinos_semana.append(
                TreinoDiario(f"Dia {len(self.treinos_semana) + 1}")
            )
        while len(self.treinos_semana) > new_count:
            self.treinos_semana.pop()
        for index, workout in enumerate(self.treinos_semana):
            workout.dia_semana = f"Dia {index + 1}"
        self.num_dias_treino_selecionados = len(self.treinos_semana)
        self.current_selected_day_index = 0 if self.treinos_semana else -1
        save_all_treinos(self.treinos_semana)

    def add_predefined_exercise_to_day(self, exercise, series, repetitions):
        if not 0 <= self.current_selected_day_index < len(self.treinos_semana):
            self.show_message("Selecione um dia de treino antes de adicionar.")
            return False
        try:
            series_value = parse_series(series)
            reps_value = parse_reps(repetitions)
        except ValueError as error:
            self.show_message(str(error))
            return False

        new_exercise = Exercicio(
            exercise.nome,
            exercise.youtube_link,
            series_value,
            reps_value,
            exercise.grupo_muscular,
        )
        self.treinos_semana[self.current_selected_day_index].adicionar_exercicio(
            new_exercise
        )
        save_all_treinos(self.treinos_semana)
        self.show_message(f"Exercício '{new_exercise.nome}' adicionado.")
        return True

    def remove_exercicio_do_dia(self, index):
        if not 0 <= self.current_selected_day_index < len(self.treinos_semana):
            return
        workout = self.treinos_semana[self.current_selected_day_index]
        if 0 <= index < len(workout.exercicios):
            del workout.exercicios[index]
            save_all_treinos(self.treinos_semana)

    def format_iso_to_ddmm_hhmm(self, iso_timestamp):
        if not iso_timestamp:
            return "-"
        parsed = parse_iso(iso_timestamp)
        return parsed.strftime("%d/%m -- %H:%M") if parsed else iso_timestamp

    def get_current_workout_elapsed_seconds(self):
        if self.workout_session_started is None:
            return 0
        if self.workout_session_running:
            end_time = datetime.now()
        elif self.workout_session_finished is not None:
            end_time = self.workout_session_finished
        else:
            return 0
        return max(0, int((end_time - self.workout_session_started).total_seconds()))

    def start_workout_session(self):
        if not 0 <= self.current_selected_day_index < len(self.treinos_semana):
            self.show_message("Selecione um dia para iniciar o treino.")
            return
        if self.workout_session_running:
            return
        self.workout_session_dia = self.treinos_semana[
            self.current_selected_day_index
        ]
        self.workout_session_started = datetime.now()
        self.workout_session_finished = None
        self.workout_session_running = True
        self.timer_event = Clock.schedule_interval(
            self.weekly_screen.atualizar_duracao,
            1,
        )

    def finish_workout_session(self):
        if self.workout_session_started is None or not self.workout_session_running:
            return
        self.workout_session_running = False
        self.workout_session_finished = datetime.now()
        if self.timer_event is not None:
            self.timer_event.cancel()
            self.timer_event = None

        duration_seconds = self.get_current_workout_elapsed_seconds()
        workout = self.workout_session_dia
        self.workout_session_dia = None
        if workout is not None and workout in self.treinos_semana:
            finished_at = self.workout_session_finished.isoformat()
            workout.last_workout_seconds = duration_seconds
            workout.last_workout_finished_at = finished_at
            workout.history.insert(
                0,
                {"seconds": duration_seconds, "finished_at": finished_at},
            )
            add_workout_history_by_dia(
                workout.dia_semana,
                duration_seconds,
                finished_at,
            )
        else:
            self.show_message(
                "O dia deste treino foi removido; a sessão não foi salva."
            )
        self.screen_manager.current = "history"

    def reset_week_markers(self):
        changed = False
        for workout in self.treinos_semana:
            if workout.last_workout_finished_at or workout.last_workout_seconds:
                workout.last_workout_finished_at = None
                workout.last_workout_seconds = 0
                changed = True
        if changed:
            save_all_treinos(self.treinos_semana)

    def show_message(self, text):
        popup = Popup(
            title="",
            content=Label(text=text, color=TEXT_COLOR),
            size_hint=(0.8, 0.2),
            background_color=BLUE_GREY_900,
            separator_color=DIVIDER_COLOR,
        )
        popup.open()
        Clock.schedule_once(lambda *_: popup.dismiss(), 2)

    def confirmar_limpeza_completa(self):
        content = BoxLayout(orientation="vertical", padding=16, spacing=12)
        content.add_widget(Label(
            text=(
                "A limpeza completa apagará todos os treinos adicionados "
                "e todo o histórico. Deseja continuar?"
            ),
            color=TEXT_COLOR,
            halign="center",
        ))
        buttons = BoxLayout(size_hint_y=None, height=44, spacing=10)
        popup = Popup(
            title="Confirmar limpeza completa",
            content=content,
            size_hint=(0.88, 0.40),
            auto_dismiss=False,
            background_color=BLUE_GREY_900,
            separator_color=DIVIDER_COLOR,
            title_color=TEXT_COLOR,
        )
        cancel_button = make_button("Cancelar")
        clear_button = make_button("Limpar tudo", primary=True)
        cancel_button.bind(on_release=lambda *_: popup.dismiss())
        clear_button.bind(
            on_release=lambda *_: (popup.dismiss(), self.limpar_todos_os_dados())
        )
        buttons.add_widget(cancel_button)
        buttons.add_widget(clear_button)
        content.add_widget(buttons)
        popup.open()

    def limpar_todos_os_dados(self):
        clear_all_training_data()
        if self.timer_event is not None:
            self.timer_event.cancel()
            self.timer_event = None
        self.treinos_semana = []
        self.num_dias_treino_selecionados = 0
        self.current_selected_day_index = -1
        self.current_selected_muscle_group = ""
        self.workout_session_started = None
        self.workout_session_finished = None
        self.workout_session_running = False
        self.workout_session_dia = None
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
                activity.startActivity(
                    intent(intent.ACTION_VIEW, uri.parse(url))
                )
            else:
                webbrowser.open(url)
        except Exception as error:
            self.show_message(f"Não foi possível abrir o vídeo: {error}")


if __name__ == "__main__":
    GymApp().run()
