"""
diario_pdf.py — exporta o "Meu diário" como um PDF para guardar ou imprimir.

O PDF tem:
    1. a capa vermelha ("este diário pertence a..."),
    2. uma página com os números do diário,
    3. as entradas, separadas por mês, da mais antiga para a mais nova:
       pôster em polaroide, data, estrelas, coração dos favoritos e a sua anotação.

Cada página é desenhada como imagem com o Pillow (o mesmo que desenha as
polaroides da janela) e gravada no PDF uma de cada vez. Assim um diário
com centenas de entradas não enche a memória, e não precisa instalar nada novo.

Não sabe nada de tkinter: a interface só chama exportar_diario_pdf().
"""
import random
import re
import unicodedata
from datetime import date, datetime

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from cineai import usuario
from cineai.caminhos import PASTA_DADOS, PASTA_POSTERS

PASTA_EXPORTADOS = PASTA_DADOS / "exportados"

# ---------------- Folha A4 a 150 dpi ----------------
DPI = 150
LARGURA_PAGINA, ALTURA_PAGINA = 1240, 1754
MARGEM_ESQUERDA = 150        # depois da linha vermelha de caderno
MARGEM_DIREITA = 95
MARGEM_TOPO = 130
MARGEM_BAIXO = 120
X_LINHA_DA_MARGEM = 112
QUALIDADE_JPEG = 88

# ---------------- Cores (as mesmas da janela) ----------------
COR_PAPEL = (251, 244, 227)
COR_CAPA = (163, 34, 28)
COR_VERMELHO = (179, 38, 30)
COR_TEXTO = (42, 28, 23)
COR_TEXTO_SECUNDARIO = (107, 85, 70)
COR_TEXTO_SUAVE = (143, 122, 102)
COR_AZUL_CANETA = (47, 79, 160)
COR_DOURADO = (201, 154, 59)
COR_DOURADO_CLARO = (236, 203, 128)
COR_CREME = (255, 241, 220)
COR_PAUTA = (226, 210, 176)
COR_MARGEM_CADERNO = (214, 120, 110)
COR_BORDA_PAPEL = (214, 191, 149)
COR_ESTRELA_ACESA = (212, 160, 23)
COR_ESTRELA_APAGADA = (205, 187, 152)
COR_POLAROIDE = (255, 253, 247)
COR_SEM_POSTER = (43, 33, 29)
COR_FITA = (228, 207, 156)
CORES_PAPEL_SELO = [(255, 253, 247), (243, 230, 200), (251, 244, 227), (234, 219, 184)]

# ---------------- Fontes (Windows primeiro; as outras são reservas) ----------------
FONTES_TITULO = ["impact.ttf", "Impact.ttf", "/root/.fonts/Anton-Regular.ttf", "DejaVuSans-Bold.ttf"]
FONTES_TEXTO = ["georgia.ttf", "Georgia.ttf", "/root/.fonts/Gelasio[wght].ttf", "DejaVuSerif.ttf"]
FONTES_MANUSCRITAS = ["Inkfree.ttf", "inkfree.ttf", "segoepr.ttf", "/root/.fonts/Caveat[wght].ttf", "DejaVuSans.ttf"]
FONTES_ETIQUETA = ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"]

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
MESES_CURTOS = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

# ---------------- Entradas ----------------
LARGURA_POSTER, ALTURA_POSTER = 150, 222
BORDA_POLAROIDE = 10
BASE_POLAROIDE = 26
ESPACO_ENTRE_ENTRADAS = 34
MAXIMO_LINHAS_ANOTACAO = 14

cache_fontes = {}


# =========================================================
# Ferramentas de desenho
# =========================================================
def fonte(candidatas, tamanho):
    chave = (tuple(candidatas), tamanho)
    if chave not in cache_fontes:
        escolhida = None
        for nome in candidatas:
            try:
                escolhida = ImageFont.truetype(nome, tamanho)
                break
            except OSError:
                continue
        cache_fontes[chave] = escolhida or ImageFont.load_default(size=tamanho)
    return cache_fontes[chave]


