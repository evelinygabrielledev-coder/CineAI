"""
caminhos.py — onde fica cada coisa do CineAI (um lugar só para todos os arquivos).

    assistente_filmes/
    ├── main.py          ← abre o programa
    ├── cineai/          ← o código do programa (este arquivo está aqui)
    ├── importadores/    ← scripts que montam o catálogo
    ├── dados/           ← catálogo, pôsteres e os SEUS dados
    ├── testes/
    └── .env             ← suas chaves (fica na raiz)

Pelo CineAI.exe, a pasta do projeto é procurada a partir da pasta do .exe
(veja pasta_do_projeto()).

Os testes automáticos trocam alguns destes caminhos por variáveis de ambiente
(CINEAI_CATALOGO, CINEAI_CACHE, CINEAI_PASTA_USUARIO) para não mexer nos seus dados.
"""
import os
import sys
from pathlib import Path

PASTAS_ACIMA_DO_EXE = 3   # dist/CineAI/CineAI.exe -> dist -> pasta do projeto


def esta_no_executavel():
    """True quando roda pelo CineAI.exe (feito com o PyInstaller), e não pelo python main.py."""
    return getattr(sys, "frozen", False)


def pasta_do_projeto():
    """
    Pelo python: a pasta acima de cineai/.
    Pelo .exe: a primeira pasta (a do .exe ou alguma acima dela) que tem dados/filmes.json.
    Assim o CineAI.exe dentro de dist/CineAI/ usa o MESMO diário do python main.py,
    e quem copiar a pasta do .exe para outro lugar só precisa levar a pasta dados/ junto.
    CINEAI_PASTA_PROJETO (variável de ambiente) escolhe outra pasta, se precisar.
    """
    if os.environ.get("CINEAI_PASTA_PROJETO"):
        return Path(os.environ["CINEAI_PASTA_PROJETO"]).resolve()
    if not esta_no_executavel():
        return Path(__file__).resolve().parent.parent
    pasta_exe = Path(sys.executable).resolve().parent
    candidata = pasta_exe
    for _ in range(PASTAS_ACIMA_DO_EXE + 1):
        if (candidata / "dados" / "filmes.json").exists():
            return candidata
        candidata = candidata.parent
    return pasta_exe   # não achou: cria dados/ ao lado do .exe


PASTA_PROJETO = pasta_do_projeto()
PASTA_DADOS = PASTA_PROJETO / "dados"
PASTA_POSTERS = PASTA_DADOS / "posters"

CAMINHO_CATALOGO = Path(os.environ.get("CINEAI_CATALOGO", PASTA_DADOS / "filmes.json"))
CAMINHO_CATALOGO_MANUAL = PASTA_DADOS / "filmes_manual.json"
CAMINHO_CACHE_EMBEDDINGS = Path(os.environ.get("CINEAI_CACHE", PASTA_DADOS / "embeddings_cache.pkl"))

# Seus dados (favoritos, diário, conversas)
PASTA_USUARIO = Path(os.environ.get("CINEAI_PASTA_USUARIO", PASTA_DADOS))

CAMINHO_ENV = PASTA_PROJETO / ".env"

# Arquivos que vão DENTRO do .exe (o ícone). Pelo python, ficam na pasta do projeto.
PASTA_RECURSOS = Path(getattr(sys, "_MEIPASS", PASTA_PROJETO))
CAMINHO_ICONE = PASTA_RECURSOS / "cineai.ico"
CAMINHO_LOG = PASTA_DADOS / "cineai.log"   # erros do .exe (ele não tem janela preta para mostrar)