"""
main.py — abre o CineAI.

Como usar (na pasta do projeto):
    python main.py

Também é a "porta de entrada" do CineAI.exe (veja construir_exe.py).
"""
import multiprocessing
import os
import sys
import traceback


def preparar_executavel():
    """
    Ajustes que só valem no CineAI.exe:
      - ele não tem a janela preta do terminal, então print() e as barras de
        progresso do sentence-transformers vão para dados/cineai.log
        (sem isso, alguns pacotes quebram ao tentar escrever na tela);
      - usa o modelo de embeddings que já está baixado, sem ir à internet.
    """
    from cineai.caminhos import CAMINHO_LOG

    CAMINHO_LOG.parent.mkdir(parents=True, exist_ok=True)
    arquivo_log = open(CAMINHO_LOG, "w", encoding="utf-8", buffering=1)
    sys.stdout = arquivo_log
    sys.stderr = arquivo_log
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def mostrar_erro_ao_abrir(erro_texto):
    """No .exe um erro some sem aviso; aqui ele aparece numa janelinha (e fica no log)."""
    print(erro_texto)
    try:
        import tkinter
        from tkinter import messagebox
        from cineai.caminhos import CAMINHO_LOG

        raiz = tkinter.Tk()
        raiz.withdraw()
        messagebox.showerror(
            "CineAI não conseguiu abrir",
            f"{erro_texto.strip().splitlines()[-1]}\n\n"
            "Confira se o Ollama está instalado e se o catálogo (dados/filmes.json) está na pasta.\n\n"
            f"Detalhes em:\n{CAMINHO_LOG}"
        )
        raiz.destroy()
    except Exception:
        pass


def main():
    from cineai.caminhos import esta_no_executavel

    if esta_no_executavel():
        preparar_executavel()
    try:
        from cineai import interface
    except Exception:
        mostrar_erro_ao_abrir(traceback.format_exc())
        sys.exit(1)
    interface.iniciar()


if __name__ == "__main__":
    multiprocessing.freeze_support()   # o .exe precisa disso antes de tudo (o torch usa multiprocessing)
    main()