def quebrar_linhas(texto, fonte_usada, largura_maxima):
    """Quebra o texto em linhas que cabem na largura (respeita os Enter que você deu)."""
    lapis = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    linhas = []
    for paragrafo in (texto or "").splitlines() or [""]:
        linha_atual = ""
        for palavra in paragrafo.split():
            tentativa = f"{linha_atual} {palavra}".strip()
            if lapis.textlength(tentativa, font=fonte_usada) <= largura_maxima:
                linha_atual = tentativa
            else:
                if linha_atual:
                    linhas.append(linha_atual)
                linha_atual = palavra
        linhas.append(linha_atual)
    return linhas


def altura_da_linha(fonte_usada):
    subida, descida = fonte_usada.getmetrics()
    return subida + descida


def desenhar_estrela(lapis, centro_x, centro_y, raio, cor):
    """Estrela de 5 pontas (sem depender de uma fonte com ★)."""
    import math
    pontos = []
    for indice in range(10):
        angulo = math.pi / 2 + indice * math.pi / 5
        distancia = raio if indice % 2 == 0 else raio * 0.45
        pontos.append((centro_x + distancia * math.cos(angulo), centro_y - distancia * math.sin(angulo)))
    lapis.polygon(pontos, fill=cor)


def desenhar_estrelas(lapis, x, centro_y, nota, raio=13):
    """As 5 estrelas, acesas até a nota. Devolve onde terminou (x)."""
    for posicao in range(1, usuario.NOTA_MAXIMA + 1):
        cor = COR_ESTRELA_ACESA if nota and posicao <= nota else COR_ESTRELA_APAGADA
        desenhar_estrela(lapis, x + raio, centro_y, raio, cor)
        x += 2 * raio + 6
    return x


def desenhar_coracao(lapis, x, y, tamanho, cor):
    raio = tamanho // 4
    lapis.ellipse([x, y, x + 2 * raio, y + 2 * raio], fill=cor)
    lapis.ellipse([x + 2 * raio, y, x + 4 * raio, y + 2 * raio], fill=cor)
    lapis.polygon([(x, y + raio + 1), (x + 4 * raio, y + raio + 1), (x + 2 * raio, y + tamanho)], fill=cor)


def titulo_manuscrito(lapis, texto, centro_x, y, tamanho=58):
    """Título à mão em vermelho, com o marca-texto dourado atrás (igual à janela)."""
    fonte_titulo = fonte(FONTES_MANUSCRITAS, tamanho)
    largura = lapis.textlength(texto, font=fonte_titulo)
    altura = altura_da_linha(fonte_titulo)
    lapis.rectangle(
        [centro_x - largura / 2 - 10, y + altura * 0.55, centro_x + largura / 2 + 10, y + altura * 0.9],
        fill=COR_DOURADO_CLARO
    )
    lapis.text((centro_x, y), texto, font=fonte_titulo, fill=COR_VERMELHO, anchor="ma")
    return y + altura


