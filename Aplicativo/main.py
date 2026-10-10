"""
Controle Financeiro — NovaVoid Studio (v3.4)

Instalar:  sudo apt install python3-tk
           pip install customtkinter matplotlib --break-system-packages
Rodar:     python3 controle_financeiro_v3.py

Dados: ~/.local/share/Financas/financas.json (Linux) ou %APPDATA%\\Financas (Windows).
Lê automaticamente os dados da V1/V2. Uma cópia por dia fica em .../Financas/backups (últimas 14).

Tela principal: calendário mensal dia a dia (entradas, saídas e saldo de cada dia),
com totais por dia da semana e simulação de "e se a diária não cair?".

Atalhos: Enter (salvar), Esc (cancelar edição / sair da tela cheia), Delete (excluir),
         Ctrl+Z (desfazer exclusão), Ctrl+N (novo lançamento),
         F11 (tela cheia), F1 (guia rápido), F2 (ajustes: diária padrão e reserva mínima).
"""
import calendar
import csv
import json
import os
import re
import shutil
import traceback
import uuid
import tkinter as tk
import tkinter.font as tkfont
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from tkinter import ttk, messagebox, filedialog

import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

EMPRESA = "NovaVoid Studio"
APP = "Controle Financeiro"
VERSAO = "3.4"
MAX_LOTE = 400  # máximo de lançamentos criados de uma vez por uma repetição
MAX_DESC = 80   # tamanho máximo da descrição
MAX_CAT = 30    # tamanho máximo do nome de categoria


def pasta_dados() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    p = base / "Financas"
    p.mkdir(parents=True, exist_ok=True)
    return p


PASTA = pasta_dados()
ARQUIVO = PASTA / "financas.json"
LEGADO = Path(__file__).resolve().with_name("financas.json")  # arquivo da V1

CAT_DESPESA = ["Moradia", "Alimentação", "Transporte", "Saúde", "Lazer",
               "Educação", "Contas", "Outros"]
CAT_RECEITA = ["Diária", "Salário", "Freelance", "Vendas", "Investimentos", "Outros"]
DIAS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
DIAS_LONGOS = ["Domingo", "Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
               "Sexta-feira", "Sábado"]
PLURAL = ["domingos", "segundas", "terças", "quartas", "quintas", "sextas", "sábados"]
MODOS_REP = ["Não repetir", "Todo mês", "Toda semana", "Dias da semana escolhidos"]
MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto",
         "Setembro", "Outubro", "Novembro", "Dezembro"]
TITULOS = {"data": "Data", "tipo": "Tipo", "categoria": "Categoria",
           "descricao": "Descrição", "valor": "Valor", "status": "Status"}

# ---------- paleta: preto + azul + roxo + branco  [claro, escuro] ----------
BG = ["#ffffff", "#000000"]
PAINEL = ["#f3f1fb", "#08080d"]
CARTAO = ["#ffffff", "#10101a"]
CAMPO = ["#ffffff", "#0c0c14"]
BORDA = ["#cfd0f0", "#25254a"]
SUAVE = ["#e6e4fa", "#191930"]
TEXTO = ["#0a0a14", "#ffffff"]
MUTED = ["#5b5f8f", "#9a9fcf"]
ROXO = ["#7c3aed", "#8b5cf6"]
ROXO_H = ["#6d28d9", "#7c3aed"]
ROXO_TXT = ["#6d28d9", "#a78bfa"]
ROXO_ESC = ["#6d28d9", "#5b21b6"]
ROXO_ESC_H = ["#5b21b6", "#4c1d95"]
ROXO_SEL = ["#a78bfa", "#8b5cf6"]
ROXO_SEL_H = ["#9575f5", "#7c3aed"]
AZUL = ["#2563eb", "#2563eb"]
AZUL_H = ["#1d4ed8", "#1d4ed8"]
AZUL_TXT = ["#1d4ed8", "#60a5fa"]
SEG_TXT = ["#0a0a14", "#ffffff"]
BRANCO = ["#ffffff", "#ffffff"]
PALETA = ["#8b5cf6", "#3b82f6", "#a78bfa", "#60a5fa", "#c4b5fd", "#93c5fd", "#6d28d9", "#1d4ed8"]


def pick(cor, escuro):
    return cor[1] if escuro else cor[0]


def aplicar_tema_cores():
    """Sobrescreve o tema padrão do CustomTkinter com a paleta preto/azul/roxo/branco."""
    T = ctk.ThemeManager.theme

    def up(w, **kw):
        if w in T:
            for k, v in kw.items():
                if k in T[w]:
                    T[w][k] = v

    up("CTk", fg_color=BG)
    up("CTkToplevel", fg_color=BG)
    up("CTkFrame", fg_color=PAINEL, top_fg_color=CARTAO, border_color=BORDA)
    up("CTkButton", fg_color=ROXO, hover_color=ROXO_H, text_color=BRANCO)
    up("CTkLabel", text_color=TEXTO)
    up("CTkEntry", fg_color=CAMPO, border_color=BORDA, text_color=TEXTO, placeholder_text_color=MUTED)
    up("CTkCheckBox", fg_color=AZUL, hover_color=AZUL_H, border_color=ROXO, text_color=TEXTO)
    up("CTkSwitch", fg_color=SUAVE, progress_color=ROXO, button_color=BRANCO,
       button_hover_color=["#f0eaff", "#f0eaff"], text_color=TEXTO)
    up("CTkProgressBar", fg_color=SUAVE, progress_color=AZUL)
    up("CTkOptionMenu", fg_color=ROXO, button_color=ROXO_H,
       button_hover_color=["#5b21b6", "#6d28d9"], text_color=BRANCO)
    up("CTkComboBox", fg_color=CAMPO, border_color=BORDA, button_color=ROXO,
       button_hover_color=ROXO_H, text_color=TEXTO)
    up("CTkScrollbar", button_color=BORDA, button_hover_color=ROXO)
    up("CTkSegmentedButton", fg_color=SUAVE, selected_color=ROXO_SEL, selected_hover_color=ROXO_SEL_H,
       unselected_color=SUAVE, unselected_hover_color=BORDA, text_color=SEG_TXT)
    up("DropdownMenu", fg_color=CARTAO, hover_color=SUAVE, text_color=TEXTO)


ctk.set_default_color_theme("blue")
aplicar_tema_cores()


# ---------- utilidades (dinheiro em centavos inteiros: sem erro de float) ----------
def brl(c: int) -> str:
    sinal = "-" if c < 0 else ""
    reais, cent = divmod(abs(c), 100)
    return f"{sinal}R$ {reais:,}".replace(",", ".") + f",{cent:02d}"


def fmt_input(c: int) -> str:
    return f"{c // 100},{c % 100:02d}"


def compacto(c: int) -> str:
    """Valor curto para as células do calendário (sem R$ e sem sinal; sem centavos a partir de R$ 1.000)."""
    c = abs(c)
    if c >= 100000:
        return f"{(c + 50) // 100:,}".replace(",", ".")
    reais, cent = divmod(c, 100)
    return f"{reais:,}".replace(",", ".") + (f",{cent:02d}" if cent else "")


_RE_MILHAR = re.compile(r"^\d{1,3}(\.\d{3})+(,\d{1,2})?$")  # 1.250 | 1.250,90
_RE_SIMPLES = re.compile(r"^\d+([.,]\d{1,2})?$")             # 1250 | 1250,9 | 1250.90


