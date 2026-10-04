"""
construir_exe.py — gera o CineAI.exe.

Como usar (no terminal do VS Code, na pasta do projeto):
    python construir_exe.py

O que ele faz:
    1. instala/atualiza o PyInstaller
    2. roda os testes (se algum falhar, para aqui e mostra o erro)
    3. escreve a receita CineAI.spec e gera dist/CineAI/CineAI.exe

Demora alguns minutos (o torch é grande). Rode de novo sempre que mudar
o código e quiser o .exe atualizado.
"""
import os
import subprocess
import sys
from pathlib import Path

PASTA_PROJETO = Path(__file__).resolve().parent
CAMINHO_SPEC = PASTA_PROJETO / "CineAI.spec"
CAMINHO_LOG_TESTES = PASTA_PROJETO / "dados" / "testes_antes_do_exe.log"

# A receita do PyInstaller fica aqui dentro (e é escrita no CineAI.spec a cada vez),
# assim não existe o risco de o CineAI.spec estar com o conteúdo errado.
RECEITA_SPEC = r'''# -*- mode: python ; coding: utf-8 -*-
"""
CineAI.spec — receita do PyInstaller para gerar o CineAI.exe.

Não rode este arquivo direto: use o construir_exe.bat (na mesma pasta).
O resultado fica em dist/CineAI/  (CineAI.exe + a pasta _internal com as bibliotecas).

Por que "uma pasta" e não um .exe único?
    O torch e o sentence-transformers têm centenas de MB. Num .exe único, o
    Windows teria que descompactar tudo numa pasta temporária a CADA vez que
    você abrisse o CineAI (demora quase um minuto). Em pasta, abre direto.

O que NÃO vai dentro do .exe (fica na pasta do projeto, como sempre):
    dados/  -> catálogo, pôsteres, cache de embeddings e o SEU diário
    .env    -> suas chaves (só os importadores usam)
O CineAI.exe procura a pasta dados/ subindo a partir da pasta dele
(veja cineai/caminhos.py), então usa o mesmo diário do "python main.py".
"""
from PyInstaller.utils.hooks import collect_all, collect_data_files, copy_metadata

datas = [("cineai.ico", ".")]
binaries = []
hiddenimports = []

# customtkinter: temas e fontes (.json / .otf) que ele lê em tempo de execução
datas += collect_data_files("customtkinter")

# sentence-transformers e transformers carregam módulos "pelo nome" na hora
# (ex.: o modelo BERT do MiniLM), então levamos os pacotes inteiros.
for pacote in ("sentence_transformers", "transformers", "tokenizers"):
    try:
        dados_pacote, binarios_pacote, modulos_pacote = collect_all(pacote)
    except Exception:
        continue
    datas += dados_pacote
    binaries += binarios_pacote
    hiddenimports += modulos_pacote

# O transformers confere as versões das bibliotecas pelos "metadados" delas.
for pacote in (
    "torch", "tqdm", "regex", "requests", "packaging", "filelock", "numpy",
    "tokenizers", "huggingface-hub", "safetensors", "pyyaml", "transformers",
    "sentence-transformers", "scikit-learn", "scipy", "Pillow",
):
    try:
        datas += copy_metadata(pacote)
    except Exception:
        pass   # pacote que não está instalado nesta máquina: não faz falta

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ["ollama", "PIL._tkinter_finder"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Coisas que o PyInstaller acharia "por tabela" e que o CineAI não usa:
    excludes=["tensorflow", "keras", "flax", "jax", "matplotlib", "IPython", "notebook", "pytest"],
    noarchive=False,
    # Leva também o código-fonte (.py) desses pacotes: algumas partes do
    # torch/transformers leem o próprio código ao carregar e quebram sem ele.
    module_collection_mode={"transformers": "pyz+py", "sentence_transformers": "pyz+py"},
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CineAI",
    icon="cineai.ico",
    console=False,          # sem a janela preta do terminal
    debug=False,
    strip=False,
    upx=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="CineAI",
)
'''


def rodar(comando, **opcoes):
    print("  >", " ".join(str(parte) for parte in comando), flush=True)
    return subprocess.run(comando, cwd=PASTA_PROJETO, **opcoes).returncode


def main():
    ambiente = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")

    print("\n=== 1/3  Instalando o PyInstaller ===", flush=True)
    if rodar([sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"], env=ambiente) != 0:
        sys.exit("Não consegui instalar o PyInstaller.")

    print("\n=== 2/3  Rodando os testes ===", flush=True)
    CAMINHO_LOG_TESTES.parent.mkdir(parents=True, exist_ok=True)
    with open(CAMINHO_LOG_TESTES, "w", encoding="utf-8") as log:
        codigo = rodar([sys.executable, "testes/testes.py"], env=ambiente, stdout=log, stderr=subprocess.STDOUT)
    if codigo != 0:
        linhas = CAMINHO_LOG_TESTES.read_text(encoding="utf-8").splitlines()
        print("\n".join(linhas[-25:]))
        sys.exit(f"\nOs testes falharam (log completo em {CAMINHO_LOG_TESTES}).")
    print("Testes OK.")

    print("\n=== 3/3  Gerando o CineAI.exe (pode levar uns minutos) ===", flush=True)
    if not (PASTA_PROJETO / "cineai.ico").exists():
        sys.exit("Faltou o cineai.ico na pasta do projeto (o ícone do .exe).")
    CAMINHO_SPEC.write_text(RECEITA_SPEC, encoding="utf-8")
    if rodar([sys.executable, "-m", "PyInstaller", str(CAMINHO_SPEC), "--noconfirm", "--clean"], env=ambiente) != 0:
        sys.exit("\nO PyInstaller deu erro. Copie as últimas linhas acima e mande para o Claude.")

    pasta_exe = PASTA_PROJETO / "dist" / "CineAI"
    print(f"\nPronto! O executável está em: {pasta_exe / 'CineAI.exe'}")
    if sys.platform.startswith("win"):
        os.startfile(pasta_exe)


if __name__ == "__main__":
    main()