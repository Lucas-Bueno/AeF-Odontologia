import flet as ft
import sqlite3
import requests
import threading
from abc import ABC, abstractmethod

# ==========================================
# CAMADA DE DADOS (Aplicando SOLID)
# ==========================================
class IRepository(ABC):
    @abstractmethod
    def execute(self, query: str, params: tuple = ()): pass
    @abstractmethod
    def fetch(self, query: str, params: tuple = ()): pass

class SQLiteRepository(IRepository):
    def __init__(self, db_name="clinica_local.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        # Tabelas essenciais normalizadas
        self.cursor.executescript("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT, documento TEXT, celular TEXT, endereco TEXT
            );
            CREATE TABLE IF NOT EXISTS dentistas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT, cro TEXT, celular TEXT, especialidade TEXT
            );
            CREATE TABLE IF NOT EXISTS procedimentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT, duracao_minutos INTEGER
            );
            CREATE TABLE IF NOT EXISTS agendamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER, dentista_id INTEGER,
                data_hora TEXT, procedimento TEXT, observacoes TEXT,
                status TEXT DEFAULT 'Agendado'
            );
        """)
        self.conn.commit()

    def execute(self, query: str, params: tuple = ()):
        self.cursor.execute(query, params)
        self.conn.commit()
        return self.cursor.lastrowid

    def fetch(self, query: str, params: tuple = ()):
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

# ==========================================
# INTEGRAÇÃO WHATSAPP (Webhook Assíncrono)
# ==========================================
def enviar_mensagem_whatsapp(celular, mensagem):
    # Exemplo genérico de webhook (Evolution API, Z-API, etc)
    webhook_url = "https://seu-servidor-webhook.com/api/send"
    payload = {
        "number": celular,
        "message": mensagem
    }
    try:
        # requests.post(webhook_url, json=payload, timeout=5)
        print(f"[Webhook Fake] Mensagem enviada para {celular}: {mensagem}")
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

# ==========================================
# INTERFACE GRÁFICA (Flet - UX)
# ==========================================
def main(page: ft.Page):
    page.title = "Clínica Ágil"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 400
    page.window_height = 700
    page.padding = 20
    
    # Atualizado para ft.Colors no Flet 1.0+
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.TEAL)

    db = SQLiteRepository()

    # --- Componentes de UI ---
    
    def renderizar_dashboard():
        agendamentos = db.fetch("SELECT * FROM agendamentos ORDER BY data_hora DESC LIMIT 5")
        
        lista_cards = []
        for ag in agendamentos:
            # ag = (id, cliente_id, dentista_id, data_hora, procedimento, obs, status)
            card = ft.Card(
                elevation=4,
                content=ft.Container(
                    padding=15,
                    content=ft.Column([
                        ft.Text(f"📅 {ag[3]} - {ag[4]}", weight=ft.FontWeight.BOLD, size=16),
                        ft.Text(f"Observações: {ag[5]}", color=ft.Colors.GREY_700),
                        ft.Row([
                            ft.Chip(
                                label=ft.Text(ag[6], color=ft.Colors.WHITE), 
                                bgcolor=ft.Colors.AMBER_700 if ag[6] == 'Agendado' else ft.Colors.GREEN_600
                            ),
                            ft.IconButton(
                                icon=ft.Icons.MESSAGE, 
                                tooltip="Enviar Lembrete WhatsApp",
                                icon_color=ft.Colors.GREEN,
                                on_click=lambda e: disparar_lembrete_manual()
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ])
                )
            )
            lista_cards.append(card)
            
        if not lista_cards:
            lista_cards.append(ft.Text("Nenhum agendamento para hoje.", italic=True))
            
        return ft.Column([
            ft.Text("Consultas Recentes", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL),
            ft.Divider(),
            *lista_cards
        ], scroll=ft.ScrollMode.AUTO, expand=True)

    def disparar_lembrete_manual():
        # Executa a requisição em background usando threading para NÃO congelar a tela do celular
        t = threading.Thread(target=enviar_mensagem_whatsapp, args=("5511999999999", "Olá! Lembramos da sua consulta amanhã no consultório."))
        t.start()
        
        snack = ft.SnackBar(ft.Text("Enviando mensagem via Webhook..."), bgcolor=ft.Colors.GREEN)
        page.overlay.append(snack)
        snack.open = True
        page.update()

    # --- View de Novo Agendamento ---
    input_data = ft.TextField(label="Data e Hora (DD/MM/YYYY HH:MM)", prefix_icon=ft.Icons.CALENDAR_MONTH)
    input_procedimento = ft.Dropdown(
        label="Procedimento",
        options=[
            ft.dropdown.Option("Limpeza"),
            ft.dropdown.Option("Extração"),
            ft.dropdown.Option("Canal"),
            ft.dropdown.Option("Avaliação Inicial")
        ]
    )
    input_obs = ft.TextField(label="Observações", multiline=True)

    def salvar_agendamento(e):
        if not input_data.value or not input_procedimento.value:
            return
        
        db.execute(
            "INSERT INTO agendamentos (cliente_id, dentista_id, data_hora, procedimento, observacoes) VALUES (?, ?, ?, ?, ?)",
            (1, 1, input_data.value, input_procedimento.value, input_obs.value)
        )
        input_data.value = ""
        input_procedimento.value = None
        input_obs.value = ""
        atualizar_tela(0) # Volta para dashboard

    view_agendamento = ft.Column([
        ft.Text("Novo Agendamento", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL),
        input_data,
        input_procedimento,
        input_obs,
        ft.ElevatedButton(
            "Salvar Consulta", 
            icon=ft.Icons.SAVE, 
            on_click=salvar_agendamento, 
            width=400, 
            style=ft.ButtonStyle(bgcolor=ft.Colors.TEAL, color=ft.Colors.WHITE)
        )
    ], expand=True)

    # --- Navegação Bottom ---
    area_conteudo = ft.Container(content=renderizar_dashboard(), expand=True)

    def atualizar_tela(index):
        if index == 0:
            area_conteudo.content = renderizar_dashboard()
        elif index == 1:
            area_conteudo.content = view_agendamento
        page.update()

    bottom_nav = ft.NavigationBar(
        destinations=[
            ft.NavigationDestination(icon=ft.Icons.DASHBOARD, label="Dashboard"),
            ft.NavigationDestination(icon=ft.Icons.ADD_ALARM, label="Agendar"),
            ft.NavigationDestination(icon=ft.Icons.PEOPLE, label="Cadastros"),
        ],
        on_change=lambda e: atualizar_tela(e.control.selected_index)
    )

    page.add(area_conteudo, bottom_nav)

# Try/Except para garantir compatibilidade dependendo de como o Serious Python envelopa o Flet no Android
if __name__ == "__main__":
    try:
        ft.app(target=main)
    except AttributeError:
        ft.run(main)
