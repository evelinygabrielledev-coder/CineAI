"""
importar_letterboxd.py — traz o seu diário do Letterboxd para o CineAI.

1. No Letterboxd: Settings › Data › Export your data (ele baixa um .zip).
2. Na pasta do projeto:

    python importadores/importar_letterboxd.py caminho/do/arquivo.zip
        -> junta ao diário os filmes que já estão no catálogo

    python importadores/importar_letterboxd.py caminho/do/arquivo.zip --adicionar
        -> antes, busca no TMDB os filmes que faltam no catálogo e coloca eles lá
           (com pôster). Precisa da chave do TMDB no .env.

    python importadores/importar_letterboxd.py caminho/do/arquivo.zip --simular
        -> só mostra o que aconteceria, sem mudar nada

Também dá para importar pela janela: Meu diário › Capa › "📥 importar do Letterboxd"
(sem o --adicionar, que precisa da internet e da chave).
"""
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))  # deixa achar as pastas cineai/ e importadores/
import json
import sys
from pathlib import Path

from cineai import letterboxd                           # noqa: E402
from cineai.caminhos import CAMINHO_CATALOGO, PASTA_POSTERS  # noqa: E402


def carregar_catalogo():
    with open(CAMINHO_CATALOGO, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def salvar_catalogo(catalogo):
    temporario = CAMINHO_CATALOGO.with_suffix(".tmp")
    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump(catalogo, arquivo, ensure_ascii=False, indent=2)
    temporario.replace(CAMINHO_CATALOGO)


def adicionar_os_que_faltam(catalogo, caminho_zip):
    """Busca no TMDB os filmes da exportação que não estão no catálogo e coloca eles lá."""
    from importadores import importar_tmdb as tmdb

    tmdb.chave_api = tmdb.ler_chave_api()
    PASTA_POSTERS.mkdir(parents=True, exist_ok=True)

    simulado = letterboxd.importar(catalogo, caminho_zip, simular=True)
    faltando = simulado["nao_encontrados"]
    if not faltando:
        print("Todos os filmes do Letterboxd já estão no catálogo.\n")
        return 0

    print(f"Buscando no TMDB {len(faltando)} filmes que não estão no catálogo...\n")
    ids_no_catalogo = {filme.get("id") for filme in catalogo if filme.get("tipo") != "serie"}
    adicionados = 0
    for posicao, texto in enumerate(faltando, start=1):
        nome, _, resto = texto.rpartition(" (")
        ano = resto.rstrip(")")
        resultado = tmdb.requisitar("/search/movie", {"query": nome, "year": ano}) if ano.isdigit() else None
        if not resultado or not resultado.get("results"):
            resultado = tmdb.requisitar("/search/movie", {"query": nome})
        if not resultado or not resultado.get("results"):
            print(f"[{posicao:>3}/{len(faltando)}] {texto}: não achei no TMDB")
            continue
        id_filme = resultado["results"][0]["id"]
        if id_filme in ids_no_catalogo:
            print(f"[{posicao:>3}/{len(faltando)}] {texto}: já estava (com outro nome)")
            continue
        filme = tmdb.buscar_e_converter(id_filme)
        if filme is None:
            print(f"[{posicao:>3}/{len(faltando)}] {texto}: faltam dados no TMDB (sinopse, diretor...)")
            continue
        filme["poster"] = tmdb.baixar_poster(filme.pop("caminho_poster_tmdb"), tmdb.criar_nome_poster(filme["nome"], filme["id"]))
        filme["titulo_letterboxd"] = nome   # ajuda a achar de novo na próxima importação
        catalogo.append(filme)
        ids_no_catalogo.add(id_filme)
        adicionados += 1
        print(f"[{posicao:>3}/{len(faltando)}] {texto} -> {filme['nome']} ({filme['ano']}) ✓")
        if adicionados % 25 == 0:
            salvar_catalogo(catalogo)

    salvar_catalogo(catalogo)
    print(f"\n{adicionados} filmes entraram no catálogo. Na próxima vez que abrir, o CineAI calcula os embeddings deles.\n")
    return adicionados


def main():
    argumentos = [argumento for argumento in sys.argv[1:] if not argumento.startswith("--")]
    if not argumentos:
        print(__doc__)
        sys.exit(1)
    caminho_zip = Path(argumentos[0])
    if not caminho_zip.exists():
        sys.exit(f"Não achei o arquivo: {caminho_zip}")

    catalogo = carregar_catalogo()
    if "--adicionar" in sys.argv:
        adicionar_os_que_faltam(catalogo, caminho_zip)

    simular = "--simular" in sys.argv
    resumo = letterboxd.importar(catalogo, caminho_zip, simular=simular)
    print(("SIMULAÇÃO (nada foi gravado):\n" if simular else "Pronto! No seu diário agora:\n") + letterboxd.texto_do_resumo(resumo))
    if resumo["backup"]:
        print(f"\nBackup de antes da importação: {resumo['backup']}")
    if resumo["nao_encontrados"]:
        print("\nFora do catálogo:")
        for texto in resumo["nao_encontrados"][:40]:
            print("   -", texto)
        if len(resumo["nao_encontrados"]) > 40:
            print(f"   ... e mais {len(resumo['nao_encontrados']) - 40}")
        if "--adicionar" not in sys.argv:
            print("\nPara trazer esses também, rode de novo com --adicionar.")


if __name__ == "__main__":
    main()