# =========================================================
# Pôster em polaroide
# =========================================================
def simplificar_nome(nome):
    texto = unicodedata.normalize("NFD", str(nome).lower())
    texto = "".join(caractere for caractere in texto if unicodedata.category(caractere) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", texto).strip("_")


def caminho_do_poster(filme):
    """Mesmo jeito da janela: o campo "poster" do TMDB ou o nome do filme em .png/.jpg."""
    if filme.get("poster"):
        caminho = PASTA_POSTERS / filme["poster"]
        if caminho.exists():
            return caminho
    for extensao in (".png", ".jpg", ".jpeg"):
        caminho = PASTA_POSTERS / (simplificar_nome(filme["nome"]) + extensao)
        if caminho.exists():
            return caminho
    return None


def desenhar_polaroide(filme):
    """Polaroide levemente torta, com fita em cima, já colada no papel da página."""
    sorteio = random.Random(usuario.chave_filme(filme))
    largura = LARGURA_POSTER + 2 * BORDA_POLAROIDE
    altura = ALTURA_POSTER + BORDA_POLAROIDE + BASE_POLAROIDE
    papel = Image.new("RGBA", (largura, altura), COR_POLAROIDE + (255,))
    lapis = ImageDraw.Draw(papel)

    caminho = caminho_do_poster(filme)
    poster = None
    if caminho is not None:
        try:
            with Image.open(caminho) as arquivo:
                poster = arquivo.convert("RGB").resize((LARGURA_POSTER, ALTURA_POSTER), Image.LANCZOS)
        except Exception:
            poster = None
    if poster is not None:
        papel.paste(poster, (BORDA_POLAROIDE, BORDA_POLAROIDE))
    else:
        lapis.rectangle(
            [BORDA_POLAROIDE, BORDA_POLAROIDE, BORDA_POLAROIDE + LARGURA_POSTER, BORDA_POLAROIDE + ALTURA_POSTER],
            fill=COR_SEM_POSTER
        )
        lapis.text(
            (largura / 2, BORDA_POLAROIDE + ALTURA_POSTER / 2), "SEM PÔSTER",
            font=fonte(FONTES_TITULO, 20), fill=COR_DOURADO_CLARO, anchor="mm"
        )

    folga = 12
    com_sombra = Image.new("RGBA", (largura + 2 * folga, altura + 2 * folga), (0, 0, 0, 0))
    com_sombra.alpha_composite(Image.new("RGBA", (largura, altura), (60, 40, 25, 70)), (folga + 3, folga + 5))
    com_sombra = com_sombra.filter(ImageFilter.GaussianBlur(4))
    com_sombra.alpha_composite(papel, (folga, folga))
    girada = com_sombra.rotate(sorteio.uniform(-2.5, 2.5), resample=Image.BICUBIC, expand=True)

    fita = Image.new("RGBA", (int(largura * 0.4), 18), COR_FITA + (215,))
    fita = fita.rotate(sorteio.uniform(-7, 7), resample=Image.BICUBIC, expand=True)
    girada.alpha_composite(fita, (girada.width // 2 - fita.width // 2, folga - fita.height // 2 + 2))

    if usuario.eh_favorito(filme):
        coracao = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        lapis_coracao = ImageDraw.Draw(coracao)
        desenhar_coracao(lapis_coracao, 2, 2, 36, COR_POLAROIDE + (255,))
        desenhar_coracao(lapis_coracao, 6, 6, 28, (190, 36, 30, 255))
        coracao = coracao.rotate(-14, resample=Image.BICUBIC, expand=True)
        girada.alpha_composite(coracao, (girada.width - coracao.width - 2, 4))
    return girada


# =========================================================
# Páginas
# =========================================================
def nova_folha():
    """Página de caderno: papel creme, linha vermelha da margem."""
    pagina = Image.new("RGB", (LARGURA_PAGINA, ALTURA_PAGINA), COR_PAPEL)
    lapis = ImageDraw.Draw(pagina)
    lapis.line([(X_LINHA_DA_MARGEM, 0), (X_LINHA_DA_MARGEM, ALTURA_PAGINA)], fill=COR_MARGEM_CADERNO, width=2)
    return pagina, lapis


def rodape(lapis, numero_pagina, total_paginas=None):
    texto = f"— {numero_pagina} —"
    lapis.text(
        (LARGURA_PAGINA / 2, ALTURA_PAGINA - 70), texto, font=fonte(FONTES_MANUSCRITAS, 28),
        fill=COR_TEXTO_SUAVE, anchor="mm"
    )
    lapis.text(
        (LARGURA_PAGINA - MARGEM_DIREITA, ALTURA_PAGINA - 70), "CineAI · movie journal",
        font=fonte(FONTES_MANUSCRITAS, 22), fill=COR_TEXTO_SUAVE, anchor="rm"
    )


def etiqueta(lapis, texto, x, y, cor_fundo=COR_VERMELHO, cor_texto=COR_CREME, tamanho=20, ancora="la"):
    """Faixinha de texto em caixa alta (MOVIE JOURNAL)."""
    fonte_etiqueta = fonte(FONTES_ETIQUETA, tamanho)
    largura = lapis.textlength(texto, font=fonte_etiqueta) + 28
    altura = altura_da_linha(fonte_etiqueta) + 10
    if ancora == "ma":
        x -= largura / 2
    lapis.rectangle([x, y, x + largura, y + altura], fill=cor_fundo)
    lapis.text((x + 14, y + 5), texto, font=fonte_etiqueta, fill=cor_texto)
    return y + altura


def periodo_do_diario(entradas):
    datas = [entrada["data"] for entrada in entradas if entrada["data"] is not None]
    if not datas:
        return ""
    inicio, fim = min(datas), max(datas)
    texto_inicio = f"{MESES[inicio.month - 1]} de {inicio.year}"
    texto_fim = f"{MESES[fim.month - 1]} de {fim.year}"
    return texto_inicio if texto_inicio == texto_fim else f"{texto_inicio}  —  {texto_fim}"


def desenhar_capa(entradas, titulo_extra, hoje):
    pagina = Image.new("RGB", (LARGURA_PAGINA, ALTURA_PAGINA), COR_CAPA)
    lapis = ImageDraw.Draw(pagina)
    meio = LARGURA_PAGINA / 2

    # lombada com costura
    lapis.rectangle([0, 0, 70, ALTURA_PAGINA], fill=(124, 25, 20))
    for y in range(30, ALTURA_PAGINA, 46):
        lapis.ellipse([31, y, 39, y + 8], fill=(231, 169, 156))

    etiqueta(lapis, "MOVIE JOURNAL", meio, 430, cor_fundo=COR_CREME, cor_texto=COR_VERMELHO, tamanho=26, ancora="ma")
    lapis.text((meio, 520), "MEU DIÁRIO", font=fonte(FONTES_TITULO, 170), fill=COR_CREME, anchor="ma")
    lapis.text((meio, 720), "DE CINEMA", font=fonte(FONTES_TITULO, 96), fill=COR_DOURADO_CLARO, anchor="ma")
    if titulo_extra:
        lapis.text((meio, 850), titulo_extra, font=fonte(FONTES_TITULO, 70), fill=COR_CREME, anchor="ma")

    lapis.text((meio, 1040), "este diário pertence a", font=fonte(FONTES_MANUSCRITAS, 38), fill=COR_CREME, anchor="ma")
    nome = usuario.obter_nome_do_dono() or "______________________"
    lapis.text((meio, 1095), nome, font=fonte(FONTES_MANUSCRITAS, 76), fill=COR_DOURADO_CLARO, anchor="ma")
    lapis.line([(meio - 260, 1200), (meio + 260, 1200)], fill=COR_CREME, width=3)

    periodo = periodo_do_diario(entradas)
    if periodo:
        lapis.text((meio, 1235), periodo, font=fonte(FONTES_MANUSCRITAS, 36), fill=COR_CREME, anchor="ma")

    lapis.text(
        (meio, ALTURA_PAGINA - 120), f"exportado do CineAI em {hoje.strftime('%d/%m/%Y')}",
        font=fonte(FONTES_MANUSCRITAS, 28), fill=COR_DOURADO_CLARO, anchor="ma"
    )
    return pagina


def plural(quantidade, singular, plural_da_palavra):
    return f"{quantidade} {singular if quantidade == 1 else plural_da_palavra}"


def numeros_da_pagina_de_estatisticas(catalogo, ano):
    """
    [(título, valor, legenda)] dos selos e [(rótulo, texto)] das linhas à mão.
    Sem ano: o diário inteiro (os números da Capa). Com ano: a retrospectiva daquele ano.
    """
    if ano is None:
        numeros = usuario.estatisticas_do_diario(catalogo)
        titulos, sessoes = numeros["total"], numeros["sessoes"]
        genero = numeros["genero"]
        revistos = numeros["revistos"]
        mes = numeros["mes"]
        texto_mes = f"{MESES[mes[0].month - 1]} de {mes[0].year} ({plural(mes[1], 'sessão', 'sessões')})" if mes else None
        anotacoes = numeros["anotacoes"]
    else:
        numeros = usuario.retrospectiva_do_ano(catalogo, ano)
        titulos, sessoes = numeros["titulos"], numeros["sessoes"]
        genero = numeros["generos"][0] if numeros["generos"] else None
        revistos = len({usuario.chave_filme(entrada["filme"]) for entrada in numeros["revistos"]})
        mes = numeros["mes"]
        texto_mes = f"{MESES[mes[0] - 1]} ({plural(mes[1], 'sessão', 'sessões')})" if mes else None
        anotacoes = numeros["anotacoes"]

    horas = ("≈" if numeros["horas_estimadas"] else "") + f"{numeros['horas']:,}".replace(",", ".") + "h"
    nota = "–" if numeros["nota_media"] is None else f"{numeros['nota_media']:.1f}".replace(".", ",")
    selos = [
        ("TÍTULOS", str(titulos), "no diário"),
        ("FILMES", str(numeros["filmes"]), "vistos"),
        ("SÉRIES", str(numeros["series"]), "vistas"),
        ("NOTA MÉDIA", nota, "de 5"),
        ("HORAS", horas, "de tela"),
        ("ANOTAÇÕES", str(anotacoes), "escritas"),
    ]

    linhas = []
    if genero:
        linhas.append(("gênero que mais aparece:", f"{genero[0]} ({plural(genero[1], 'título', 'títulos')})"))
    if numeros["pessoa"]:
        linhas.append(("diretor que mais aparece:", f"{numeros['pessoa'][0]} ({numeros['pessoa'][1]})"))
    if texto_mes:
        linhas.append(("mês com mais sessões:", texto_mes))
    if numeros["melhor"]:
        linhas.append(("o mais bem avaliado:", numeros["melhor"]["filme"]["nome"]))
    if revistos:
        linhas.append(("vi de novo:", f"{plural(revistos, 'título', 'títulos')} ({plural(sessoes, 'sessão', 'sessões')} no total)"))
    if ano is None and numeros["favoritos"]:
        linhas.append(("favoritos:", plural(numeros["favoritos"], "título", "títulos")))
    return selos, linhas


def desenhar_selo(titulo, valor, legenda, indice):
    sorteio = random.Random(f"pdf{titulo}{indice}")
    largura, altura = 250, 190
    selo = Image.new("RGBA", (largura, altura), CORES_PAPEL_SELO[indice % len(CORES_PAPEL_SELO)] + (255,))
    lapis = ImageDraw.Draw(selo)
    lapis.rectangle([0, 0, largura - 1, altura - 1], outline=COR_BORDA_PAPEL)
    lapis.text((largura / 2, 38), titulo, font=fonte(FONTES_TITULO, 26), fill=COR_VERMELHO, anchor="mm")
    lapis.text((largura / 2, 98), valor, font=fonte(FONTES_TITULO, 62), fill=COR_TEXTO, anchor="mm")
    lapis.text((largura / 2, 154), legenda, font=fonte(FONTES_MANUSCRITAS, 30), fill=COR_AZUL_CANETA, anchor="mm")

    folga = 14
    com_sombra = Image.new("RGBA", (largura + 2 * folga, altura + 2 * folga), (0, 0, 0, 0))
    com_sombra.alpha_composite(Image.new("RGBA", (largura, altura), (60, 40, 25, 60)), (folga + 3, folga + 5))
    com_sombra = com_sombra.filter(ImageFilter.GaussianBlur(4))
    com_sombra.alpha_composite(selo, (folga, folga))
    girado = com_sombra.rotate(sorteio.uniform(-3.5, 3.5), resample=Image.BICUBIC, expand=True)
    if indice % 2 == 0:
        fita = Image.new("RGBA", (80, 22), COR_FITA + (215,))
        fita = fita.rotate(sorteio.uniform(-10, 10), resample=Image.BICUBIC, expand=True)
        girado.alpha_composite(fita, (girado.width // 2 - fita.width // 2, folga - fita.height // 2 + 2))
    return girado


def desenhar_pagina_de_estatisticas(catalogo, ano, numero_pagina):
    pagina, lapis = nova_folha()
    meio = (MARGEM_ESQUERDA + LARGURA_PAGINA - MARGEM_DIREITA) / 2
    titulo = "o diário em números" if ano is None else f"{ano} em números"
    y = titulo_manuscrito(lapis, titulo, meio, MARGEM_TOPO, 64) + 50

    selos, linhas = numeros_da_pagina_de_estatisticas(catalogo, ano)
    colunas = 3
    for indice, (titulo_selo, valor, legenda) in enumerate(selos):
        selo = desenhar_selo(titulo_selo, valor, legenda, indice)
        coluna, linha = indice % colunas, indice // colunas
        centro_x = meio + (coluna - 1) * 320
        topo = y + linha * 250 + (coluna % 2) * 14
        fundo = Image.new("RGBA", selo.size, COR_PAPEL + (255,))
        fundo.alpha_composite(selo)
        pagina.paste(fundo.convert("RGB"), (int(centro_x - selo.width / 2), int(topo)))
    y += ((len(selos) + colunas - 1) // colunas) * 250 + 50

    fonte_rotulo = fonte(FONTES_MANUSCRITAS, 34)
    fonte_valor = fonte(FONTES_MANUSCRITAS, 38)
    lapis.line([(MARGEM_ESQUERDA + 40, y), (LARGURA_PAGINA - MARGEM_DIREITA - 40, y)], fill=COR_PAUTA, width=2)
    for rotulo, texto in linhas:
        y += 22
        lapis.text((MARGEM_ESQUERDA + 50, y), rotulo, font=fonte_rotulo, fill=COR_VERMELHO)
        x_valor = MARGEM_ESQUERDA + 70 + lapis.textlength(rotulo, font=fonte_rotulo)
        lapis.text((x_valor, y - 3), texto, font=fonte_valor, fill=COR_AZUL_CANETA)
        y += altura_da_linha(fonte_valor) + 10
        lapis.line([(MARGEM_ESQUERDA + 40, y), (LARGURA_PAGINA - MARGEM_DIREITA - 40, y)], fill=COR_PAUTA, width=2)

    rodape(lapis, numero_pagina)
    return pagina


# ---------------- Entradas ----------------
def texto_da_data(data):
    return f"{data.day:02d} {MESES_CURTOS[data.month - 1]} {data.year}" if data else "SEM DATA"


def detalhes_do_filme(filme):
    partes = [str(filme.get("ano") or "")]
    genero = ", ".join(usuario.separar_nomes(filme.get("genero"))[:2])
    if genero:
        partes.append(genero)
    if filme.get("diretor"):
        partes.append(usuario.separar_nomes(filme["diretor"])[0])
    if filme.get("tipo") == "serie":
        partes.insert(0, "série")
    return "  ·  ".join(parte for parte in partes if parte)


def medir_entrada(entrada, largura_texto):
    """Altura que a entrada ocupa (e as linhas já quebradas da anotação e do título)."""
    fonte_titulo = fonte(FONTES_TITULO, 46)
    fonte_anotacao = fonte(FONTES_MANUSCRITAS, 34)
    linhas_titulo = quebrar_linhas(entrada["filme"]["nome"], fonte_titulo, largura_texto)
    linhas_anotacao = []
    if (entrada["anotacao"] or "").strip():
        linhas_anotacao = quebrar_linhas(entrada["anotacao"].strip(), fonte_anotacao, largura_texto)
        if len(linhas_anotacao) > MAXIMO_LINHAS_ANOTACAO:
            linhas_anotacao = linhas_anotacao[:MAXIMO_LINHAS_ANOTACAO]
            linhas_anotacao[-1] = linhas_anotacao[-1].rstrip(" .,;") + "…"
    altura_texto = (
        34                                                   # etiqueta da entrada
        + len(linhas_titulo) * altura_da_linha(fonte_titulo)
        + 40                                                 # ano · gênero · diretor
        + 44                                                 # estrelas
        + len(linhas_anotacao) * (altura_da_linha(fonte_anotacao) - 4)
        + (14 if linhas_anotacao else 0)
    )
    altura_foto = ALTURA_POSTER + BORDA_POLAROIDE + BASE_POLAROIDE + 30
    return max(altura_texto, altura_foto), linhas_titulo, linhas_anotacao


def desenhar_entrada(pagina, lapis, entrada, y, linhas_titulo, linhas_anotacao):
    filme = entrada["filme"]
    polaroide = desenhar_polaroide(filme)
    fundo = Image.new("RGBA", polaroide.size, COR_PAPEL + (255,))
    fundo.alpha_composite(polaroide)
    pagina.paste(fundo.convert("RGB"), (MARGEM_ESQUERDA - 4, int(y)))

    x = MARGEM_ESQUERDA + LARGURA_POSTER + 2 * BORDA_POLAROIDE + 50
    texto_etiqueta = f"ENTRADA #{entrada['numero']:03d}  ·  {texto_da_data(entrada['data'])}"
    if entrada["vez"] > 1:
        texto_etiqueta += f"  ·  {entrada['vez']}ª VEZ"
    lapis.text((x, y + 8), texto_etiqueta, font=fonte(FONTES_ETIQUETA, 20), fill=COR_VERMELHO)
    y += 34

    fonte_titulo = fonte(FONTES_TITULO, 46)
    for linha in linhas_titulo:
        lapis.text((x, y), linha, font=fonte_titulo, fill=COR_TEXTO)
        y += altura_da_linha(fonte_titulo)

    lapis.text((x, y + 2), detalhes_do_filme(filme), font=fonte(FONTES_TEXTO, 24), fill=COR_TEXTO_SECUNDARIO)
    y += 40

    fim_estrelas = desenhar_estrelas(lapis, x, y + 20, entrada["nota"])
    if entrada["nota"] is None:
        lapis.text((fim_estrelas + 8, y + 20), "sem nota", font=fonte(FONTES_MANUSCRITAS, 26),
                   fill=COR_TEXTO_SUAVE, anchor="lm")
    elif usuario.eh_favorito(filme):
        desenhar_coracao(lapis, fim_estrelas + 10, y + 8, 26, (190, 36, 30))
    y += 44

    if linhas_anotacao:
        y += 14
        fonte_anotacao = fonte(FONTES_MANUSCRITAS, 34)
        for linha in linhas_anotacao:
            lapis.text((x, y), linha, font=fonte_anotacao, fill=COR_AZUL_CANETA)
            y += altura_da_linha(fonte_anotacao) - 4


def cabecalho_do_mes(lapis, data, quantidade, y):
    """'setembro de 2026' à mão, com o marca-texto, e quantas sessões teve."""
    texto = f"{MESES[data.month - 1]} de {data.year}" if data else "sem data"
    fonte_mes = fonte(FONTES_MANUSCRITAS, 54)
    largura = lapis.textlength(texto, font=fonte_mes)
    altura = altura_da_linha(fonte_mes)
    lapis.rectangle(
        [MARGEM_ESQUERDA - 8, y + altura * 0.55, MARGEM_ESQUERDA + largura + 8, y + altura * 0.9],
        fill=COR_DOURADO_CLARO
    )
    lapis.text((MARGEM_ESQUERDA, y), texto, font=fonte_mes, fill=COR_VERMELHO)
    lapis.text(
        (MARGEM_ESQUERDA + largura + 26, y + altura * 0.62), plural(quantidade, "sessão", "sessões"),
        font=fonte(FONTES_MANUSCRITAS, 28), fill=COR_TEXTO_SUAVE, anchor="lm"
    )
    return y + altura + 26


ALTURA_CABECALHO_MES = 110


def paginas_das_entradas(entradas, primeiro_numero):
    """Gera as páginas do diário, uma de cada vez (gerador: não guarda todas na memória)."""
    largura_texto = LARGURA_PAGINA - MARGEM_DIREITA - (MARGEM_ESQUERDA + LARGURA_POSTER + 2 * BORDA_POLAROIDE + 50)
    limite = ALTURA_PAGINA - MARGEM_BAIXO

    quantidade_por_mes = {}
    for entrada in entradas:
        mes = entrada["data"].replace(day=1) if entrada["data"] else None
        quantidade_por_mes[mes] = quantidade_por_mes.get(mes, 0) + 1

    numero_pagina = primeiro_numero
    pagina, lapis = nova_folha()
    y = MARGEM_TOPO
    mes_atual = "nenhum"

    for entrada in entradas:
        altura, linhas_titulo, linhas_anotacao = medir_entrada(entrada, largura_texto)
        mes = entrada["data"].replace(day=1) if entrada["data"] else None
        precisa_cabecalho = mes != mes_atual
        altura_total = altura + (ALTURA_CABECALHO_MES if precisa_cabecalho else 0)

        if y + altura_total > limite and y > MARGEM_TOPO:
            rodape(lapis, numero_pagina)
            yield pagina
            numero_pagina += 1
            pagina, lapis = nova_folha()
            y = MARGEM_TOPO

        if precisa_cabecalho:
            if y > MARGEM_TOPO:
                y += 20
            y = cabecalho_do_mes(lapis, mes, quantidade_por_mes[mes], y)
            mes_atual = mes

        desenhar_entrada(pagina, lapis, entrada, y, linhas_titulo, linhas_anotacao)
        y += altura + ESPACO_ENTRE_ENTRADAS
        lapis.line(
            [(MARGEM_ESQUERDA, y - ESPACO_ENTRE_ENTRADAS / 2),
             (LARGURA_PAGINA - MARGEM_DIREITA, y - ESPACO_ENTRE_ENTRADAS / 2)],
            fill=COR_PAUTA, width=2
        )

    rodape(lapis, numero_pagina)
    yield pagina


# =========================================================
# Exportar
# =========================================================
def entradas_para_exportar(catalogo, ano=None):
    """Entradas da mais antiga para a mais nova (só as do ano, se ele for informado)."""
    entradas = usuario.entradas_do_diario(catalogo, usuario.ORDEM_DIARIO_ANTIGOS)
    if ano is not None:
        entradas = [entrada for entrada in entradas if entrada["data"] is not None and entrada["data"].year == ano]
    return entradas


def caminho_padrao(ano=None, agora=None):
    agora = agora or datetime.now()
    sufixo = f"_{ano}" if ano is not None else ""
    return PASTA_EXPORTADOS / f"diario{sufixo}_{agora.strftime('%Y-%m-%d_%H%M%S')}.pdf"


def exportar_diario_pdf(catalogo, ano=None, caminho=None, ao_avancar=None):
    """
    Grava o PDF e devolve o caminho. ano=None exporta o diário inteiro.
    ao_avancar(paginas_prontas) é chamado a cada página (para a interface mostrar o progresso).
    Levanta ValueError se não houver nenhuma entrada para exportar.
    """
    entradas = entradas_para_exportar(catalogo, ano)
    if not entradas:
        raise ValueError("Não há nenhuma entrada no diário" + (f" em {ano}." if ano else "."))

    caminho = caminho or caminho_padrao(ano)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho_temporario = caminho.with_suffix(".tmp")

    def todas_as_paginas():
        yield desenhar_capa(entradas, str(ano) if ano else "", date.today())
        yield desenhar_pagina_de_estatisticas(catalogo, ano, 2)
        yield from paginas_das_entradas(entradas, 3)

    quantidade = 0
    for pagina in todas_as_paginas():
        pagina.save(
            caminho_temporario, "PDF", resolution=DPI, quality=QUALIDADE_JPEG,
            append=quantidade > 0, title="Meu diário de cinema", author=usuario.obter_nome_do_dono() or "CineAI"
        )
        quantidade += 1
        if ao_avancar is not None:
            ao_avancar(quantidade)

    caminho_temporario.replace(caminho)
    return caminho