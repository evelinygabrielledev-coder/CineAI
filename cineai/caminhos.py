"""
caminhos.py — onde fica cada coisa do CineAI (um lugar só para todos os arquivos).

    assistente_filmes/
    ├── main.py          ← abre o programa
    ├── cineai/          ← o código do programa (este arquivo está aqui)
    ├── importadores/    ← scripts que montam o catálogo
    ├── dados/           ← catálogo, pôsteres e os SEUS dados
    ├── testes/
    └── .env             ← suas chaves (fica na raiz)

Os testes automáticos trocam alguns destes caminhos por variáveis de ambiente
(CINEAI_CATALOGO, CINEAI_CACHE, CINEAI_PASTA_USUARIO) para não mexer nos seus dados.
"""
import os
from pathlib import Path

PASTA_PROJETO = Path(__file__).resolve().parent.parent
PASTA_DADOS = PASTA_PROJETO / "dados"
PASTA_POSTERS = PASTA_DADOS / "posters"

CAMINHO_CATALOGO = Path(os.environ.get("CINEAI_CATALOGO", PASTA_DADOS / "filmes.json"))
CAMINHO_CATALOGO_MANUAL = PASTA_DADOS / "filmes_manual.json"
CAMINHO_CACHE_EMBEDDINGS = Path(os.environ.get("CINEAI_CACHE", PASTA_DADOS / "embeddings_cache.pkl"))

# Seus dados (favoritos, diário, conversas)
PASTA_USUARIO = Path(os.environ.get("CINEAI_PASTA_USUARIO", PASTA_DADOS))

CAMINHO_ENV = PASTA_PROJETO / ".env"
