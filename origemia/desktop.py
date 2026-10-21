"""Interface desktop Tkinter. A análise ocorre fora da thread da interface."""

from pathlib import Path
from queue import Empty, Queue
from threading import Thread
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .analysis import analyze
from .classifier import Classifier
from .report import render_text, save_report

BG, PANEL, FG, MUTED, ACCENT = "#101722", "#182333", "#f0f4fa", "#a7b8cd", "#58dcc2"


class App:
    def __init__(self, root):
        self.root = root
        self.events = Queue()
        self.report = None
        self.source = None
        self.model = None
        self.model_offline = None
        self.path = tk.StringVar()
        self.use_ai = tk.BooleanVar(value=True)
        self.offline = tk.BooleanVar(value=False)
        self.frames = tk.IntVar(value=12)
        self.status = tk.StringVar(value="Escolha uma foto ou vídeo para começar.")
        root.title("OrigemIA • Análise de imagens e vídeos")
        root.geometry("1040x790")
        root.minsize(720, 600)
        root.configure(bg=BG)
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 11))
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Title.TLabel", font=("Segoe UI", 27, "bold"))
        style.configure("TButton", font=("Segoe UI", 11), padding=(14, 9))
        style.configure("Accent.TButton", background=ACCENT, foreground=BG)
        style.configure("TCheckbutton", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.map("TCheckbutton", background=[("active", BG)], foreground=[("active", FG)])
        outer = ttk.Frame(root, padding=26)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="OrigemIA", style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Investigue a origem. Examine as evidências.",
                  style="Muted.TLabel").pack(anchor="w", pady=(3, 14))
        note = tk.Label(outer, text="EXPERIMENTAL  •  Pode errar. Escores não comprovam origem.",
                        bg=PANEL, fg=ACCENT, anchor="w", padx=14, pady=12,
                        font=("Segoe UI", 11, "bold"))
        note.pack(fill="x", pady=(0, 18))
        row = ttk.Frame(outer)
        row.pack(fill="x")
        self.entry = ttk.Entry(row, textvariable=self.path, font=("Segoe UI", 11))
        self.entry.pack(side="left", fill="x", expand=True)
        self.browse_button = ttk.Button(row, text="Selecionar arquivo", command=self.browse)
        self.browse_button.pack(side="left", padx=(10, 0))
        options = ttk.Frame(outer)
        options.pack(fill="x", pady=12)
        self.ai_check = ttk.Checkbutton(options, text="Usar classificador de IA", variable=self.use_ai)
        self.ai_check.grid(row=0, column=0, sticky="w", padx=(0, 14))
        self.offline_check = ttk.Checkbutton(options, text="Offline (modelo já baixado)", variable=self.offline)
        self.offline_check.grid(row=0, column=1, sticky="w")
        ttk.Label(options, text="Quadros do vídeo:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.spinner = ttk.Spinbox(options, from_=1, to=32, textvariable=self.frames, width=5)
        self.spinner.grid(row=1, column=1, sticky="w", pady=(8, 0))
        ttk.Label(outer, text="Primeiro uso de IA: requer instalação do módulo IA e download do modelo.\n"
                  "Fotos e vídeos são processados no seu computador; nenhum arquivo é enviado pelo app.",
                  style="Muted.TLabel", wraplength=900).pack(anchor="w", pady=(0, 12))
        actions = ttk.Frame(outer)
        actions.pack(fill="x")
        self.run_button = ttk.Button(actions, text="Analisar conteúdo", style="Accent.TButton", command=self.start)
        self.run_button.pack(side="left")
        self.export_button = ttk.Button(actions, text="Salvar relatório", command=self.export, state="disabled")
        self.export_button.pack(side="left", padx=10)
        self.bar = ttk.Progressbar(outer, mode="indeterminate")
        self.bar.pack(fill="x", pady=(14, 6))
        ttk.Label(outer, textvariable=self.status, style="Muted.TLabel", wraplength=900).pack(anchor="w")
        box = ttk.Frame(outer)
        box.pack(fill="both", expand=True, pady=(12, 0))
        self.output = tk.Text(box, bg=PANEL, fg=FG, insertbackground=FG, wrap="word",
                              padx=18, pady=16, relief="flat", font=("Segoe UI", 11),
                              state="disabled", height=12)
        scroll = ttk.Scrollbar(box, command=self.output.yview)
        self.output.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.output.pack(fill="both", expand=True)
        self.set_output("Seu relatório aparecerá aqui.\n\n"
                        "• Fotos: classificador experimental e metadados disponíveis.\n"
                        "• Vídeos: escores de quadros amostrados; sem análise de áudio ou movimento.\n"
                        "• Sem classificador: inspeção técnica, com origem inconclusiva.\n\n"
                        "Credenciais C2PA e marcas-d'água não são verificadas nesta versão.")
        root.after(100, self.poll)

    def set_output(self, text):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def browse(self):
        path = filedialog.askopenfilename(title="Selecione uma mídia local", filetypes=[
            ("Fotos e vídeos", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.mp4 *.mov *.avi *.mkv *.webm"),
            ("Todos os arquivos", "*.*")])
        if path:
            self.path.set(path)

    def busy(self, active):
        for widget in (self.run_button, self.browse_button, self.entry, self.ai_check,
                       self.offline_check, self.spinner):
            widget.configure(state="disabled" if active else "normal")
        self.export_button.configure(state="normal" if self.report and not active else "disabled")
        self.bar.start(12) if active else self.bar.stop()

    def start(self):
        try:
            count = self.frames.get()
            if not 1 <= count <= 32:
                raise ValueError()
        except (ValueError, tk.TclError):
            messagebox.showerror("Quadros inválidos", "Escolha um número inteiro de 1 a 32.")
            return
        path, use_ai, offline = self.path.get().strip(), self.use_ai.get(), self.offline.get()
        if not path:
            messagebox.showinfo("Selecione um arquivo", "Escolha uma foto ou vídeo local.")
            return
        self.report = None
        self.busy(True)
        self.status.set("Preparando análise…")
        self.set_output("Analisando… O carregamento inicial do modelo pode demorar alguns minutos.")

        def work():
            try:
                if use_ai and (self.model is None or self.model_offline != offline):
                    self.model, self.model_offline = Classifier(offline=offline), offline
                result = analyze(path, self.model if use_ai else None, frames=count,
                                 progress=lambda text: self.events.put(("progress", text)))
                self.events.put(("done", (result, path)))
            except Exception as exc:
                self.events.put(("error", str(exc)))

        Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "progress":
                    self.status.set(value)
                elif kind == "done":
                    self.report, self.source = value
                    self.set_output(render_text(self.report))
                    self.status.set("Análise concluída. Consulte o estado do classificador e os limites no relatório.")
                    self.busy(False)
                else:
                    self.set_output(f"Não foi possível concluir a análise.\n\n{value}")
                    self.status.set("Falha na análise. Verifique o arquivo e tente novamente.")
                    self.busy(False)
        except Empty:
            pass
        self.root.after(100, self.poll)

    def export(self):
        if not self.report:
            return
        path = filedialog.asksaveasfilename(title="Novo relatório", defaultextension=".json",
            initialfile=f"{Path(self.source).stem}_relatorio.json",
            filetypes=[("JSON", "*.json"), ("Texto", "*.txt")])
        if path:
            try:
                save_report(self.report, path, self.source)
                self.status.set("Relatório salvo.")
            except (ValueError, OSError) as exc:
                messagebox.showerror("Não foi possível salvar", str(exc) + "\nEscolha um nome de arquivo novo.")


def main():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise SystemExit("Interface gráfica indisponível. Execute origemia --help pelo terminal. " + str(exc))
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
