"""
tela/ponte.py — a "ponte" entre as partes da janela.

Cada parte da janela (tela/*.py) usa tudo o que as partes ANTERIORES criaram.
Às vezes uma parte precisa chamar algo de uma parte que vem DEPOIS: por exemplo,
o card de filme (recortes.py) abre a página do filme (janela_detalhes.py), e a
janela de detalhes desenha cards. Um precisa do outro.

Para isso existe a ponte: a parte de depois se registra
    ponte.registrar(abrir_detalhes=abrir_detalhes)
e a parte de antes chama
    ponte.abrir_detalhes(filme)

Se a parte de antes pedir algo que ainda não foi registrado (ex.: ao montar um
botão com command=ponte.processar enquanto a janela é criada), recebe uma função
que só procura o registro na hora do clique.
"""


class Ponte:
    def __init__(self):
        self._registrados = {}

    def registrar(self, **itens):
        self._registrados.update(itens)

    def __getattr__(self, nome):
        if nome.startswith("_"):
            raise AttributeError(nome)
        if nome in self._registrados:
            return self._registrados[nome]

        def chamar_quando_existir(*argumentos, **opcoes):
            return self._registrados[nome](*argumentos, **opcoes)

        chamar_quando_existir.__name__ = nome
        return chamar_quando_existir


ponte = Ponte()