def parse_centavos(txt: str) -> int:
    """Converte '1.250,90', '1250,90', '1250.90' ou 'R$ 15' em centavos. Levanta ValueError se inválido."""
    t = txt.replace("R$", "").replace(" ", "").strip()
    if _RE_MILHAR.match(t):
        t = t.replace(".", "").replace(",", ".")
    elif _RE_SIMPLES.match(t):
        t = t.replace(",", ".")
    else:
        raise ValueError
    v = Decimal(t)
    if v <= 0 or v > Decimal("1000000000"):
        raise ValueError
    return int((v * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def parse_data(txt: str) -> date:
    """Aceita dd/mm/aaaa, dd/mm/aa, dd/mm (ano atual), aaaa-mm-dd, 'hoje', 'ontem' e 'amanhã'."""
    txt = txt.strip().lower()
    atalhos = {"hoje": 0, "ontem": -1, "amanha": 1, "amanhã": 1}
    if txt in atalhos:
        return date.today() + timedelta(days=atalhos[txt])
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", txt):
        return date.fromisoformat(txt)
    partes = [p.strip() for p in txt.replace("-", "/").replace(".", "/").split("/")]
    if len(partes) == 2:
        partes.append(str(date.today().year))
    if len(partes) != 3 or not all(p.isdigit() for p in partes):
        raise ValueError
    d, m, a = (int(p) for p in partes)
    return date(a + 2000 if a < 100 else a, m, d)


def add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def vencido(d: dict) -> bool:
    return not d["pago"] and d["data"] < date.today().isoformat()


def status_txt(d: dict) -> str:
    if d["pago"]:
        return "✓ Recebido" if d["tipo"] == "Receita" else "✓ Pago"
    return "! Vencido" if vencido(d) else "○ Pendente"


def normalizar_lancamento(d, ids_usados: set):
    """Valida um lançamento lido do arquivo. Devolve um dict limpo ou None se for inválido."""
    try:
        tipo = d.get("tipo")
        if tipo not in ("Receita", "Despesa"):
            return None
        cents = int(d["centavos"]) if "centavos" in d else int(round(float(d["valor"]) * 100))
        if cents <= 0:
            return None
        data = date.fromisoformat(str(d["data"])[:10]).isoformat()
        ident = str(d.get("id") or "")
        if not ident or ident in ids_usados:  # V1 podia não ter id (ou repetir)
            ident = uuid.uuid4().hex
        ids_usados.add(ident)
        novo = {"id": ident, "tipo": tipo, "data": data, "centavos": cents,
                "descricao": (str(d.get("descricao") or "").strip() or "(sem descrição)")[:MAX_DESC],
                "categoria": (str(d.get("categoria") or "").strip() or "Outros")[:MAX_CAT],
                "pago": bool(d.get("pago", True))}
        if d.get("serie"):  # liga os lançamentos criados juntos por uma repetição
            novo["serie"] = str(d["serie"])[:64]
        return novo
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return None


def efeito_previsto(d: dict, hoje: str, simular: bool) -> int:
    """Quanto o lançamento mexe no caixa previsto (centavos, com sinal).
    Pago conta sempre. Despesa pendente conta (ainda vai ser paga). Receita pendente só conta
    se ainda é esperada (data de hoje em diante) e não estiver simulando 'a diária não caiu'."""
    c = d["centavos"]
    if d["pago"]:
        return c if d["tipo"] == "Receita" else -c
    if d["tipo"] == "Despesa":
        return -c
    return c if (d["data"] >= hoje and not simular) else 0


def csv_seguro(t: str) -> str:
    """Impede que Excel/LibreOffice interprete texto como fórmula (=, +, -, @)."""
    return "'" + t if t[:1] in ("=", "+", "-", "@", "\t", "\r") else t


def csv_limpo(t: str) -> str:
    return t[1:] if t[:1] == "'" and t[1:2] in ("=", "+", "-", "@") else t


# ---------- logo minimalista da NovaVoid (anel roxo/azul cortado por uma lâmina branca) ----------
def desenhar_logo(cv: tk.Canvas, bg: str, tam: int = 46):
    cv.delete("all")
    cv.configure(bg=bg)
    p = 6
    caixa = (p, p, tam - p, tam - p)
    # metade superior-esquerda roxa, inferior-direita azul (divididas pela diagonal)
    cv.create_arc(*caixa, start=45, extent=180, style="arc", outline="#8b5cf6", width=5)
    cv.create_arc(*caixa, start=225, extent=180, style="arc", outline="#3b82f6", width=5)
    # lâmina branca que corta o anel
    cv.create_line(3, tam - 3, tam - 3, 3, fill=bg, width=6, capstyle="round")
    cv.create_line(3, tam - 3, tam - 3, 3, fill="#ffffff", width=2, capstyle="round")


def criar_icone(n: int = 64) -> tk.PhotoImage:
    """Ícone da janela, desenhado pixel a pixel (sem arquivos externos)."""
    img = tk.PhotoImage(width=n, height=n)
    c = (n - 1) / 2
    r_out, r_in, comp = n * 0.42, n * 0.29, n * 0.48
    for y in range(n):
        for x in range(n):
            dx, dy = x - c, y - c
            r = (dx * dx + dy * dy) ** 0.5
            d = (dx + dy) / 1.41421
            s = (dx - dy) / 1.41421
            w = 1.4 * (1 - abs(s) / comp) if abs(s) <= comp else -1
            if abs(s) <= comp and abs(d) <= w:
                img.put("#ffffff", (x, y))
            elif r_in <= r <= r_out and abs(d) > w + 1.6:
                img.put("#8b5cf6" if d < 0 else "#3b82f6", (x, y))
    return img


# ---------- dicas ao passar o mouse ----------
class Dica:
    def __init__(self, widget, texto):
        self.w, self.t, self.tip, self._id = widget, texto, None, None
        try:
            widget.bind("<Enter>", self.agendar, add="+")
            widget.bind("<Leave>", self.esconder, add="+")
            widget.bind("<ButtonPress>", self.esconder, add="+")
        except (NotImplementedError, ValueError, tk.TclError):
            pass  # alguns widgets do customtkinter (ex.: SegmentedButton) não aceitam bind

    def agendar(self, _e=None):
        self.esconder()
        self._id = self.w.after(600, self.mostrar)

    def mostrar(self):
        self._id = None
        try:
            x = self.w.winfo_rootx() + 12
            y = self.w.winfo_rooty() + self.w.winfo_height() + 6
            self.tip = tk.Toplevel(self.w)
            self.tip.wm_overrideredirect(True)
            self.tip.wm_geometry(f"+{x}+{y}")
            tk.Label(self.tip, text=self.t, bg="#191930", fg="#ffffff", relief="solid", bd=1,
                     padx=8, pady=4, justify="left", wraplength=260).pack()
        except tk.TclError:
            self.tip = None

    def esconder(self, _e=None):
        if self._id:
            try:
                self.w.after_cancel(self._id)
            except tk.TclError:
                pass
            self._id = None
        if self.tip:
            try:
                self.tip.destroy()
            except tk.TclError:
                pass
            self.tip = None


# ---------- guia rápido (tutorial dentro do programa) ----------
PASSOS = [
    ("Bem-vindo! 👋",
     "Este programa ajuda você a enxergar o seu dinheiro DIA A DIA, como um calendário.\n\n"
     "Foi pensado para quem recebe por diária ou tem renda que varia: você anota o que entra "
     "e o que sai em cada dia, e o programa mostra quanto sobra no fim de cada dia e o que "
     "acontece se uma diária não cair.\n\n"
     "Este guia leva 2 minutos. Use os botões abaixo ou as setas ← → do teclado.\n"
     "Para abrir de novo depois, aperte F1."),
    ("1. O calendário do mês",
     "A tela principal é um calendário. Cada dia mostra:\n\n"
     "• o número do dia (● marca hoje)\n"
     "• +valor = o que entrou (azul)\n"
     "• −valor = o que saiu (roxo)\n"
     "• o número pequeno no canto = quanto sobra no fim daquele dia\n\n"
     "Símbolos: ○ previsto (ainda não aconteceu) · ! vencido ou saldo negativo · "
     "✕ diária que não está sendo contada.\n\n"
     "Use ◀ ▶ lá em cima para trocar de mês e o botão Hoje para voltar."),
    ("2. Dias da semana",
     "Acima das colunas, cada dia da semana mostra quantos dias existem no mês e o total "
     "que entrou e saiu neles. Ex.: 'Ter ×4' = 4 terças-feiras.\n\n"
     "Clique em 'Dom', 'Ter'... e o painel da direita lista TODOS os lançamentos daquele dia "
     "da semana no mês, com a média. Ótimo para ver em quais dias você mais ganha ou gasta."),
    ("3. Lançar uma diária ou um gasto",
     "1) Clique no dia no calendário.\n"
     "2) No painel da direita, clique em ＋ Diária ou ＋ Gasto.\n"
     "3) O formulário da esquerda já vem com a data do dia. Digite o valor e clique em "
     "Adicionar.\n\n"
     "Dica: em ⚙ Ajustes (ou F2) você define o VALOR PADRÃO DA DIÁRIA. Aí o ＋ Diária já vem "
     "com o valor preenchido e basta apertar Enter.\n\n"
     "A caixinha 'Já pago / recebido' diz se o dinheiro já caiu. Diária que ainda não caiu? "
     "Desmarque: ela fica Pendente (○) até você marcar como recebida."),
    ("4. E se a diária não cair?",
     "Em cima do calendário ficam três avisos:\n\n"
     "• Em caixa hoje: o dinheiro que você realmente tem.\n"
     "• Fôlego: por quantos dias esse dinheiro dura no ritmo de gastos dos últimos 30 dias.\n"
     "• Menor saldo previsto: o pior dia do mês. Se ficar negativo (!), vai faltar dinheiro.\n\n"
     "Em ⚙ Ajustes você também pode definir uma RESERVA MÍNIMA (ex.: R$ 100). Os dias em que o "
     "saldo previsto ficar abaixo dela aparecem com ⚠, e um aviso diz em quantos dias isso "
     "acontece (ou quando o dinheiro acaba).\n\n"
     "Ligue o interruptor 'E se a diária não cair?' para ver o mês sem contar nenhuma diária "
     "pendente. Diárias de dias que já passaram e não foram marcadas como recebidas também "
     "não são contadas (✕)."),
    ("5. Repetir lançamentos",
     "Na caixa 'Repetição', ao criar um lançamento, escolha:\n\n"
     "• Todo mês: aluguel, internet... (ex.: 12 meses). Vira (1/12), (2/12)...\n"
     "• Toda semana: no mesmo dia da semana da data (ex.: 8 semanas).\n"
     "• Dias da semana escolhidos: marque os dias (ex.: Seg–Sex) e quantas semanas. "
     "Ótimo para passagem e marmita, ou diárias combinadas.\n\n"
     "Os lançamentos futuros ficam Pendentes automaticamente. Ao excluir um deles, o programa "
     "pergunta se você quer apagar só ele ou ele e os seguintes."),
    ("6. Marcar como pago, editar e excluir",
     "Clique em um lançamento no painel do dia (ou na aba Lançamentos) e use os botões:\n\n"
     "• ✓ Pago / Pendente: troca o status\n"
     "• ✏ Editar (ou dê dois cliques)\n"
     "• 🗑 Excluir (Ctrl+Z desfaz)\n\n"
     "Azul = receita · Roxo = despesa · Branco em negrito = vencido."),
    ("7. Lançamentos, Gráficos e Metas",
     "As outras abas continuam aqui:\n\n"
     "• Lançamentos: lista completa com busca e filtros.\n"
     "• Gráficos: para onde vai o seu dinheiro.\n"
     "• Metas: limite mensal por categoria. Barra azul = tranquilo, roxa = passou de 80%, "
     "branca = estourou."),
    ("8. Seus dados e dicas",
     "• Tudo é salvo automaticamente, com cópia de segurança (.bak).\n"
     "• Exportar CSV abre no Excel ou LibreOffice; Importar CSV traz planilhas.\n"
     "• O interruptor 'Modo escuro' troca o tema.\n"
     "• F11 liga a tela cheia (Esc sai) · F1 abre este guia.\n\n"
     "Pronto! Clique em Concluir e comece a usar. 🚀"),
]


class Tutorial(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.i = 0
        self.title("Guia rápido")
        self.resizable(False, False)
        w, h = 620, 520
        x = max(0, app.winfo_rootx() + (app.winfo_width() - w) // 2)
        y = max(0, app.winfo_rooty() + (app.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.transient(app)
        self.protocol("WM_DELETE_WINDOW", self.fechar)

        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(fill="x", padx=28, pady=(22, 0))
        self.l_passo = ctk.CTkLabel(topo, text="", text_color=MUTED)
        self.l_passo.pack(anchor="w")
        self.l_titulo = ctk.CTkLabel(topo, text="", anchor="w", wraplength=560,
                                     font=ctk.CTkFont(size=24, weight="bold"))
        self.l_titulo.pack(anchor="w", pady=(4, 8))
        self.barra = ctk.CTkProgressBar(topo, height=8)
        self.barra.pack(fill="x")

        self.l_texto = ctk.CTkLabel(self, text="", justify="left", anchor="nw", wraplength=560,
                                    font=ctk.CTkFont(size=14))
        self.l_texto.pack(fill="both", expand=True, padx=28, pady=18)

        rod = ctk.CTkFrame(self, fg_color="transparent")
        rod.pack(fill="x", padx=28, pady=(0, 22))
        ctk.CTkButton(rod, text="Pular guia", width=100, fg_color="transparent", border_width=1,
                      border_color=BORDA, text_color=TEXTO, hover_color=SUAVE,
                      command=self.fechar).pack(side="left")
        self.b_prox = ctk.CTkButton(rod, text="Próximo ▶", width=130, height=36, fg_color=AZUL,
                                    hover_color=AZUL_H, command=self.proximo)
        self.b_prox.pack(side="right")
        self.b_ant = ctk.CTkButton(rod, text="◀ Anterior", width=110, height=36, fg_color=SUAVE,
                                   hover_color=BORDA, text_color=TEXTO, command=self.anterior)
        self.b_ant.pack(side="right", padx=8)

        self.bind("<Right>", lambda e: self.proximo())
        self.bind("<Return>", lambda e: self.proximo())
        self.bind("<Left>", lambda e: self.anterior())
        self.bind("<Escape>", lambda e: self.fechar())
        self.mostrar()
        self.after(200, self._foco)

    def _foco(self):
        try:
            self.lift()
            self.focus_force()
        except tk.TclError:
            pass

    def mostrar(self):
        titulo, texto = PASSOS[self.i]
        n = len(PASSOS)
        self.l_passo.configure(text=f"Passo {self.i + 1} de {n}")
        self.l_titulo.configure(text=titulo)
        self.l_texto.configure(text=texto)
        self.barra.set((self.i + 1) / n)
        self.b_ant.configure(state="normal" if self.i else "disabled")
        self.b_prox.configure(text="Concluir ✓" if self.i == n - 1 else "Próximo ▶")

    def proximo(self):
        if self.i >= len(PASSOS) - 1:
            return self.fechar()
        self.i += 1
        self.mostrar()

    def anterior(self):
        if self.i:
            self.i -= 1
            self.mostrar()

    def fechar(self):
        if not self.app.cfg.get("tutorial_visto2"):
            self.app.cfg["tutorial_visto2"] = True
            self.app.salvar()
        self.destroy()


def valor_ou_none(txt: str):
    """Campo opcional em R$: vazio (ou 0) = desligado. Levanta ValueError se for inválido."""
    t = txt.strip()
    if t in ("", "0", "0,00", "0.00"):
        return None
    return parse_centavos(t)


class Ajustes(ctk.CTkToplevel):
    """Valor padrão da diária e reserva mínima."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Ajustes do calendário")
        self.resizable(False, False)
        w, h = 480, 420
        x = max(0, app.winfo_rootx() + (app.winfo_width() - w) // 2)
        y = max(0, app.winfo_rooty() + (app.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.transient(app)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        ctk.CTkLabel(self, text="Ajustes do calendário", font=ctk.CTkFont(size=22, weight="bold")
                     ).pack(anchor="w", padx=28, pady=(22, 2))
        ctk.CTkLabel(self, text="Deixe em branco para desligar.", text_color=MUTED
                     ).pack(anchor="w", padx=28)

        ctk.CTkLabel(self, text="Valor padrão da diária (R$)", font=ctk.CTkFont(size=14, weight="bold")
                     ).pack(anchor="w", padx=28, pady=(18, 0))
        self.e_dia = ctk.CTkEntry(self, placeholder_text="Ex.: 180,00", height=38)
        self.e_dia.pack(fill="x", padx=28, pady=(4, 0))
        ctk.CTkLabel(self, text="O botão ＋ Diária já preenche este valor. É só conferir e apertar Enter.",
                     text_color=MUTED, font=ctk.CTkFont(size=11), wraplength=420, justify="left"
                     ).pack(anchor="w", padx=28, pady=(3, 0))

        ctk.CTkLabel(self, text="Reserva mínima (R$)", font=ctk.CTkFont(size=14, weight="bold")
                     ).pack(anchor="w", padx=28, pady=(18, 0))
        self.e_res = ctk.CTkEntry(self, placeholder_text="Ex.: 100,00", height=38)
        self.e_res.pack(fill="x", padx=28, pady=(4, 0))
        ctk.CTkLabel(self, text="O calendário marca com ⚠ os dias em que o saldo previsto ficar abaixo "
                                "desse valor e avisa em quantos dias isso vai acontecer.",
                     text_color=MUTED, font=ctk.CTkFont(size=11), wraplength=420, justify="left"
                     ).pack(anchor="w", padx=28, pady=(3, 0))

        self.l_erro = ctk.CTkLabel(self, text="", text_color=ROXO_TXT)
        self.l_erro.pack(anchor="w", padx=28, pady=(10, 0))
        rod = ctk.CTkFrame(self, fg_color="transparent")
        rod.pack(fill="x", padx=28, pady=(8, 20), side="bottom")
        ctk.CTkButton(rod, text="Cancelar", width=100, fg_color=SUAVE, hover_color=BORDA, text_color=TEXTO,
                      command=self.destroy).pack(side="left")
        ctk.CTkButton(rod, text="Salvar", width=120, height=36, fg_color=AZUL, hover_color=AZUL_H,
                      command=self.salvar).pack(side="right")

        for chave, e in (("diaria_padrao", self.e_dia), ("reserva_minima", self.e_res)):
            if app.cfg.get(chave):
                e.insert(0, fmt_input(app.cfg[chave]))
            e.bind("<Return>", lambda ev: self.salvar())
        self.bind("<Escape>", lambda ev: self.destroy())
        self.after(200, self._foco)

    def _foco(self):
        try:
            self.lift()
            self.focus_force()
            self.e_dia.focus()
        except tk.TclError:
            pass

    def salvar(self):
        try:
            dia = valor_ou_none(self.e_dia.get())
        except (ValueError, InvalidOperation):
            return self.l_erro.configure(text="⚠ Valor da diária inválido (ex.: 180,00).")
        try:
            res = valor_ou_none(self.e_res.get())
        except (ValueError, InvalidOperation):
            return self.l_erro.configure(text="⚠ Reserva mínima inválida (ex.: 100,00).")
        self.app.cfg["diaria_padrao"] = dia
        self.app.cfg["reserva_minima"] = res
        self.app.salvar()
        self.app.atualizar_calendario()
        self.app.aviso("Ajustes salvos.", ok=True)
        self.destroy()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.lanc = []
        self.cfg = {"tema": "dark", "metas": {}, "tutorial_visto2": False,
                    "diaria_padrao": None, "reserva_minima": None,
                    "categorias": {"Despesa": list(CAT_DESPESA), "Receita": list(CAT_RECEITA)}}
        erro = self.carregar()
        ctk.set_appearance_mode(self.cfg["tema"])

        self.title(f"{APP} — {EMPRESA}")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{min(1380, sw - 40)}x{min(820, sh - 100)}+10+10")
        self.minsize(1180, 640)  # pequeno o bastante p/ o gerenciador permitir maximizar
        self.editando = None
        self.sel = ("dia", date.today().isoformat())  # seleção no calendário
        self.ordem = ("data", True)
        self.sujo = True
        self.reconstruindo = False
        self.lixeira = []
        self._aviso_id = None
        self._tut = None
        self._ajustes = None
        self._rep_visivel = True
        self.tela_cheia = False
        self.fonte = tkfont.nametofont("TkDefaultFont").actual("family")
        self.report_callback_exception = self.erro_inesperado
        self.icone()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.montar_lateral()
        self.montar_principal()
        self.estilo_tabela()
        self.atualizar()
        self.redesenhar_logo()

        self.bind("<Control-z>", self.desfazer)
        self.bind("<Control-n>", lambda e: (self.cancelar_edicao(), self.e_desc.focus()))
        self.bind("<F11>", self.alternar_tela_cheia)
        self.bind("<Escape>", self.sair_tela_cheia)
        self.bind("<F1>", self.abrir_tutorial)
        self.bind("<F2>", self.abrir_ajustes)
        self.after(200, self.maximizar)
        self._hoje = date.today()
        self.after(60000, self._tick)
        if erro:
            self.after(300, lambda: messagebox.showwarning("Arquivo de dados", erro))
        if not self.cfg.get("tutorial_visto2"):
            self.after(700, self.abrir_tutorial)

    # ---------- infraestrutura ----------
    def icone(self):
        try:
            img = criar_icone()
            self.iconphoto(True, img)
            self._icone = img
        except Exception:
            pass

    def _tick(self):
        """Se o app ficar aberto na virada do dia, atualiza o 'hoje' do calendário."""
        if date.today() != self._hoje:
            self._hoje = date.today()
            self.atualizar()
        self.after(60000, self._tick)

    def maximizar(self):
        try:
            self.state("zoomed")
        except tk.TclError:
            try:
                self.attributes("-zoomed", True)
            except tk.TclError:
                pass

    def alternar_tela_cheia(self, _e=None):
        self.tela_cheia = not self.tela_cheia
        try:
            self.attributes("-fullscreen", self.tela_cheia)
        except tk.TclError:
            self.tela_cheia = False
            return
        self.b_full.configure(text="✕ Sair da tela cheia" if self.tela_cheia else "⛶ Tela cheia")
        if self.tela_cheia:
            self.aviso("Tela cheia ligada. Esc ou F11 para sair.", ok=True)

    def sair_tela_cheia(self, _e=None):
        if self.tela_cheia:
            self.alternar_tela_cheia()

    def abrir_tutorial(self, _e=None):
        try:
            if self._tut is not None and self._tut.winfo_exists():
                self._tut.lift()
                return
        except tk.TclError:
            pass
        self._tut = Tutorial(self)

    def abrir_ajustes(self, _e=None):
        try:
            if self._ajustes is not None and self._ajustes.winfo_exists():
                self._ajustes.lift()
                return
        except tk.TclError:
            pass
        self._ajustes = Ajustes(self)

    def erro_inesperado(self, exc, val, tb):
        txt = "".join(traceback.format_exception(exc, val, tb))
        log = PASTA / "erro.log"
        try:
            with open(log, "a", encoding="utf-8") as f:
                f.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}]\n{txt}")
        except OSError:
            pass
        messagebox.showerror("Erro inesperado", f"{val}\n\nDetalhes em:\n{log}")

    def carregar(self):
        origem = next((p for p in (ARQUIVO, LEGADO) if p.exists()), None)
        if not origem:
            return None
        descartados = 0
        try:
            bruto = json.loads(origem.read_text(encoding="utf-8"))
            if isinstance(bruto, list):  # formato da V1
                bruto = {"lancamentos": bruto}
            if not isinstance(bruto, dict):
                raise ValueError("formato inesperado")
            cfg = bruto.get("config") or {}
            cats = {t: list((cfg.get("categorias") or {}).get(t) or self.cfg["categorias"][t])
                    for t in ("Despesa", "Receita")}
            if "Diária" not in cats["Receita"]:
                cats["Receita"].insert(0, "Diária")
            usados, lanc = set(), []
            for bruto_d in bruto.get("lancamentos") or []:
                d = normalizar_lancamento(bruto_d, usados)
                if d is None:  # um registro ruim não derruba o arquivo inteiro
                    descartados += 1
                    continue
                lanc.append(d)
                if d["categoria"] not in cats[d["tipo"]]:
                    cats[d["tipo"]].append(d["categoria"])
            metas = {}
            for k, v in (cfg.get("metas") or {}).items():
                try:
                    metas[str(k)] = int(v)
                except (TypeError, ValueError):
                    pass
            self.lanc = lanc
            self.cfg["tema"] = "light" if cfg.get("tema") == "light" else "dark"
            self.cfg["metas"] = metas
            self.cfg["categorias"] = cats
            self.cfg["tutorial_visto2"] = bool(cfg.get("tutorial_visto2", False))
            for chave in ("diaria_padrao", "reserva_minima"):
                v = cfg.get(chave)
                ok = isinstance(v, (int, float)) and not isinstance(v, bool) and 0 < v <= 10 ** 11
                self.cfg[chave] = int(v) if ok else None
        except Exception:
            copia = PASTA / f"corrompido-{datetime.now():%Y%m%d-%H%M%S}.json"
            try:
                shutil.copy2(origem, copia)
            except OSError:
                pass
            self.lanc = []
            return f"Não consegui ler {origem.name}.\nUma cópia foi guardada em:\n{copia}"
        aviso = None
        if descartados:
            copia = PASTA / f"original-{datetime.now():%Y%m%d-%H%M%S}.json"
            try:
                shutil.copy2(origem, copia)
            except OSError:
                pass
            aviso = (f"{descartados} lançamento(s) inválido(s) foram ignorados.\n"
                     f"O arquivo original foi guardado em:\n{copia}")
        if origem is LEGADO:
            self.salvar()
        return aviso

    def _backup_diario(self):
        """Uma cópia por dia em Financas/backups (guarda as últimas 14)."""
        try:
            if not ARQUIVO.exists():
                return
            pasta = PASTA / "backups"
            pasta.mkdir(exist_ok=True)
            alvo = pasta / f"financas-{date.today():%Y-%m-%d}.json"
            if not alvo.exists():
                shutil.copy2(ARQUIVO, alvo)
            for antigo in sorted(pasta.glob("financas-*.json"))[:-14]:
                antigo.unlink(missing_ok=True)
        except OSError:
            pass

    def salvar(self):
        try:
            tmp = ARQUIVO.with_suffix(".tmp")
            tmp.write_text(json.dumps({"versao": 3, "config": self.cfg, "lancamentos": self.lanc},
                                      ensure_ascii=False, indent=1), encoding="utf-8")
            self._backup_diario()
            if ARQUIVO.exists():
                shutil.copy2(ARQUIVO, ARQUIVO.with_suffix(".bak"))
            tmp.replace(ARQUIVO)
        except OSError as e:
            messagebox.showerror("Erro ao salvar", str(e))

    def c(self, cor):
        return pick(cor, self.escuro())

    def escuro(self):
        return ctk.get_appearance_mode() == "Dark"

    def redesenhar_logo(self):
        desenhar_logo(self.logo, self.c(PAINEL))

    # ---------- layout ----------
    def montar_lateral(self):
        lat = ctk.CTkFrame(self, width=320, corner_radius=0)
        lat.grid(row=0, column=0, sticky="nsew")
        lat.grid_propagate(False)
        lat.pack_propagate(False)

        # ---- rodapé fixo (sempre visível, de baixo para cima) ----
        ctk.CTkLabel(lat, text=f"© {EMPRESA} · v{VERSAO}", text_color=MUTED,
                     font=ctk.CTkFont(size=11)).pack(side="bottom", pady=(0, 10))
        self.sw = ctk.CTkSwitch(lat, text="Modo escuro", command=self.trocar_tema)
        if self.cfg["tema"] == "dark":
            self.sw.select()
        self.sw.pack(side="bottom", padx=24, pady=(0, 8), anchor="w")

        dados = ctk.CTkFrame(lat, fg_color="transparent")
        dados.pack(side="bottom", padx=24, pady=(0, 10), fill="x")
        dados.grid_columnconfigure((0, 1, 2), weight=1)
        b_guia = ctk.CTkButton(dados, text="❓ Guia", height=30, font=ctk.CTkFont(size=12),
                               command=self.abrir_tutorial)
        b_guia.grid(row=0, column=0, sticky="ew", padx=(0, 3))
        Dica(b_guia, "Abre um passo a passo explicando como usar o programa (F1).")
        for i, (t, cmd, dica) in enumerate((
                ("Exportar", self.exportar, "Salva seus lançamentos em uma planilha CSV (Excel/LibreOffice)."),
                ("Importar", self.importar, "Traz lançamentos de uma planilha CSV."))):
            b = ctk.CTkButton(dados, text=t, height=30, fg_color="transparent", border_width=1,
                              border_color=BORDA, text_color=TEXTO, hover_color=SUAVE,
                              font=ctk.CTkFont(size=12), command=cmd)
            b.grid(row=0, column=i + 1, sticky="ew", padx=3 if i == 0 else (3, 0))
            Dica(b, dica)

        self.l_msg = ctk.CTkLabel(lat, text="", wraplength=260, justify="left")
        self.l_msg.pack(side="bottom", padx=24, pady=(6, 6), anchor="w")

        bt = ctk.CTkFrame(lat, fg_color="transparent")
        bt.pack(side="bottom", padx=24, pady=(8, 0), fill="x")
        bt.grid_columnconfigure(0, weight=1)
        self.b_ok = ctk.CTkButton(bt, text="＋ Adicionar", height=40, fg_color=AZUL,
                                  hover_color=AZUL_H, text_color=BRANCO,
                                  font=ctk.CTkFont(weight="bold"), command=self.confirmar)
        self.b_ok.grid(row=0, column=0, sticky="ew")
        Dica(self.b_ok, "Salva o lançamento (atalho: Enter).")
        self.b_cancel = ctk.CTkButton(bt, text="✕", width=40, height=40, fg_color=SUAVE,
                                      hover_color=BORDA, text_color=TEXTO, command=self.cancelar_edicao)

        # ---- marca ----
        marca = ctk.CTkFrame(lat, fg_color="transparent")
        marca.pack(side="top", padx=24, pady=(22, 0), fill="x")
        self.logo = tk.Canvas(marca, width=46, height=46, highlightthickness=0, bd=0)
        self.logo.pack(side="left", padx=(0, 10))
        tb = ctk.CTkFrame(marca, fg_color="transparent")
        tb.pack(side="left")
        ctk.CTkLabel(tb, text=APP, font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(tb, text=EMPRESA.upper(), text_color=AZUL_TXT,
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        ctk.CTkFrame(lat, height=2, fg_color=BORDA).pack(side="top", fill="x", padx=24, pady=(14, 8))

        # ---- formulário (rola se a tela for pequena) ----
        corpo = self.corpo = ctk.CTkScrollableFrame(lat, fg_color="transparent")
        corpo.pack(side="top", fill="both", expand=True, padx=(10, 6))

        self.l_modo = ctk.CTkLabel(corpo, text="Novo lançamento", font=ctk.CTkFont(size=14, weight="bold"))
        self.l_modo.pack(padx=8, anchor="w")
        ctk.CTkLabel(corpo, text="Anote o que entrou ou saiu e clique em Adicionar.",
                     text_color=MUTED, font=ctk.CTkFont(size=11), wraplength=250,
                     justify="left").pack(padx=8, anchor="w")
        self.tipo = ctk.CTkSegmentedButton(corpo, values=["Despesa", "Receita"], command=self.trocar_tipo)
        self.tipo.set("Despesa")
        self.tipo.pack(padx=8, pady=(8, 0), fill="x")
        Dica(self.tipo, "Despesa = dinheiro que saiu. Receita = dinheiro que entrou.")

        self.e_desc = self.campo(corpo, "Descrição (ex.: Supermercado)")
        self.e_valor = self.campo(corpo, "Valor (ex.: 1.250,90)")
        self.e_data = self.campo(corpo, "Data (dd/mm/aaaa)")
        self.e_data.insert(0, date.today().strftime("%d/%m/%Y"))
        Dica(self.e_data, "Formato dd/mm/aaaa. Você também pode escrever 'hoje'.")
        ctk.CTkLabel(corpo, text="Categoria (digite para criar uma nova)", text_color=MUTED,
                     font=ctk.CTkFont(size=11)).pack(padx=8, pady=(10, 0), anchor="w")
        self.cat = ctk.CTkComboBox(corpo, values=self.cfg["categorias"]["Despesa"], height=36)
        self.cat.set(self.cfg["categorias"]["Despesa"][0])
        self.cat.pack(padx=8, pady=(2, 0), fill="x")
        # --- repetição: todo mês, toda semana ou dias da semana escolhidos ---
        self.f_rep = ctk.CTkFrame(corpo, fg_color="transparent")
        self.f_rep.pack(fill="x", padx=8, pady=(10, 0))
        ctk.CTkLabel(self.f_rep, text="Repetição", text_color=MUTED, font=ctk.CTkFont(size=11)
                     ).pack(anchor="w")
        self.m_rep = ctk.CTkOptionMenu(self.f_rep, values=MODOS_REP, height=32,
                                       command=lambda _: self.atualizar_rep_ui())
        self.m_rep.set(MODOS_REP[0])
        self.m_rep.pack(fill="x", pady=(2, 0))
        Dica(self.m_rep, "Repete o lançamento: todo mês (contas fixas), toda semana ou só nos "
                         "dias da semana que você escolher (ex.: passagem de seg a sex).")
        self.f_dias = ctk.CTkFrame(self.f_rep, fg_color="transparent")
        self.rep_dias = [False] * 7
        self.b_dias = []
        for i, nome in enumerate(DIAS):
            b = ctk.CTkButton(self.f_dias, text=nome, width=34, height=28, corner_radius=6,
                              font=ctk.CTkFont(size=10, weight="bold"), fg_color=SUAVE, hover_color=BORDA,
                              text_color=TEXTO, command=lambda i=i: self.alternar_dia_rep(i))
            b.grid(row=0, column=i, padx=1)
            self.b_dias.append(b)
        for col, (txt, cmd) in enumerate((("Seg–Sex", self.preset_semana), ("Limpar", self.limpar_dias))):
            ctk.CTkButton(self.f_dias, text=txt, width=70, height=24, font=ctk.CTkFont(size=10),
                          fg_color="transparent", border_width=1, border_color=BORDA, text_color=TEXTO,
                          hover_color=SUAVE, command=cmd).grid(row=1, column=col * 3, columnspan=3,
                                                              pady=(5, 0), sticky="w")
        self.e_rep = ctk.CTkEntry(self.f_rep, placeholder_text="", height=36)
        Dica(self.e_rep, "Quantas vezes repetir: meses (até 60) ou semanas (até 52).")
        self.var_pago = ctk.BooleanVar(value=True)
        chk = self.chk_pago = ctk.CTkCheckBox(corpo, text="Já pago / recebido", variable=self.var_pago)
        chk.pack(padx=8, pady=(14, 8), anchor="w")
        Dica(chk, "Desmarque se ainda vai pagar/receber. Fica como Pendente e entra em 'A pagar'.")

        for e in (self.e_desc, self.e_valor, self.e_data, self.e_rep):
            e.bind("<Return>", lambda ev: self.confirmar())
            e.bind("<Escape>", self._esc_campo)

    def atualizar_rep_ui(self):
        """Mostra só o que o modo de repetição escolhido precisa."""
        modo = self.m_rep.get()
        self.f_dias.pack_forget()
        self.e_rep.pack_forget()
        if modo == MODOS_REP[0]:
            return
        if modo == MODOS_REP[3]:
            if not any(self.rep_dias):  # começa marcando o dia da semana da data digitada
                try:
                    self.rep_dias[(parse_data(self.e_data.get()).weekday() + 1) % 7] = True
                except ValueError:
                    pass
                self.pintar_dias_rep()
            self.f_dias.pack(fill="x", pady=(6, 0))
        self.e_rep.configure(placeholder_text="Quantos meses? (ex.: 12)" if modo == MODOS_REP[1]
                             else "Quantas semanas? (ex.: 4)")
        self.e_rep.pack(fill="x", pady=(6, 0))
        self.after(60, self._rolar_form)

    def _rolar_form(self):
        """Rola o formulário até o fim para as opções de repetição ficarem visíveis."""
        try:
            self.update_idletasks()
            self.corpo._parent_canvas.yview_moveto(1.0)
        except (tk.TclError, AttributeError):
            pass

    def pintar_dias_rep(self):
        for i, b in enumerate(self.b_dias):
            on = self.rep_dias[i]
            b.configure(fg_color=ROXO if on else SUAVE, text_color=BRANCO if on else TEXTO)

    def alternar_dia_rep(self, i):
        self.rep_dias[i] = not self.rep_dias[i]
        self.pintar_dias_rep()

    def preset_semana(self):
        self.rep_dias = [0 < i < 6 for i in range(7)]  # segunda a sexta
        self.pintar_dias_rep()

    def limpar_dias(self):
        self.rep_dias = [False] * 7
        self.pintar_dias_rep()

    def mostrar_rep(self, resetar=True):
        """Mostra o bloco de repetição (some ao editar). resetar=True volta para 'Não repetir'."""
        if resetar:
            self.m_rep.set(MODOS_REP[0])
            self.rep_dias = [False] * 7
            self.pintar_dias_rep()
            self.e_rep.delete(0, "end")
        self.atualizar_rep_ui()
        if not self._rep_visivel:
            self.f_rep.pack(fill="x", padx=8, pady=(10, 0), before=self.chk_pago)
            self._rep_visivel = True

    def _esc_campo(self, _ev=None):
        # Esc no campo cancela a edição; fora de edição deixa o Esc sair da tela cheia
        if self.editando:
            self.cancelar_edicao()
            return "break"

    def campo(self, pai, placeholder):
        e = ctk.CTkEntry(pai, placeholder_text=placeholder, height=36)
        e.pack(padx=8, pady=(7, 0), fill="x")
        return e

    def montar_principal(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        topo = ctk.CTkFrame(main, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(topo, text="Visão geral", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        self.b_full = ctk.CTkButton(topo, text="⛶ Tela cheia", width=120, fg_color=SUAVE,
                                    hover_color=BORDA, text_color=TEXTO, command=self.alternar_tela_cheia)
        self.b_full.pack(side="right", padx=(12, 0))
        Dica(self.b_full, "Liga/desliga a tela cheia (F11). Esc para sair.")
        b_prox = ctk.CTkButton(topo, text="▶", width=32, command=lambda: self.mover_mes(-1))
        b_prox.pack(side="right")
        Dica(b_prox, "Mês mais recente")
        self.filtro = ctk.CTkOptionMenu(topo, values=["Todos"], width=120,
                                        command=lambda _: self.atualizar())
        self.filtro.pack(side="right", padx=6)
        self.filtro.set(date.today().strftime("%m/%Y"))
        Dica(self.filtro, "Escolha um mês para ver só ele, ou 'Todos' para somar tudo.")
        b_ant = ctk.CTkButton(topo, text="◀", width=32, command=lambda: self.mover_mes(1))
        b_ant.pack(side="right")
        Dica(b_ant, "Mês anterior")
        ctk.CTkLabel(topo, text="Período:", text_color=MUTED).pack(side="right", padx=10)

        cards = ctk.CTkFrame(main, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", pady=16)
        for i in range(4):
            cards.grid_columnconfigure(i, weight=1)
        self.l_rec, self.s_rec = self.card(cards, 0, "Receitas", AZUL_TXT,
                                           "Total de dinheiro que ENTRA (recebido + a receber).")
        self.l_desp, self.s_desp = self.card(cards, 1, "Despesas", ROXO_TXT,
                                             "Total de dinheiro que SAI (pago + a pagar).")
        self.l_saldo, self.s_saldo = self.card(cards, 2, "Saldo realizado", TEXTO,
                                               "O que você já recebeu menos o que já pagou.")
        self.l_pend, self.s_pend = self.card(cards, 3, "A pagar", ROXO_SEL,
                                             "Despesas ainda pendentes. Vencidas têm data anterior a hoje.")

        self.abas = ctk.CTkTabview(
            main, command=self.desenhar_se_visivel, fg_color=PAINEL, border_width=1, border_color=BORDA,
            segmented_button_fg_color=SUAVE, segmented_button_selected_color=ROXO_SEL,
            segmented_button_selected_hover_color=ROXO_SEL_H, segmented_button_unselected_color=SUAVE,
            segmented_button_unselected_hover_color=BORDA, text_color=SEG_TXT)
        self.abas.grid(row=2, column=0, sticky="nsew")
        self.montar_calendario(self.abas.add("Calendário"))
        self.montar_lancamentos(self.abas.add("Lançamentos"))
        self.montar_graficos(self.abas.add("Gráficos"))
        self.montar_metas(self.abas.add("Metas"))

    def card(self, pai, col, titulo, cor, dica):
        f = ctk.CTkFrame(pai, corner_radius=14, fg_color=CARTAO, border_width=1, border_color=BORDA)
        f.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0 if col == 3 else 6))
        ctk.CTkFrame(f, width=5, height=10, fg_color=cor, corner_radius=3
                     ).pack(side="left", fill="y", padx=(12, 0), pady=14)
        box = ctk.CTkFrame(f, fg_color="transparent")
        box.pack(side="left", padx=14, pady=12)
        ctk.CTkLabel(box, text=titulo, text_color=MUTED).pack(anchor="w")
        valor = ctk.CTkLabel(box, text="R$ 0,00", font=ctk.CTkFont(size=22, weight="bold"))
        valor.pack(anchor="w")
        legenda = ctk.CTkLabel(box, text="", text_color=MUTED, font=ctk.CTkFont(size=11))
        legenda.pack(anchor="w")
        Dica(f, dica)
        return valor, legenda

    # ---------- calendário mensal ----------
    def montar_calendario(self, aba):
        aba.grid_columnconfigure(0, weight=1)
        aba.grid_rowconfigure(0, weight=1)
        self.cel = []

        esq = ctk.CTkFrame(aba, fg_color="transparent")
        esq.grid(row=0, column=0, sticky="nsew")
        self._cal_esq = esq
        for c in range(7):
            esq.grid_columnconfigure(c, weight=1, uniform="dia")
        for r in range(6):
            esq.grid_rowconfigure(3 + r, weight=1, uniform="sem")

        topo = ctk.CTkFrame(esq, fg_color="transparent")
        topo.grid(row=0, column=0, columnspan=7, sticky="ew", pady=(0, 2))
        self.l_cal_titulo = ctk.CTkLabel(topo, text="", font=ctk.CTkFont(size=18, weight="bold"))
        self.l_cal_titulo.pack(side="left")
        b_hoje = ctk.CTkButton(topo, text="Hoje", width=60, height=28, command=self.ir_hoje)
        b_hoje.pack(side="right")
        Dica(b_hoje, "Volta para o mês atual e seleciona o dia de hoje.")
        b_aj = ctk.CTkButton(topo, text="⚙ Ajustes", width=84, height=28, fg_color=SUAVE, hover_color=BORDA,
                             text_color=TEXTO, command=self.abrir_ajustes)
        b_aj.pack(side="right", padx=(0, 8))
        Dica(b_aj, "Valor padrão da diária e reserva mínima (F2).")
        self.sw_sim = ctk.CTkSwitch(topo, text="E se a diária não cair?", command=self.atualizar_calendario)
        self.sw_sim.pack(side="right", padx=14)
        Dica(self.sw_sim, "Mostra o mês sem contar nenhuma diária pendente. "
                          "Útil para ver se o dinheiro aguenta.")

        ind = ctk.CTkFrame(esq, fg_color="transparent")
        ind.grid(row=1, column=0, columnspan=7, sticky="ew", pady=(0, 6))
        fn = ctk.CTkFont(size=12, weight="bold")
        linha = ctk.CTkFrame(ind, fg_color="transparent")
        linha.pack(fill="x")
        self.l_alerta = ctk.CTkLabel(ind, text="", font=fn, anchor="w", justify="left", wraplength=640)
        self.l_caixa = ctk.CTkLabel(linha, text="", font=fn)
        self.l_caixa.pack(side="left", padx=(0, 16))
        self.l_folego = ctk.CTkLabel(linha, text="", font=fn)
        self.l_folego.pack(side="left", padx=(0, 16))
        self.l_menor = ctk.CTkLabel(linha, text="", font=fn)
        self.l_menor.pack(side="left")
        Dica(self.l_caixa, "Dinheiro que você realmente tem hoje (só o que já foi pago/recebido).")
        Dica(self.l_folego, "Por quantos dias o dinheiro em caixa dura, no ritmo de gastos dos últimos 30 dias.")
        Dica(self.l_menor, "O pior saldo previsto no mês (contando contas a pagar e diárias pendentes).")

        self.cab_sem = []
        for i, nome in enumerate(DIAS):
            b = ctk.CTkButton(esq, text=nome, height=42, corner_radius=8, fg_color=SUAVE,
                              hover_color=BORDA, text_color=TEXTO, font=ctk.CTkFont(size=11, weight="bold"),
                              command=lambda i=i: self.selecionar_semana(i))
            b.grid(row=2, column=i, sticky="ew", padx=2, pady=(0, 2))
            Dica(b, f"Ver todos os lançamentos de {PLURAL[i]} do mês.")
            self.cab_sem.append(b)

        f_dia = ctk.CTkFont(size=12, weight="bold")
        f_val = ctk.CTkFont(size=11, weight="bold")
        f_sal = ctk.CTkFont(size=10)
        for k in range(42):
            r, c = divmod(k, 7)
            f = ctk.CTkFrame(esq, corner_radius=8, fg_color=CARTAO, border_width=2, border_color=BORDA)
            f.grid(row=3 + r, column=c, sticky="nsew", padx=2, pady=2)
            f.grid_columnconfigure(0, weight=1)
            l_dia = ctk.CTkLabel(f, text="", height=16, anchor="w", font=f_dia)
            l_sal = ctk.CTkLabel(f, text="", height=16, anchor="e", font=f_sal)
            l_rec = ctk.CTkLabel(f, text="", height=14, anchor="w", font=f_val)
            l_des = ctk.CTkLabel(f, text="", height=14, anchor="w", font=f_val)
            l_dia.grid(row=0, column=0, sticky="w", padx=(6, 0), pady=(3, 0))
            l_sal.grid(row=0, column=1, sticky="e", padx=(0, 6), pady=(3, 0))
            l_rec.grid(row=1, column=0, columnspan=2, sticky="w", padx=6)
            l_des.grid(row=2, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 3))
            for w in (f, l_dia, l_sal, l_rec, l_des):
                w.bind("<Button-1>", lambda e, k=k: self.selecionar_dia(k))
            self.cel.append((f, l_dia, l_sal, l_rec, l_des))

        ctk.CTkLabel(esq, text="○ previsto · ! vencido ou saldo negativo · ✕ diária que não conta · "
                               "número pequeno = saldo no fim do dia · valores em R$",
                     text_color=MUTED, font=ctk.CTkFont(size=10)
                     ).grid(row=9, column=0, columnspan=7, sticky="w", pady=(4, 0))

        # painel do dia / do dia da semana
        pn = ctk.CTkFrame(aba, width=340, corner_radius=12, fg_color=CARTAO)
        pn.grid(row=0, column=1, sticky="ns", padx=(10, 0))
        pn.pack_propagate(False)
        self.l_dia_titulo = ctk.CTkLabel(pn, text="", font=ctk.CTkFont(size=15, weight="bold"),
                                         anchor="w", justify="left", wraplength=310)
        self.l_dia_titulo.pack(anchor="w", padx=12, pady=(12, 0))
        self.l_dia_resumo = ctk.CTkLabel(pn, text="", text_color=MUTED, anchor="w", justify="left",
                                         wraplength=310, font=ctk.CTkFont(size=12))
        self.l_dia_resumo.pack(anchor="w", padx=12, pady=(2, 8))
        bt = ctk.CTkFrame(pn, fg_color="transparent")
        bt.pack(fill="x", padx=12)
        bt.grid_columnconfigure((0, 1), weight=1)
        b_d = ctk.CTkButton(bt, text="＋ Diária", height=34, fg_color=AZUL, hover_color=AZUL_H,
                            command=self.lancar_diaria)
        b_d.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        Dica(b_d, "Prepara o formulário com uma diária (receita) neste dia.")
        b_g = ctk.CTkButton(bt, text="＋ Gasto", height=34, command=self.lancar_gasto)
        b_g.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        Dica(b_g, "Prepara o formulário com um gasto (despesa) neste dia.")

        acoes = ctk.CTkFrame(pn, fg_color="transparent")
        acoes.pack(side="bottom", fill="x", padx=12, pady=(6, 12))
        ctk.CTkButton(acoes, text="🗑", width=40, fg_color=ROXO_ESC, hover_color=ROXO_ESC_H,
                      command=self.excluir).pack(side="right")
        ctk.CTkButton(acoes, text="✏ Editar", width=80, command=self.iniciar_edicao
                      ).pack(side="right", padx=6)
        ctk.CTkButton(acoes, text="✓ Pago / Pend.", width=110, fg_color=AZUL, hover_color=AZUL_H,
                      command=self.alternar_status).pack(side="right")

        caixa = ctk.CTkFrame(pn, fg_color="transparent")
        caixa.pack(fill="both", expand=True, padx=(12, 6), pady=(10, 0))
        caixa.grid_columnconfigure(0, weight=1)
        caixa.grid_rowconfigure(0, weight=1)
        cols = ("data", "descricao", "valor", "status")
        self.tree_dia = ttk.Treeview(caixa, columns=cols, show="headings", selectmode="extended",
                                     height=8, style="Dia.Treeview")
        for c, t, w, an, st in (("data", "Dia", 50, "center", False), ("descricao", "Descrição", 86, "w", True),
                                ("valor", "Valor", 102, "e", False), ("status", "Status", 66, "center", False)):
            self.tree_dia.heading(c, text=t)
            self.tree_dia.column(c, width=w, anchor=an, stretch=st)
        self.tree_dia.grid(row=0, column=0, sticky="nsew")
        sb = ctk.CTkScrollbar(caixa, command=self.tree_dia.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.tree_dia.configure(yscrollcommand=sb.set)
        self.tree_dia.bind("<Delete>", lambda e: self.excluir())
        self.tree_dia.bind("<Double-1>", lambda e: self.iniciar_edicao()
                           if self.tree_dia.identify_region(e.x, e.y) == "cell" else None)

    def sel_ids(self):
        if self.abas.get() == "Calendário":
            return self.tree_dia.selection()
        return self.tree.selection()

    def mes_cal(self):
        p = self.periodo()
        if p is None:
            h = date.today()
            return h.year, h.month
        return int(p[:4]), int(p[5:7])

    def ir_hoje(self):
        self.filtro.set(date.today().strftime("%m/%Y"))
        self.sel = ("dia", date.today().isoformat())
        self.atualizar()

    def selecionar_dia(self, k):
        ano, mes = self.mes_cal()
        off = (date(ano, mes, 1).weekday() + 1) % 7
        dia = k - off + 1
        if not 1 <= dia <= calendar.monthrange(ano, mes)[1]:
            return
        d = date(ano, mes, dia)
        self.sel = ("dia", d.isoformat())
        if not self.editando:  # o formulário já fica com a data do dia clicado
            self.e_data.delete(0, "end")
            self.e_data.insert(0, d.strftime("%d/%m/%Y"))
        self.atualizar_calendario()

    def selecionar_semana(self, i):
        self.sel = ("sem", i)
        self.atualizar_calendario()

    def _data_sel(self):
        if self.sel[0] != "dia":
            self.aviso("Clique primeiro em um dia do calendário.")
            return None
        return date.fromisoformat(self.sel[1])

    def alerta_reserva(self, hoje: date, simular: bool):
        """Nos próximos 60 dias: primeiro dia com saldo previsto negativo e primeiro abaixo da reserva.
        Devolve (negativo, baixo); cada um é None ou (dias_até_lá, data, saldo)."""
        reserva = self.cfg.get("reserva_minima") or 0
        h = hoje.isoformat()
        fim = (hoje + timedelta(days=59)).isoformat()
        saldo = sum(efeito_previsto(d, h, simular) for d in self.lanc if d["data"] < h)
        por_data = {}
        for d in self.lanc:
            if h <= d["data"] <= fim:
                por_data.setdefault(d["data"], []).append(d)
        neg = baixo = None
        for k in range(60):
            dia = hoje + timedelta(days=k)
            saldo += sum(efeito_previsto(d, h, simular) for d in por_data.get(dia.isoformat(), []))
            if baixo is None and reserva and saldo < reserva:
                baixo = (k, dia, saldo)
            if saldo < 0:
                neg = (k, dia, saldo)
                break
        return neg, baixo

    def atualizar_alerta(self, hoje: date, simular: bool):
        reserva = self.cfg.get("reserva_minima") or 0
        neg, baixo = self.alerta_reserva(hoje, simular)

        def quando(k, dia):
            return ("Hoje" if k == 0 else "Amanhã" if k == 1 else f"Em {k} dias") + f" ({dia:%d/%m})"

        pre = "Sem as diárias pendentes: " if simular else ""
        linhas = []
        if baixo and (not neg or baixo[0] < neg[0]):
            linhas.append(f"⚠ {pre}{quando(baixo[0], baixo[1])} o saldo previsto cai abaixo da sua reserva "
                          f"de {brl(reserva)} (fica em {brl(baixo[2])}).")
        if neg:
            linhas.append(f"! {pre}{quando(neg[0], neg[1])} o dinheiro acaba: saldo previsto {brl(neg[2])}.")
        if linhas:
            self.l_alerta.configure(text="\n".join(linhas), text_color=TEXTO if neg else ROXO_TXT)
            self.l_alerta.pack(anchor="w", pady=(3, 0))
        elif reserva:
            self.l_alerta.configure(text=f"✓ {pre}Saldo previsto acima da reserva ({brl(reserva)}) "
                                         "nos próximos 60 dias.", text_color=AZUL_TXT)
            self.l_alerta.pack(anchor="w", pady=(3, 0))
        else:
            self.l_alerta.pack_forget()

    def media_historica(self, i):
        """Média por dia da semana i (0=dom) de tudo que foi pago até hoje: (dias, entrada, saída)."""
        h = date.today()
        pagos = [d for d in self.lanc if d["pago"] and d["data"] <= h.isoformat()]
        if not pagos:
            return None
        primeiro = date.fromisoformat(min(d["data"] for d in pagos))
        total = (h - primeiro).days + 1
        desloc = (i - (primeiro.weekday() + 1) % 7) % 7
        n = 0 if desloc >= total else (total - desloc - 1) // 7 + 1
        if n < 1:
            return None
        rec = sum(d["centavos"] for d in pagos
                  if d["tipo"] == "Receita" and (date.fromisoformat(d["data"]).weekday() + 1) % 7 == i)
        desp = sum(d["centavos"] for d in pagos
                   if d["tipo"] == "Despesa" and (date.fromisoformat(d["data"]).weekday() + 1) % 7 == i)
        return n, rec // n, desp // n

    def _txt_historico(self, i):
        mh = self.media_historica(i)
        if not mh:
            return ""
        n, r, s = mh
        nome = DIAS_LONGOS[i].split("-")[0].lower()
        return (f"\nHistórico ({n} {nome if n == 1 else PLURAL[i]}, só o que foi pago): "
                f"+{brl(r)} / −{brl(s)} por {nome}")

    def lancar_diaria(self):
        d = self._data_sel()
        if not d:
            return
        self.cancelar_edicao()
        self.tipo.set("Receita")
        self.trocar_tipo("Receita")
        self.cat.set("Diária")
        self.e_desc.insert(0, "Diária")
        self.e_data.delete(0, "end")
        self.e_data.insert(0, d.strftime("%d/%m/%Y"))
        self.var_pago.set(d <= date.today())
        padrao = self.cfg.get("diaria_padrao")
        if padrao:
            self.e_valor.insert(0, fmt_input(padrao))
            self.e_valor.focus()
            try:
                self.e_valor.select_range(0, "end")
            except (tk.TclError, AttributeError):
                pass
            self.aviso(f"Diária de {d:%d/%m} ({brl(padrao)}): confira e aperte Enter.", ok=True)
        else:
            self.e_valor.focus()
            self.aviso(f"Diária de {d:%d/%m}: digite o valor e clique em Adicionar "
                       "(dica: ⚙ Ajustes define um valor padrão).", ok=True)

    def lancar_gasto(self):
        d = self._data_sel()
        if not d:
            return
        self.cancelar_edicao()
        self.tipo.set("Despesa")
        self.trocar_tipo("Despesa")
        self.e_data.delete(0, "end")
        self.e_data.insert(0, d.strftime("%d/%m/%Y"))
        self.var_pago.set(d <= date.today())
        self.e_desc.focus()
        self.aviso(f"Gasto de {d:%d/%m}: preencha e clique em Adicionar.", ok=True)

    def atualizar_calendario(self):
        if not self.cel:
            return
        ano, mes = self.mes_cal()
        n_dias = calendar.monthrange(ano, mes)[1]
        off = (date(ano, mes, 1).weekday() + 1) % 7
        linhas = (off + n_dias + 6) // 7
        h = date.today()
        hoje = h.isoformat()
        simular = bool(self.sw_sim.get())
        reserva = self.cfg.get("reserva_minima") or 0
        pref = f"{ano:04d}-{mes:02d}"

        # indicadores: caixa de hoje e fôlego (ritmo de gastos dos últimos 30 dias)
        caixa = gasto30 = 0
        ini30 = (h - timedelta(days=29)).isoformat()
        for d in self.lanc:
            if d["pago"] and d["data"] <= hoje:
                caixa += d["centavos"] if d["tipo"] == "Receita" else -d["centavos"]
                if d["tipo"] == "Despesa" and d["data"] >= ini30:
                    gasto30 += d["centavos"]
        self.l_caixa.configure(text=f"Em caixa hoje: {brl(caixa)}",
                               text_color=AZUL_TXT if caixa >= 0 else ROXO_TXT)
        media = gasto30 / 30
        if caixa <= 0:
            fol = "sem caixa"
        elif media <= 0:
            fol = "—"
        else:
            fol = f"≈ {int(caixa // media)} dia(s)"
        self.l_folego.configure(text=f"Fôlego: {fol}", text_color=TEXTO)
        self.atualizar_alerta(h, simular)

        # saldo previsto no início do mês: tudo que veio antes, pelas mesmas regras dos dias do mês
        inicio = f"{pref}-01"
        saldo = sum(efeito_previsto(d, hoje, simular) for d in self.lanc if d["data"] < inicio)
        por_dia = {}
        for d in self.lanc:
            if d["data"].startswith(pref):
                por_dia.setdefault(d["data"], []).append(d)

        sem = [[0, 0, 0] for _ in range(7)]  # dias, entradas, saídas por dia da semana
        info, menor = {}, None
        for dia in range(1, n_dias + 1):
            iso = f"{pref}-{dia:02d}"
            rec_ok = rec_prev = rec_exc = desp_ok = desp_pend = desp_venc = 0
            for d in por_dia.get(iso, []):
                c = d["centavos"]
                if d["tipo"] == "Receita":
                    if d["pago"]:
                        rec_ok += c
                    elif iso >= hoje and not simular:
                        rec_prev += c      # diária futura ainda esperada
                    else:
                        rec_exc += c       # atrasada ou simulando: não conta
                elif d["pago"]:
                    desp_ok += c
                elif iso < hoje:
                    desp_venc += c
                else:
                    desp_pend += c
            rec, desp = rec_ok + rec_prev, desp_ok + desp_pend + desp_venc
            saldo += rec - desp
            info[dia] = (rec_prev, rec_exc, desp_pend, desp_venc, rec, desp, saldo,
                         bool(por_dia.get(iso)))
            wd = (off + dia - 1) % 7
            sem[wd][0] += 1
            sem[wd][1] += rec
            sem[wd][2] += desp
            if (iso >= hoje or pref < hoje[:7]) and (menor is None or saldo < menor[0]):
                menor = (saldo, iso)

        if menor:
            neg = menor[0] < 0
            self.l_menor.configure(
                text=f"{'! ' if neg else ''}Menor saldo previsto: {brl(menor[0])} em "
                     f"{menor[1][8:]}/{menor[1][5:7]}",
                text_color=ROXO_TXT if neg else TEXTO)
        else:
            self.l_menor.configure(text="")

        titulo = f"{MESES[mes - 1]} de {ano}"
        if self.periodo() is None:
            titulo += "  (filtro 'Todos': mostrando o mês atual)"
        self.l_cal_titulo.configure(text=titulo)

        for r in range(6):
            self._cal_esq.grid_rowconfigure(3 + r, weight=1 if r < linhas else 0)
        for i, b in enumerate(self.cab_sem):
            n, r_, s_ = sem[i]
            ativo = self.sel == ("sem", i)
            b.configure(text=f"{DIAS[i]} ×{n}\n+{compacto(r_)}  −{compacto(s_)}",
                        fg_color=ROXO if ativo else SUAVE, text_color=BRANCO if ativo else TEXTO)

        for k in range(42):
            f, l_dia, l_sal, l_rec, l_des = self.cel[k]
            dia = k - off + 1
            if k >= linhas * 7:
                f.grid_remove()
                continue
            f.grid()
            if not 1 <= dia <= n_dias:
                f.configure(fg_color="transparent", border_width=0)
                for lb in (l_dia, l_sal, l_rec, l_des):
                    lb.configure(text="")
                continue
            iso = f"{pref}-{dia:02d}"
            rec_prev, rec_exc, desp_pend, desp_venc, rec, desp, sfim, tem = info[dia]
            marcado = self.sel == ("dia", iso)
            baixo = bool(reserva) and 0 <= sfim < reserva and iso >= hoje  # abaixo da reserva (de hoje em diante)
            f.configure(fg_color=SUAVE if (sfim < 0 or baixo) else CARTAO, border_width=2,
                        border_color=ROXO if marcado else AZUL if iso == hoje else BORDA)
            l_dia.configure(text=f"{dia}" + (" ●" if iso == hoje else ""), text_color=TEXTO)
            if rec:
                t_rec = ("○" if rec_prev else "") + "+" + compacto(rec) + (" ✕" if rec_exc else "")
                cor_rec = AZUL_TXT
            elif rec_exc:
                t_rec, cor_rec = "✕" + compacto(rec_exc), MUTED
            else:
                t_rec, cor_rec = "", AZUL_TXT
            l_rec.configure(text=t_rec, text_color=cor_rec)
            if desp:
                pre = "!" if desp_venc else "○" if desp_pend else ""
                l_des.configure(text=f"{pre}−{compacto(desp)}",
                                text_color=TEXTO if desp_venc else ROXO_TXT)
            else:
                l_des.configure(text="")
            if sfim < 0:
                l_sal.configure(text=f"!−{compacto(sfim)}", text_color=TEXTO)
            elif baixo:
                l_sal.configure(text=f"⚠{compacto(sfim)}", text_color=TEXTO)
            elif tem or sfim:
                l_sal.configure(text=compacto(sfim), text_color=MUTED)
            else:
                l_sal.configure(text="")

        # painel da direita
        if self.sel[0] == "dia":
            if not self.sel[1].startswith(pref):
                self.sel = ("dia", hoje if hoje.startswith(pref) else f"{pref}-01")
            iso = self.sel[1]
            d_sel = date.fromisoformat(iso)
            itens = por_dia.get(iso, [])
            _, _, _, _, rec, desp, sfim, _ = info[d_sel.day]
            self.l_dia_titulo.configure(text=f"{DIAS_LONGOS[(d_sel.weekday() + 1) % 7]}, {d_sel:%d/%m/%Y}")
            self.l_dia_resumo.configure(
                text=f"Entradas {brl(rec)} · Saídas {brl(desp)}\nSaldo do dia {brl(rec - desp)} · "
                     f"no fim do dia {brl(sfim)}")
        else:
            i = self.sel[1]
            dias_i = [dia for dia in range(1, n_dias + 1) if (off + dia - 1) % 7 == i]
            itens = [d for dia in dias_i for d in por_dia.get(f"{pref}-{dia:02d}", [])]
            n, r_, s_ = sem[i]
            self.l_dia_titulo.configure(text=f"Todas as {PLURAL[i]} de {MESES[mes - 1].lower()}")
            self.l_dia_resumo.configure(
                text=f"{n} dia(s) · Entradas {brl(r_)} · Saídas {brl(s_)}\n"
                     f"Média por {DIAS_LONGOS[i].split('-')[0].lower()}: +{brl(r_ // max(n, 1))} / "
                     f"−{brl(s_ // max(n, 1))}" + self._txt_historico(i))
        self.tree_dia.delete(*self.tree_dia.get_children())
        for d in sorted(itens, key=lambda x: (x["data"], x["descricao"].lower())):
            tag = d["tipo"] if d["pago"] else ("vencido" if vencido(d) else "pendente")
            self.tree_dia.insert("", "end", iid=d["id"], tags=(tag,), values=(
                d["data"][8:] + "/" + d["data"][5:7], d["descricao"],
                ("+ " if d["tipo"] == "Receita" else "- ") + brl(d["centavos"]),
                "✓ Ok" if d["pago"] else "! Venc." if vencido(d) else "○ Pend."))

    def montar_lancamentos(self, aba):
        aba.grid_columnconfigure(0, weight=1)
        aba.grid_rowconfigure(1, weight=1)

        bar = ctk.CTkFrame(aba, fg_color="transparent")
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.e_busca = ctk.CTkEntry(bar, placeholder_text="🔍 Buscar descrição ou categoria", width=250)
        self.e_busca.pack(side="left")
        self.e_busca.bind("<KeyRelease>", lambda e: self.atualizar_tabela())
        self.f_tipo = ctk.CTkSegmentedButton(bar, values=["Todos", "Receita", "Despesa"],
                                             command=lambda _: self.atualizar_tabela())
        self.f_tipo.set("Todos")
        self.f_tipo.pack(side="left", padx=10)
        self.f_status = ctk.CTkOptionMenu(bar, values=["Todos os status", "Pendentes", "Pagos"],
                                          width=140, command=lambda _: self.atualizar_tabela())
        self.f_status.pack(side="left")

        self.tree = ttk.Treeview(aba, columns=tuple(TITULOS), show="headings", selectmode="extended")
        larg = {"data": (115, "center", False), "tipo": (80, "center", False),
                "categoria": (130, "w", False), "descricao": (260, "w", True),
                "valor": (130, "e", False), "status": (110, "center", False)}
        for c, t in TITULOS.items():
            self.tree.heading(c, text=t, command=lambda c=c: self.ordenar(c))
            self.tree.column(c, width=larg[c][0], anchor=larg[c][1], stretch=larg[c][2])
        self.tree.grid(row=1, column=0, sticky="nsew")
        sb = ctk.CTkScrollbar(aba, command=self.tree.yview)
        sb.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<Delete>", lambda e: self.excluir())
        self.tree.bind("<Double-1>", lambda e: self.iniciar_edicao()
                       if self.tree.identify_region(e.x, e.y) == "cell" else None)

        # mensagem quando a tabela está vazia (criada depois da tabela para ficar por cima)
        self.l_vazio = ctk.CTkLabel(aba, text="", justify="center", text_color=MUTED,
                                    fg_color=CAMPO, font=ctk.CTkFont(size=14))

        rod = ctk.CTkFrame(aba, fg_color="transparent")
        rod.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.l_rodape = ctk.CTkLabel(rod, text="", text_color=MUTED)
        self.l_rodape.pack(side="left")
        b_exc = ctk.CTkButton(rod, text="🗑 Excluir", width=90, fg_color=ROXO_ESC,
                              hover_color=ROXO_ESC_H, command=self.excluir)
        b_exc.pack(side="right")
        Dica(b_exc, "Exclui as linhas selecionadas (Delete). Ctrl+Z desfaz.")
        b_edit = ctk.CTkButton(rod, text="✏ Editar", width=90, command=self.iniciar_edicao)
        b_edit.pack(side="right", padx=8)
        Dica(b_edit, "Edita a linha selecionada (ou dê dois cliques nela).")
        b_pago = ctk.CTkButton(rod, text="✓ Pago / Pendente", width=140, fg_color=AZUL,
                               hover_color=AZUL_H, text_color=BRANCO, command=self.alternar_status)
        b_pago.pack(side="right")
        Dica(b_pago, "Troca as linhas selecionadas entre Pago/Recebido e Pendente.")

    def montar_graficos(self, aba):
        aba.grid_columnconfigure(0, weight=1)
        aba.grid_rowconfigure(0, weight=1)
        self.fig = Figure(figsize=(7, 4), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=aba)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    def montar_metas(self, aba):
        self.l_meta_per = ctk.CTkLabel(aba, text="", text_color=MUTED)
        self.l_meta_per.pack(anchor="w", pady=(0, 6))
        self.quadro_metas = ctk.CTkScrollableFrame(aba)
        self.quadro_metas.pack(fill="both", expand=True)
        self.metas_ui = {}
        self.construir_metas()

    def construir_metas(self):
        self.reconstruindo = True
        q = self.quadro_metas
        for w in q.winfo_children():
            w.destroy()
        q.grid_columnconfigure(2, weight=1)
        ctk.CTkLabel(q, text="Limite mensal por categoria de despesa — digite o valor e pressione Enter",
                     text_color=MUTED).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 2))
        ctk.CTkLabel(q, text="Barra azul = tranquilo · roxa = passou de 80% · branca = estourou o limite",
                     text_color=MUTED, font=ctk.CTkFont(size=11)
                     ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 8))
        self.metas_ui = {}
        for i, cat in enumerate(self.cfg["categorias"]["Despesa"], start=2):
            ctk.CTkLabel(q, text=cat, width=120, anchor="w").grid(row=i, column=0, pady=6, padx=(0, 8))
            e = ctk.CTkEntry(q, width=110, placeholder_text="Limite")
            if cat in self.cfg["metas"]:
                e.insert(0, fmt_input(self.cfg["metas"][cat]))
            e.grid(row=i, column=1, padx=(0, 12))
            barra = ctk.CTkProgressBar(q, height=14)
            barra.set(0)
            barra.grid(row=i, column=2, sticky="ew", padx=(0, 12))
            txt = ctk.CTkLabel(q, text="", width=240, anchor="e")
            txt.grid(row=i, column=3)
            for ev in ("<Return>", "<FocusOut>"):
                e.bind(ev, lambda _ev, c=cat, en=e: self.salvar_meta(c, en))
            self.metas_ui[cat] = (barra, txt)
        self.reconstruindo = False
        self.atualizar_metas()

    # ---------- tema ----------
    def estilo_tabela(self):
        c = self.c
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Treeview", background=c(CAMPO), fieldbackground=c(CAMPO), foreground=c(TEXTO),
                    rowheight=32, borderwidth=0, font=(self.fonte, 11), bordercolor=c(CAMPO),
                    lightcolor=c(CAMPO), darkcolor=c(CAMPO))
        s.configure("Treeview.Heading", background=c(SUAVE), foreground=c(TEXTO), relief="flat",
                    font=(self.fonte, 11, "bold"), padding=(6, 6))
        s.map("Treeview.Heading", background=[("active", c(BORDA))])
        s.map("Treeview", background=[("selected", "#7c3aed")], foreground=[("selected", "#ffffff")])
        s.configure("Dia.Treeview", background=c(CAMPO), fieldbackground=c(CAMPO), foreground=c(TEXTO),
                    rowheight=28, borderwidth=0, font=(self.fonte, 10), bordercolor=c(CAMPO),
                    lightcolor=c(CAMPO), darkcolor=c(CAMPO))
        s.configure("Dia.Treeview.Heading", background=c(SUAVE), foreground=c(TEXTO), relief="flat",
                    font=(self.fonte, 10, "bold"), padding=(4, 4))
        s.map("Dia.Treeview.Heading", background=[("active", c(BORDA))])
        s.map("Dia.Treeview", background=[("selected", "#7c3aed")], foreground=[("selected", "#ffffff")])
        for tv, tam in ((self.tree, 11), (self.tree_dia, 10)):
            for tag, cor in (("Receita", AZUL_TXT), ("Despesa", ROXO_TXT), ("pendente", MUTED)):
                tv.tag_configure(tag, foreground=c(cor))
            tv.tag_configure("vencido", foreground=c(TEXTO), font=(self.fonte, tam, "bold"))

    def trocar_tema(self):
        self.cfg["tema"] = "dark" if self.sw.get() else "light"
        ctk.set_appearance_mode(self.cfg["tema"])
        self.salvar()
        self.after(80, self._aplicar_tema)

    def _aplicar_tema(self):
        self.estilo_tabela()
        self.redesenhar_logo()
        self.sujo = True
        self.desenhar_se_visivel()

    # ---------- feedback ----------
    def aviso(self, texto, ok=False):
        self.l_msg.configure(text=("✓ " if ok else "⚠ ") + texto,
                             text_color=AZUL_TXT if ok else ROXO_TXT)
        if self._aviso_id:
            self.after_cancel(self._aviso_id)
        self._aviso_id = self.after(4500, lambda: self.l_msg.configure(text=""))

    # ---------- formulário ----------
    def trocar_tipo(self, tipo):
        lista = self.cfg["categorias"][tipo]
        self.cat.configure(values=lista)
        self.cat.set(lista[0])

    def achar(self, i):
        return next((d for d in self.lanc if d["id"] == i), None)

    def garantir_categoria(self, tipo, cat):
        """Devolve (nome_normalizado, é_nova)."""
        lista = self.cfg["categorias"][tipo]
        cat = " ".join(cat.split())[:MAX_CAT] or "Outros"
        cat = cat[:1].upper() + cat[1:]
        existente = next((c for c in lista if c.lower() == cat.lower()), None)
        if existente:
            return existente, False
        lista.append(cat)
        return cat, True

    def sincronizar_categorias(self):
        self.cat.configure(values=self.cfg["categorias"][self.tipo.get()])
        self.construir_metas()

    def confirmar(self):
        desc = self.e_desc.get().strip()
        if not desc:
            return self.aviso("Informe a descrição.")
        if len(desc) > MAX_DESC:
            return self.aviso(f"Descrição muito longa (máximo {MAX_DESC} letras).")
        try:
            cents = parse_centavos(self.e_valor.get())
        except (ValueError, InvalidOperation):
            return self.aviso("Valor inválido (ex.: 1.250,90).")
        try:
            d = parse_data(self.e_data.get())
        except ValueError:
            return self.aviso("Data inválida (use dd/mm/aaaa).")
        if not 2000 <= d.year <= 2100:
            return self.aviso("Ano fora do intervalo 2000–2100.")
        if not self.cat.get().strip():
            return self.aviso("Informe a categoria.")
        if len(self.cat.get().strip()) > MAX_CAT:
            return self.aviso(f"Categoria muito longa (máximo {MAX_CAT} letras).")

        datas, numerar = [d], False
        if not self.editando and self.m_rep.get() != MODOS_REP[0]:
            modo = self.m_rep.get()
            limite = 60 if modo == MODOS_REP[1] else 52
            txt = self.e_rep.get().strip() or "1"
            if not txt.isdigit() or not 1 <= int(txt) <= limite:
                return self.aviso(f"Repetições: número de 1 a {limite}.")
            n = int(txt)
            if modo == MODOS_REP[1]:      # todo mês (numera: 1/12, 2/12...)
                datas, numerar = [add_months(d, i) for i in range(n)], n > 1
            elif modo == MODOS_REP[2]:    # toda semana
                datas = [d + timedelta(days=7 * i) for i in range(n)]
            else:                         # só nos dias da semana escolhidos, por n semanas
                dias = {i for i in range(7) if self.rep_dias[i]}
                if not dias:
                    return self.aviso("Escolha pelo menos um dia da semana.")
                datas = [x for x in (d + timedelta(days=k) for k in range(7 * n))
                         if (x.weekday() + 1) % 7 in dias]
            if len(datas) > MAX_LOTE:
                return self.aviso(f"Isso criaria {len(datas)} lançamentos (máximo {MAX_LOTE} de uma vez).")
            if datas[-1].year > 2100:
                return self.aviso("A repetição passa do ano 2100.")

        tipo = self.tipo.get()
        cat, nova = self.garantir_categoria(tipo, self.cat.get())
        pago = self.var_pago.get()

        if self.editando:
            lan = self.achar(self.editando)
            if lan:
                lan.update(tipo=tipo, descricao=desc, categoria=cat, centavos=cents,
                           data=d.isoformat(), pago=pago)
            self.cancelar_edicao()
            msg = "Lançamento atualizado."
        else:
            serie = uuid.uuid4().hex if len(datas) > 1 else None
            hoje = date.today()
            for i, dt in enumerate(datas):
                novo = {"id": uuid.uuid4().hex, "tipo": tipo,
                        "descricao": f"{desc} ({i + 1}/{len(datas)})" if numerar else desc,
                        "categoria": cat, "centavos": cents, "data": dt.isoformat(),
                        "pago": pago and (i == 0 or dt <= hoje)}
                if serie:
                    novo["serie"] = serie
                self.lanc.append(novo)
            self.e_desc.delete(0, "end")
            self.e_valor.delete(0, "end")
            self.var_pago.set(True)
            self.mostrar_rep(resetar=True)
            msg = ("1 lançamento adicionado." if len(datas) == 1 else
                   f"{len(datas)} lançamentos adicionados ({datas[0]:%d/%m} a {datas[-1]:%d/%m}).")
        self.salvar()
        if nova:
            self.sincronizar_categorias()
        self.atualizar()
        self.aviso(msg, ok=True)
        self.e_desc.focus()

    def iniciar_edicao(self):
        sel = self.sel_ids()
        d = self.achar(sel[0]) if len(sel) == 1 else None
        if not d:
            return self.aviso("Selecione 1 lançamento para editar.")
        self.editando = d["id"]
        self.tipo.set(d["tipo"])
        self.trocar_tipo(d["tipo"])
        self.cat.set(d["categoria"])
        for e, v in ((self.e_desc, d["descricao"]), (self.e_valor, fmt_input(d["centavos"])),
                     (self.e_data, datetime.fromisoformat(d["data"]).strftime("%d/%m/%Y"))):
            e.delete(0, "end")
            e.insert(0, v)
        self.var_pago.set(d["pago"])
        self.f_rep.pack_forget()  # repetição só vale ao criar um lançamento novo
        self._rep_visivel = False
        self.l_modo.configure(text="Editando lançamento")
        self.b_ok.configure(text="💾 Salvar alterações")
        self.b_cancel.grid(row=0, column=1, padx=(8, 0))

    def data_padrao(self) -> date:
        """Data inicial do formulário: o dia selecionado no calendário (ou hoje)."""
        try:
            return date.fromisoformat(self.sel[1]) if self.sel[0] == "dia" else date.today()
        except ValueError:
            return date.today()

    def cancelar_edicao(self):
        estava_editando = self.editando is not None
        self.editando = None
        self.e_desc.delete(0, "end")
        self.e_valor.delete(0, "end")
        self.e_data.delete(0, "end")
        self.e_data.insert(0, self.data_padrao().strftime("%d/%m/%Y"))
        self.var_pago.set(True)
        self.l_modo.configure(text="Novo lançamento")
        self.b_ok.configure(text="＋ Adicionar")
        self.b_cancel.grid_remove()
        # a repetição escolhida só é zerada se estávamos editando (senão o usuário perderia o que marcou)
        self.mostrar_rep(resetar=estava_editando)

    def alternar_status(self):
        sel = self.sel_ids()
        if not sel:
            return self.aviso("Selecione os lançamentos na tabela.")
        for i in sel:
            d = self.achar(i)
            if d:
                d["pago"] = not d["pago"]
        self.salvar()
        self.atualizar()
        self.aviso(f"{len(sel)} lançamento(s) atualizado(s).", ok=True)

    def excluir(self):
        sel = self.sel_ids()
        if not sel:
            return self.aviso("Selecione o que excluir.")
        ids, perguntou = set(sel), False
        if len(sel) == 1:
            d = self.achar(sel[0])
            seguintes = ([x for x in self.lanc if x.get("serie") == d["serie"] and x["data"] >= d["data"]]
                         if d and d.get("serie") else [])
            if len(seguintes) > 1:  # faz parte de uma repetição: oferece apagar os seguintes também
                r = messagebox.askyesnocancel(
                    "Excluir", "Este lançamento faz parte de uma repetição.\n\n"
                               f"Sim = excluir este e os {len(seguintes) - 1} seguinte(s)\n"
                               "Não = excluir só este\nCancelar = não excluir")
                if r is None:
                    return
                if r:
                    ids = {x["id"] for x in seguintes}
                perguntou = True
        if not perguntou and not messagebox.askyesno("Excluir", f"Excluir {len(ids)} lançamento(s)?"):
            return
        self.lixeira = [d for d in self.lanc if d["id"] in ids]
        self.lanc = [d for d in self.lanc if d["id"] not in ids]
        if self.editando in ids:
            self.cancelar_edicao()
        self.salvar()
        self.atualizar()
        self.tree.focus_set()
        self.aviso(f"{len(ids)} lançamento(s) excluído(s). Ctrl+Z desfaz.", ok=True)

    def desfazer(self, _e=None):
        try:
            if isinstance(self.focus_get(), tk.Entry):
                return
        except Exception:
            pass
        if not self.lixeira:
            return self.aviso("Nada para desfazer.")
        self.lanc.extend(self.lixeira)
        n, self.lixeira = len(self.lixeira), []
        self.salvar()
        self.atualizar()
        self.aviso(f"{n} lançamento(s) restaurado(s).", ok=True)

    # ---------- CSV ----------
    def exportar(self):
        if not self.lanc:
            return messagebox.showinfo("Exportar", "Nada para exportar.")
        caminho = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                               initialfile="controle_financeiro.csv")
        if not caminho:
            return
        try:
            with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["Data", "Tipo", "Categoria", "Descrição", "Valor", "Status"])
                for d in sorted(self.lanc, key=lambda x: x["data"]):
                    w.writerow([datetime.fromisoformat(d["data"]).strftime("%d/%m/%Y"), d["tipo"],
                                csv_seguro(d["categoria"]), csv_seguro(d["descricao"]),
                                fmt_input(d["centavos"]), "Pago" if d["pago"] else "Pendente"])
        except OSError as e:
            return messagebox.showerror("Exportar", str(e))
        self.aviso("CSV exportado.", ok=True)

    def importar(self):
        caminho = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("Todos os arquivos", "*.*")])
        if not caminho:
            return
        try:
            if os.path.getsize(caminho) > 5_000_000:
                return messagebox.showerror("Importar", "Arquivo grande demais (máximo 5 MB).")
        except OSError as e:
            return messagebox.showerror("Importar", str(e))
        chaves = {(d["data"], d["tipo"], d["categoria"], d["descricao"], d["centavos"]) for d in self.lanc}
        novos, ignorados = [], 0
        try:
            with open(caminho, newline="", encoding="utf-8-sig") as f:
                amostra = f.readline()
                f.seek(0)
                sep = max([";", ",", "\t"], key=amostra.count)  # ; (Excel BR), vírgula ou tab
                for n, lin in enumerate(csv.DictReader(f, delimiter=sep)):
                    if n >= 20000:
                        ignorados += 1
                        break
                    try:
                        tipo = lin["Tipo"].strip().capitalize()
                        if tipo not in ("Receita", "Despesa"):
                            raise ValueError
                        dt = parse_data(lin["Data"])
                        cents = parse_centavos(lin["Valor"])
                        desc = csv_limpo(lin["Descrição"].strip())[:MAX_DESC]
                        cat = csv_limpo((lin["Categoria"] or "").strip())[:MAX_CAT] or "Outros"
                        pago = (lin.get("Status") or "Pago").strip().lower() not in ("pendente", "vencido")
                        if not desc:
                            raise ValueError
                    except (ValueError, KeyError, InvalidOperation, AttributeError):
                        ignorados += 1
                        continue
                    k = (dt.isoformat(), tipo, cat, desc, cents)
                    if k in chaves:
                        ignorados += 1
                        continue
                    chaves.add(k)
                    novos.append({"id": uuid.uuid4().hex, "tipo": tipo, "descricao": desc, "categoria": cat,
                                  "centavos": cents, "data": dt.isoformat(), "pago": pago})
        except (OSError, UnicodeDecodeError, csv.Error) as e:
            return messagebox.showerror("Importar", f"Não consegui ler o arquivo:\n{e}")
        if not novos:
            return messagebox.showinfo("Importar", f"Nada novo para importar ({ignorados} linha(s) ignorada(s)).")
        if not messagebox.askyesno("Importar", f"Importar {len(novos)} lançamento(s)?\n"
                                               f"({ignorados} ignorado(s): duplicados ou inválidos)"):
            return
        for d in novos:  # usa o nome normalizado da categoria (evita 'alimentação' x 'Alimentação')
            d["categoria"], _ = self.garantir_categoria(d["tipo"], d["categoria"])
        self.lanc.extend(novos)
        self.salvar()
        self.sincronizar_categorias()
        self.atualizar()
        self.aviso(f"{len(novos)} lançamento(s) importado(s).", ok=True)

    # ---------- metas ----------
    def salvar_meta(self, cat, e):
        if self.reconstruindo:
            return
        txt = e.get().strip()
        if not txt:
            if self.cfg["metas"].pop(cat, None) is not None:
                self.salvar()
        else:
            try:
                novo = parse_centavos(txt)
            except (ValueError, InvalidOperation):
                return self.aviso(f"Meta inválida em {cat}.")
            if self.cfg["metas"].get(cat) != novo:
                self.cfg["metas"][cat] = novo
                self.salvar()
        self.atualizar_metas()

    def atualizar_metas(self):
        p = self.periodo() or date.today().strftime("%Y-%m")
        self.l_meta_per.configure(text=f"Período: {p[5:]}/{p[:4]}")
        gasto = {}
        for d in self.lanc:
            if d["tipo"] == "Despesa" and d["data"].startswith(p):
                gasto[d["categoria"]] = gasto.get(d["categoria"], 0) + d["centavos"]
        for cat, (barra, txt) in self.metas_ui.items():
            g, lim = gasto.get(cat, 0), self.cfg["metas"].get(cat)
            if lim:
                r = g / lim
                barra.configure(progress_color=AZUL if r <= 0.8 else ROXO if r <= 1 else TEXTO)
                barra.set(min(r, 1))
                txt.configure(text=f"{brl(g)} / {brl(lim)}  ({r:.0%})" + ("  ⚠ estourou" if r > 1 else ""))
            else:
                barra.set(0)
                txt.configure(text=f"{brl(g)} · sem meta")

    # ---------- dados / atualização ----------
    def periodo(self):
        m = self.filtro.get()
        if m == "Todos":
            return None
        mm, aaaa = m.split("/")
        return f"{aaaa}-{mm}"

    def do_periodo(self):
        p = self.periodo()
        return self.lanc if p is None else [d for d in self.lanc if d["data"].startswith(p)]

    def mover_mes(self, delta):
        if self.filtro.get() == "Todos":  # sai do 'Todos' direto para o mês atual
            self.filtro.set(date.today().strftime("%m/%Y"))
            return self.atualizar()
        ops = list(self.filtro.cget("values"))
        i = ops.index(self.filtro.get()) if self.filtro.get() in ops else 0
        self.filtro.set(ops[max(1, min(len(ops) - 1, i + delta))])  # nunca cai em 'Todos' sem querer
        self.atualizar()

    def ordenar(self, col):
        self.ordem = (col, not self.ordem[1]) if self.ordem[0] == col else (col, col in ("data", "valor"))
        self.atualizar_tabela()

    def atualizar(self):
        hoje = date.today()
        usados = {d["data"][:7] for d in self.lanc} | {hoje.strftime("%Y-%m")}
        ini, fim = min(usados), max(max(usados), add_months(hoje, 3).strftime("%Y-%m"))
        meses, a, m = [], int(ini[:4]), int(ini[5:])
        while f"{a:04d}-{m:02d}" <= fim:  # meses seguidos, sem buracos
            meses.append(f"{a:04d}-{m:02d}")
            a, m = (a + 1, 1) if m == 12 else (a, m + 1)
        meses.reverse()
        ops = ["Todos"] + [f"{x[5:]}/{x[:4]}" for x in meses]
        self.filtro.configure(values=ops)
        if self.filtro.get() not in ops:
            self.filtro.set(hoje.strftime("%m/%Y"))

        dados = self.do_periodo()
        rec = sum(d["centavos"] for d in dados if d["tipo"] == "Receita")
        rec_ok = sum(d["centavos"] for d in dados if d["tipo"] == "Receita" and d["pago"])
        desp = sum(d["centavos"] for d in dados if d["tipo"] == "Despesa")
        desp_ok = sum(d["centavos"] for d in dados if d["tipo"] == "Despesa" and d["pago"])
        pend = [d for d in dados if d["tipo"] == "Despesa" and not d["pago"]]
        n_venc = sum(1 for d in pend if vencido(d))

        self.l_rec.configure(text=brl(rec))
        self.s_rec.configure(text=f"recebido: {brl(rec_ok)}")
        self.l_desp.configure(text=brl(desp))
        self.s_desp.configure(text=f"pago: {brl(desp_ok)}")
        self.l_saldo.configure(text=brl(rec_ok - desp_ok),
                               text_color=AZUL_TXT if rec_ok >= desp_ok else ROXO_TXT)
        self.s_saldo.configure(text="recebido − pago")
        self.l_pend.configure(text=brl(sum(d["centavos"] for d in pend)),
                              text_color=ROXO_TXT if n_venc else TEXTO)
        self.s_pend.configure(text=f"! {n_venc} vencida(s)" if n_venc else "tudo em dia")

        self.atualizar_tabela()
        self.atualizar_metas()
        self.atualizar_calendario()
        self.sujo = True
        self.desenhar_se_visivel()

    def atualizar_tabela(self):
        termo = self.e_busca.get().strip().lower()
        tipo, st = self.f_tipo.get(), self.f_status.get()
        linhas = [d for d in self.do_periodo()
                  if (tipo == "Todos" or d["tipo"] == tipo)
                  and (st == "Todos os status" or (st == "Pagos") == d["pago"])
                  and (not termo or termo in d["descricao"].lower() or termo in d["categoria"].lower())]
        col, desc = self.ordem
        chave = {"data": lambda d: d["data"], "tipo": lambda d: d["tipo"],
                 "categoria": lambda d: d["categoria"].lower(),
                 "descricao": lambda d: d["descricao"].lower(),
                 "valor": lambda d: d["centavos"],
                 "status": lambda d: (d["pago"], d["data"])}[col]
        linhas.sort(key=chave, reverse=desc)

        self.tree.delete(*self.tree.get_children())
        for d in linhas:
            tag = d["tipo"] if d["pago"] else ("vencido" if vencido(d) else "pendente")
            self.tree.insert("", "end", iid=d["id"], tags=(tag,), values=(
                datetime.fromisoformat(d["data"]).strftime("%d/%m/%Y"), d["tipo"], d["categoria"],
                d["descricao"], ("+ " if d["tipo"] == "Receita" else "- ") + brl(d["centavos"]),
                status_txt(d)))
        for c, t in TITULOS.items():
            self.tree.heading(c, text=t + ((" ▼" if desc else " ▲") if c == col else ""))
        liq = sum(d["centavos"] if d["tipo"] == "Receita" else -d["centavos"] for d in linhas)
        self.l_rodape.configure(text=f"{len(linhas)} lançamento(s) · resultado listado: {brl(liq)}")

        # mensagem de tabela vazia
        if linhas:
            self.l_vazio.place_forget()
        else:
            if not self.lanc:
                msg = ("Nenhum lançamento ainda.\n\n"
                       "← Preencha o formulário à esquerda e clique em ＋ Adicionar.\n"
                       "Primeira vez aqui? Aperte F1 para abrir o guia rápido.")
            else:
                msg = "Nada encontrado com esses filtros.\nTente outro período, busca ou status."
            self.l_vazio.configure(text=msg)
            self.l_vazio.place(relx=0.5, rely=0.5, anchor="center")
            self.l_vazio.lift()

    # ---------- gráficos (só desenha quando a aba está visível) ----------
    def desenhar_se_visivel(self, *_):
        if self.sujo and self.abas.get() == "Gráficos":
            self.desenhar_graficos()
            self.sujo = False

    def desenhar_graficos(self):
        c = self.c
        bg, fg = c(PAINEL), c(TEXTO)
        azul, roxo = c(AZUL_TXT), c(ROXO_TXT)
        self.fig.clear()
        self.fig.set_facecolor(bg)
        gs = self.fig.add_gridspec(2, 2, hspace=0.42, wspace=0.22,
                                   left=0.06, right=0.98, top=0.93, bottom=0.07)
        ax_d, ax_r, ax_b, ax_s = (self.fig.add_subplot(gs[i, j]) for i in (0, 1) for j in (0, 1))
        for ax in (ax_d, ax_r, ax_b, ax_s):
            ax.set_facecolor(bg)
            ax.tick_params(colors=fg, labelsize=8)
            for sp in ax.spines.values():
                sp.set_color(fg)
                sp.set_alpha(0.25)

        periodo = self.do_periodo()
        suf = f" — {self.filtro.get()}" if self.periodo() else ""

        def vazio(ax, txt="Sem dados"):
            ax.text(0.5, 0.5, txt, ha="center", va="center", color=fg, transform=ax.transAxes)
            ax.axis("off")

        def rosca(ax, tipo, titulo, cores):
            ax.set_title(titulo + suf, color=fg, fontsize=11)
            cats = {}
            for d in periodo:
                if d["tipo"] == tipo:
                    cats[d["categoria"]] = cats.get(d["categoria"], 0) + d["centavos"]
            if not cats:
                return vazio(ax)
            total = sum(cats.values())
            ordenado = sorted(cats.items(), key=lambda kv: -kv[1])
            grandes = [kv for kv in ordenado[:6] if kv[1] / total >= 0.04]
            resto = total - sum(v for _, v in grandes)
            itens = grandes + ([("Outras", resto)] if resto else [])
            ax.pie([v for _, v in itens], labels=[k for k, _ in itens], colors=cores, startangle=90,
                   autopct=lambda p: f"{p:.0f}%" if p >= 6 else "", pctdistance=0.8,
                   wedgeprops={"width": 0.45, "edgecolor": bg, "linewidth": 2},
                   textprops={"color": fg, "fontsize": 8})
            ax.text(0, 0, brl(sum(v for _, v in itens)), ha="center", va="center",
                    color=fg, fontsize=10, fontweight="bold")

        rosca(ax_d, "Despesa", "Despesas por categoria", PALETA)
        rosca(ax_r, "Receita", "Receitas por categoria", PALETA[1:] + PALETA[:1])

        milhar = FuncFormatter(lambda v, _: f"{v / 1000:.0f}k" if abs(v) >= 1000 else f"{v:.0f}")

        # barras: receitas x despesas por mês (últimos 12 meses, todos os dados)
        ax_b.set_title("Receitas x Despesas por mês", color=fg, fontsize=11)
        mes = {}
        for d in self.lanc:
            mes.setdefault(d["data"][:7], [0, 0])[0 if d["tipo"] == "Receita" else 1] += d["centavos"] / 100
        if mes:
            ks = sorted(mes)[-12:]
            x = list(range(len(ks)))
            ax_b.bar([i - 0.2 for i in x], [mes[k][0] for k in ks], 0.4, color=azul, label="Receitas")
            ax_b.bar([i + 0.2 for i in x], [mes[k][1] for k in ks], 0.4, color=roxo, label="Despesas")
            ax_b.set_xticks(x)
            ax_b.set_xticklabels([f"{k[5:]}/{k[2:4]}" for k in ks])
            ax_b.yaxis.set_major_formatter(milhar)
            ax_b.grid(axis="y", alpha=0.15)
            leg = ax_b.legend(fontsize=8, facecolor=bg, edgecolor="none")
            for t in leg.get_texts():
                t.set_color(fg)
        else:
            vazio(ax_b)

        # linha: saldo acumulado do período (previsto: todos os lançamentos)
        ax_s.set_title("Saldo acumulado (previsto)" + suf, color=fg, fontsize=11)
        if periodo:
            acum, xs, ys = 0, [], []
            for d in sorted(periodo, key=lambda x: x["data"]):
                acum += (d["centavos"] if d["tipo"] == "Receita" else -d["centavos"]) / 100
                xs.append(datetime.fromisoformat(d["data"]))
                ys.append(acum)
            ax_s.plot(xs, ys, color=c(ROXO), marker="o", markersize=4, linewidth=2)
            ax_s.fill_between(xs, ys, 0, where=[y >= 0 for y in ys], color=azul, alpha=0.25, interpolate=True)
            ax_s.fill_between(xs, ys, 0, where=[y < 0 for y in ys], color=roxo, alpha=0.25, interpolate=True)
            ax_s.axhline(0, color=fg, alpha=0.3, linewidth=0.8)
            ax_s.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=6))
            ax_s.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
            ax_s.yaxis.set_major_formatter(milhar)
            ax_s.margins(x=0.05)
            ax_s.grid(alpha=0.15)
        else:
            vazio(ax_s)

        self.canvas.draw_idle()


if __name__ == "__main__":
    App().mainloop()