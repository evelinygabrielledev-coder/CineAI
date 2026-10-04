"""
montar_portatil.py — monta a pasta "CineAI portátil", para usar o CineAI em outro computador.

Como usar (na pasta do projeto, depois do python construir_exe.py):
    python montar_portatil.py          -> cria a pasta "CineAI portátil" aqui
    python montar_portatil.py --zip    -> e também um "CineAI portátil.zip" (para mandar)

O que vai na pasta:
    CineAI.exe + _internal/      o programa (do dist/CineAI)
    dados/filmes.json            o catálogo
    dados/posters/               os pôsteres
    dados/embeddings_cache.pkl   para não recalcular tudo na primeira vez
    dados/modelo_embeddings/     o modelo que entende as sinopses (no outro PC ele não está baixado)
    LEIA-ME.txt                  o passo a passo para quem for usar

O que NÃO vai (é seu): usuario.json, conversas.json, backups/, exportados/ e o .env.
Quem abrir lá começa com um diário em branco.
"""
import os
import shutil
import sys
from pathlib import Path

PASTA_PROJETO = Path(__file__).resolve().parent
PASTA_EXE = PASTA_PROJETO / "dist" / "CineAI"
PASTA_DADOS = PASTA_PROJETO / "dados"
DESTINO = PASTA_PROJETO / "CineAI portátil"

ARQUIVOS_DO_CATALOGO = ["filmes.json", "filmes_manual.json", "embeddings_cache.pkl"]
NOME_DO_MODELO = "paraphrase-multilingual-MiniLM-L12-v2"

LEIA_ME = """CineAI — seu diário de cinema
=============================

1. Instale o Ollama (a IA que conversa):  https://ollama.com
   Depois, no Prompt de Comando, rode uma vez:
       ollama pull qwen3:1.7b

2. Dê dois cliques em CineAI.exe.
   - Se aparecer "O Windows protegeu o computador": clique em "Mais informações"
     e depois em "Executar assim mesmo" (o programa não tem assinatura digital).
   - A primeira abertura demora um pouquinho.

3. Para ter um atalho: botão direito no CineAI.exe > Enviar para > Área de trabalho.
   (Não copie o CineAI.exe sozinho: ele precisa da pasta _internal e da pasta dados ao lado.)

O seu diário fica em dados/usuario.json. Faça backup pela Capa do Meu diário.
Sem o Ollama aberto, o CineAI abre do mesmo jeito, mas as respostas que precisam da IA não funcionam.
"""


def pastas_de_cache_do_huggingface():
    """Onde o sentence-transformers costuma guardar os modelos baixados."""
    candidatas = []
    if os.environ.get("HF_HUB_CACHE"):
        candidatas.append(Path(os.environ["HF_HUB_CACHE"]))
    if os.environ.get("HF_HOME"):
        candidatas.append(Path(os.environ["HF_HOME"]) / "hub")
    candidatas.append(Path.home() / ".cache" / "huggingface" / "hub")
    return candidatas


def achar_modelo():
    """A pasta com os arquivos do modelo (a "snapshot" mais nova), ou None."""
    for cache in pastas_de_cache_do_huggingface():
        pasta = cache / f"models--sentence-transformers--{NOME_DO_MODELO}" / "snapshots"
        if pasta.is_dir():
            versoes = [versao for versao in pasta.iterdir() if (versao / "modules.json").exists()]
            if versoes:
                return max(versoes, key=lambda versao: versao.stat().st_mtime)
    antiga = Path.home() / ".cache" / "torch" / "sentence_transformers" / f"sentence-transformers_{NOME_DO_MODELO}"
    return antiga if (antiga / "modules.json").exists() else None


def tamanho_da_pasta(pasta):
    return sum(arquivo.stat().st_size for arquivo in pasta.rglob("*") if arquivo.is_file())


def montar(fazer_zip=False):
    if not (PASTA_EXE / "CineAI.exe").exists() and not (PASTA_EXE / "CineAI").exists():
        sys.exit("Ainda não existe o dist/CineAI. Rode antes:  python construir_exe.py")
    if not (PASTA_DADOS / "filmes.json").exists():
        sys.exit("Não achei o dados/filmes.json (o catálogo).")

    modelo = achar_modelo()
    if modelo is None:
        sys.exit(
            "Não achei o modelo de embeddings baixado neste computador.\n"
            "Abra o CineAI uma vez pelo python main.py (com internet) para ele baixar e rode de novo."
        )

    if DESTINO.exists():
        print(f"Apagando a versão antiga de \"{DESTINO.name}\"...")
        shutil.rmtree(DESTINO)

    print("1/4  Copiando o programa (CineAI.exe e _internal)... (pode demorar)")
    shutil.copytree(PASTA_EXE, DESTINO)

    print("2/4  Copiando o catálogo e os pôsteres...")
    dados_destino = DESTINO / "dados"
    dados_destino.mkdir(exist_ok=True)
    for nome in ARQUIVOS_DO_CATALOGO:
        if (PASTA_DADOS / nome).exists():
            shutil.copy2(PASTA_DADOS / nome, dados_destino / nome)
    if (PASTA_DADOS / "posters").is_dir():
        shutil.copytree(PASTA_DADOS / "posters", dados_destino / "posters")

    print("3/4  Copiando o modelo de embeddings...")
    shutil.copytree(modelo, dados_destino / "modelo_embeddings")   # copia os arquivos de verdade (não atalhos)

    print("4/4  Escrevendo o LEIA-ME.txt...")
    (DESTINO / "LEIA-ME.txt").write_text(LEIA_ME, encoding="utf-8")

    # Conferência: nada pessoal foi junto
    pessoais = [nome for nome in ("usuario.json", "conversas.json", "backups", "exportados") if (dados_destino / nome).exists()]
    if pessoais:
        sys.exit(f"Algo pessoal foi copiado sem querer: {pessoais}. Apague a pasta e me avise.")

    tamanho_gb = tamanho_da_pasta(DESTINO) / 1024 ** 3
    print(f"\nPronto! Pasta: {DESTINO}  ({tamanho_gb:.1f} GB)")

    if fazer_zip:
        print("Compactando (pode demorar alguns minutos)...")
        arquivo_zip = shutil.make_archive(str(DESTINO), "zip", root_dir=DESTINO.parent, base_dir=DESTINO.name)
        print(f"Zip: {arquivo_zip}  ({Path(arquivo_zip).stat().st_size / 1024 ** 3:.1f} GB)")

    print("\nNo outro computador: copie a pasta inteira e siga o LEIA-ME.txt (precisa do Ollama).")
    if sys.platform.startswith("win"):
        os.startfile(DESTINO)


if __name__ == "__main__":
    montar(fazer_zip="--zip" in sys.argv)
