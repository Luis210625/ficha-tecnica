"""
cli.py
=======
Interface de linha de comando (CLI) do Sistema de Fichas Técnicas.

Todo o fluxo do usuário passa por aqui: menus, leitura de dados com
validação, exibição de tabelas (tabulate) e chamadas ao GerenciadorFichas.
"""

from pathlib import Path
from datetime import datetime

from tabulate import tabulate

from gerenciador import GerenciadorFichas
from models import Ingrediente, CATEGORIAS_PADRAO, UNIDADES_VALIDAS, ALERGENICOS_COMUNS
from exportador_pdf import exportar_ficha_pdf
from exportador_excel import exportar_todas_excel

PASTA_EXPORTACAO = Path("exportados")


# ====================================================================== #
# Funções auxiliares de entrada de dados (com validação e tratamento
# de erros, para o usuário nunca "quebrar" o programa digitando algo
# inesperado).
# ====================================================================== #

def ler_texto(mensagem: str, obrigatorio: bool = True, padrao: str = "") -> str:
    while True:
        entrada = input(mensagem).strip()
        if not entrada:
            if padrao:
                return padrao
            if not obrigatorio:
                return ""
            print("⚠️  Este campo é obrigatório. Tente novamente.")
            continue
        return entrada


def ler_float(mensagem: str, minimo: float = None, padrao: float = None) -> float:
    while True:
        entrada = input(mensagem).strip().replace(",", ".")
        if not entrada and padrao is not None:
            return padrao
        try:
            valor = float(entrada)
        except ValueError:
            print("⚠️  Digite um número válido (ex.: 12.5).")
            continue
        if minimo is not None and valor < minimo:
            print(f"⚠️  O valor deve ser maior ou igual a {minimo}.")
            continue
        return valor


def ler_int(mensagem: str, minimo: int = None, padrao: int = None) -> int:
    while True:
        entrada = input(mensagem).strip()
        if not entrada and padrao is not None:
            return padrao
        try:
            valor = int(entrada)
        except ValueError:
            print("⚠️  Digite um número inteiro válido.")
            continue
        if minimo is not None and valor < minimo:
            print(f"⚠️  O valor deve ser maior ou igual a {minimo}.")
            continue
        return valor


def ler_opcao_menu(mensagem: str, opcoes_validas) -> str:
    while True:
        escolha = input(mensagem).strip()
        if escolha in opcoes_validas:
            return escolha
        print("⚠️  Opção inválida. Tente novamente.")


def ler_categoria() -> str:
    print("\nCategorias sugeridas:")
    for i, cat in enumerate(CATEGORIAS_PADRAO, start=1):
        print(f"  {i}. {cat}")
    escolha = input("Escolha o número da categoria ou digite uma categoria personalizada: ").strip()
    if escolha.isdigit() and 1 <= int(escolha) <= len(CATEGORIAS_PADRAO):
        return CATEGORIAS_PADRAO[int(escolha) - 1]
    if escolha:
        return escolha
    print("⚠️  Categoria não pode ser vazia.")
    return ler_categoria()


def ler_unidade() -> str:
    while True:
        entrada = input(f"Unidade ({'/'.join(UNIDADES_VALIDAS)}): ").strip().lower()
        if entrada in UNIDADES_VALIDAS:
            return entrada
        print(f"⚠️  Unidade inválida. Use uma de: {', '.join(UNIDADES_VALIDAS)}.")


def ler_confirmacao(mensagem: str) -> bool:
    resposta = input(f"{mensagem} (s/n): ").strip().lower()
    return resposta in ("s", "sim", "y", "yes")


def pausar():
    input("\nPressione ENTER para continuar...")


def cabecalho(titulo: str):
    print("\n" + "=" * 60)
    print(titulo.center(60))
    print("=" * 60)


# ====================================================================== #
# Coleta de listas (ingredientes / modo de preparo)
# ====================================================================== #

def coletar_ingredientes() -> list:
    """Coleta a lista de ingredientes da receita, um a um, até o usuário encerrar."""
    ingredientes = []
    print("\n--- Ingredientes da receita ---")
    print("(digite o nome do ingrediente em branco para encerrar a lista)")
    while True:
        nome = input(f"\nIngrediente #{len(ingredientes) + 1} - nome: ").strip()
        if not nome:
            if not ingredientes:
                print("⚠️  Cadastre pelo menos um ingrediente.")
                continue
            break
        quantidade = ler_float("  Quantidade usada na receita: ", minimo=0.001)
        unidade = ler_unidade()
        custo_unitario = ler_float(f"  Custo por {unidade} (R$): ", minimo=0)
        try:
            ingredientes.append(Ingrediente(nome, quantidade, unidade, custo_unitario))
        except ValueError as erro:
            print(f"⚠️  {erro}")
    return ingredientes


def coletar_modo_preparo() -> list:
    """Coleta o passo a passo do modo de preparo."""
    passos = []
    print("\n--- Modo de preparo ---")
    print("(digite cada passo e ENTER; deixe em branco para encerrar)")
    while True:
        passo = input(f"Passo {len(passos) + 1}: ").strip()
        if not passo:
            if not passos:
                print("⚠️  Cadastre pelo menos um passo.")
                continue
            break
        passos.append(passo)
    return passos


def coletar_alergenicos() -> list:
    print("\n--- Alergênicos ---")
    print("Comuns: " + ", ".join(f"{i+1}={a}" for i, a in enumerate(ALERGENICOS_COMUNS)))
    entrada = input(
        "Digite os números separados por vírgula e/ou outros alergênicos por extenso "
        "(ou deixe em branco se não houver): "
    ).strip()
    if not entrada:
        return []
    selecionados = []
    for item in entrada.split(","):
        item = item.strip()
        if not item:
            continue
        if item.isdigit() and 1 <= int(item) <= len(ALERGENICOS_COMUNS):
            selecionados.append(ALERGENICOS_COMUNS[int(item) - 1])
        else:
            selecionados.append(item)
    return selecionados


# ====================================================================== #
# Exibição de dados
# ====================================================================== #

def exibir_tabela_fichas(fichas):
    if not fichas:
        print("\nNenhuma ficha técnica encontrada.")
        return
    linhas = []
    for f in fichas:
        linhas.append([
            f.id, f.nome, f.categoria,
            f"R$ {f.custo_total_producao:.2f}",
            f"R$ {f.preco_venda_final:.2f}",
            f"{f.margem_lucro_percentual:.1f}%",
            f"{f.food_cost_percentual:.1f}%",
        ])
    print(tabulate(
        linhas,
        headers=["ID", "Nome", "Categoria", "Custo", "Preço venda", "Margem", "Food Cost"],
        tablefmt="fancy_grid",
    ))


def exibir_detalhes_ficha(f):
    cabecalho(f"FICHA TÉCNICA #{f.id} — {f.nome}")
    print(f"Categoria: {f.categoria}")
    print(f"Porção/Rendimento: {f.porcao_rendimento}")
    print(f"Tempo de preparo: {f.tempo_preparo_min} min")
    print(f"Alergênicos: {', '.join(f.alergenicos) if f.alergenicos else 'Nenhum informado'}")
    print(f"Criada em: {f.data_criacao}  |  Atualizada em: {f.data_atualizacao}")

    print("\nIngredientes:")
    linhas_ing = [
        [i.nome, f"{i.quantidade:g} {i.unidade}", f"R$ {i.custo_unitario:.4f}", f"R$ {i.custo_total:.2f}"]
        for i in f.ingredientes
    ]
    print(tabulate(linhas_ing, headers=["Ingrediente", "Quantidade", "Custo unit.", "Custo total"], tablefmt="grid"))

    print("\nModo de preparo:")
    for i, passo in enumerate(f.modo_preparo, start=1):
        print(f"  {i}. {passo}")

    print("\nCustos e precificação:")
    linhas_custo = [
        ["Custo dos ingredientes", f"R$ {f.custo_ingredientes:.2f}"],
        ["Custo de mão de obra", f"R$ {f.custo_mao_de_obra:.2f}"],
        ["Custo total de produção", f"R$ {f.custo_total_producao:.2f}"],
        ["Preço de venda sugerido", f"R$ {f.preco_venda_sugerido:.2f}"],
        ["Preço de venda praticado", f"R$ {f.preco_venda_final:.2f}"],
        ["Margem de lucro", f"{f.margem_lucro_percentual:.1f}% (R$ {f.margem_lucro_valor:.2f})"],
        ["Food Cost %", f"{f.food_cost_percentual:.1f}%"],
    ]
    print(tabulate(linhas_custo, tablefmt="grid"))

    print(f"\nObservações: {f.observacoes if f.observacoes else '(nenhuma)'}")


# ====================================================================== #
# Fluxos principais do menu
# ====================================================================== #

def fluxo_adicionar_ficha(gerenciador: GerenciadorFichas):
    cabecalho("ADICIONAR NOVA FICHA TÉCNICA")
    nome = ler_texto("Nome do prato: ")
    categoria = ler_categoria()
    porcao = ler_texto("Porção/Rendimento (ex.: 1 pizza de 35cm / 8 fatias): ")
    ingredientes = coletar_ingredientes()
    modo_preparo = coletar_modo_preparo()
    tempo_preparo = ler_int("Tempo de preparo (minutos): ", minimo=0)
    alergenicos = coletar_alergenicos()
    observacoes = ler_texto(
        "Observações (validade após preparo, temperatura de armazenamento etc.) [opcional]: ",
        obrigatorio=False,
    )
    margem = ler_float(
        f"Margem de lucro desejada em % [padrão {gerenciador.config['margem_padrao']}]: ",
        minimo=0, padrao=gerenciador.config["margem_padrao"],
    )
    custo_hora = ler_float(
        f"Custo de mão de obra por hora em R$ [padrão {gerenciador.config['custo_mao_de_obra_hora_padrao']}]: ",
        minimo=0, padrao=gerenciador.config["custo_mao_de_obra_hora_padrao"],
    )
    definir_preco_manual = ler_confirmacao("Deseja definir um preço de venda fixo (em vez do sugerido)?")
    preco_manual = ler_float("Preço de venda (R$): ", minimo=0) if definir_preco_manual else None

    try:
        ficha = gerenciador.adicionar_ficha(
            nome=nome, categoria=categoria, porcao_rendimento=porcao,
            ingredientes=ingredientes, modo_preparo=modo_preparo,
            tempo_preparo_min=tempo_preparo, alergenicos=alergenicos,
            observacoes=observacoes, margem_lucro_desejada=margem,
            custo_mao_de_obra_hora=custo_hora, preco_venda_manual=preco_manual,
        )
    except ValueError as erro:
        print(f"\n❌ Erro ao criar ficha: {erro}")
        return

    print(f"\n✅ Ficha técnica '{ficha.nome}' criada com sucesso (ID #{ficha.id})!")
    exibir_detalhes_ficha(ficha)


def fluxo_listar_fichas(gerenciador: GerenciadorFichas):
    cabecalho("FICHAS TÉCNICAS CADASTRADAS")
    filtrar = ler_confirmacao("Deseja filtrar por categoria?")
    categoria = ler_categoria() if filtrar else None
    exibir_tabela_fichas(gerenciador.listar_fichas(categoria))


def _selecionar_ficha(gerenciador: GerenciadorFichas):
    if not gerenciador.fichas:
        print("\nNenhuma ficha técnica cadastrada ainda.")
        return None
    exibir_tabela_fichas(gerenciador.fichas)
    id_ficha = ler_int("\nDigite o ID da ficha desejada: ", minimo=1)
    ficha = gerenciador.obter_ficha(id_ficha)
    if ficha is None:
        print("❌ Ficha não encontrada.")
    return ficha


def fluxo_ver_detalhes(gerenciador: GerenciadorFichas):
    cabecalho("VER DETALHES DE UMA FICHA")
    ficha = _selecionar_ficha(gerenciador)
    if ficha:
        exibir_detalhes_ficha(ficha)


def fluxo_editar_ficha(gerenciador: GerenciadorFichas):
    cabecalho("EDITAR FICHA TÉCNICA")
    ficha = _selecionar_ficha(gerenciador)
    if not ficha:
        return

    campos = {
        "1": ("nome", "Novo nome"),
        "2": ("categoria", None),
        "3": ("porcao_rendimento", "Nova porção/rendimento"),
        "4": ("ingredientes", None),
        "5": ("modo_preparo", None),
        "6": ("tempo_preparo_min", "Novo tempo de preparo (min)"),
        "7": ("alergenicos", None),
        "8": ("observacoes", "Novas observações"),
        "9": ("margem_lucro_desejada", "Nova margem de lucro desejada (%)"),
        "10": ("custo_mao_de_obra_hora", "Novo custo de mão de obra por hora (R$)"),
        "11": ("preco_venda_manual", "Novo preço de venda fixo (R$) — 0 para remover"),
    }

    print("\nO que deseja editar?")
    print("  1. Nome            5. Modo de preparo     9.  Margem de lucro desejada")
    print("  2. Categoria       6. Tempo de preparo     10. Custo de mão de obra/hora")
    print("  3. Porção          7. Alergênicos          11. Preço de venda fixo")
    print("  4. Ingredientes    8. Observações")
    escolha = ler_opcao_menu("Opção: ", campos.keys())
    campo, prompt = campos[escolha]

    try:
        if campo == "categoria":
            novo_valor = ler_categoria()
        elif campo == "ingredientes":
            novo_valor = coletar_ingredientes()
        elif campo == "modo_preparo":
            novo_valor = coletar_modo_preparo()
        elif campo == "alergenicos":
            novo_valor = coletar_alergenicos()
        elif campo == "tempo_preparo_min":
            novo_valor = ler_int(f"{prompt}: ", minimo=0)
        elif campo == "margem_lucro_desejada":
            novo_valor = ler_float(f"{prompt}: ", minimo=0)
        elif campo == "custo_mao_de_obra_hora":
            novo_valor = ler_float(f"{prompt}: ", minimo=0)
        elif campo == "preco_venda_manual":
            valor = ler_float(f"{prompt}: ", minimo=0)
            novo_valor = None if valor == 0 else valor
        elif campo == "observacoes":
            novo_valor = ler_texto(f"{prompt}: ", obrigatorio=False)
        else:
            novo_valor = ler_texto(f"{prompt}: ")

        gerenciador.editar_ficha(ficha.id, **{campo: novo_valor})
        print("\n✅ Ficha atualizada com sucesso!")
        exibir_detalhes_ficha(gerenciador.obter_ficha(ficha.id))
    except ValueError as erro:
        print(f"\n❌ Erro ao editar: {erro}")


def fluxo_excluir_ficha(gerenciador: GerenciadorFichas):
    cabecalho("EXCLUIR FICHA TÉCNICA")
    ficha = _selecionar_ficha(gerenciador)
    if not ficha:
        return
    if ler_confirmacao(f"Tem certeza que deseja excluir '{ficha.nome}'? Esta ação não pode ser desfeita."):
        gerenciador.excluir_ficha(ficha.id)
        print("✅ Ficha excluída com sucesso.")
    else:
        print("Operação cancelada.")


def fluxo_buscar(gerenciador: GerenciadorFichas):
    cabecalho("BUSCAR FICHAS TÉCNICAS")
    termo = ler_texto("Digite o nome ou categoria para buscar: ")
    resultados = gerenciador.buscar(termo)
    print(f"\n{len(resultados)} resultado(s) encontrado(s):")
    exibir_tabela_fichas(resultados)


def fluxo_exportar_pdf(gerenciador: GerenciadorFichas):
    cabecalho("EXPORTAR FICHA TÉCNICA PARA PDF")
    ficha = _selecionar_ficha(gerenciador)
    if not ficha:
        return
    PASTA_EXPORTACAO.mkdir(exist_ok=True)
    nome_arquivo = f"{ficha.id:03d}_{ficha.nome}".replace(" ", "_").replace("/", "-")
    caminho = PASTA_EXPORTACAO / f"{nome_arquivo}.pdf"
    try:
        caminho_final = exportar_ficha_pdf(ficha, str(caminho))
        print(f"\n✅ PDF gerado com sucesso em: {caminho_final}")
    except Exception as erro:
        print(f"\n❌ Erro ao gerar PDF: {erro}")


def fluxo_exportar_excel(gerenciador: GerenciadorFichas):
    cabecalho("EXPORTAR TODAS AS FICHAS PARA EXCEL")
    if not gerenciador.fichas:
        print("Nenhuma ficha técnica cadastrada para exportar.")
        return
    PASTA_EXPORTACAO.mkdir(exist_ok=True)
    data_str = datetime.now().strftime("%Y-%m-%d_%H%M")
    caminho = PASTA_EXPORTACAO / f"fichas_tecnicas_{data_str}.xlsx"
    try:
        relatorio = gerenciador.relatorio_custo_medio_por_categoria()
        caminho_final = exportar_todas_excel(gerenciador.fichas, relatorio, str(caminho))
        print(f"\n✅ Excel gerado com sucesso em: {caminho_final}")
    except Exception as erro:
        print(f"\n❌ Erro ao gerar Excel: {erro}")


def fluxo_relatorio_categoria(gerenciador: GerenciadorFichas):
    cabecalho("RELATÓRIO DE CUSTO MÉDIO POR CATEGORIA")
    relatorio = gerenciador.relatorio_custo_medio_por_categoria()
    if not relatorio:
        print("Nenhuma ficha técnica cadastrada ainda.")
        return
    linhas = [
        [cat, d["quantidade_fichas"], f"R$ {d['custo_medio']:.2f}", f"R$ {d['preco_medio']:.2f}",
         f"{d['margem_media']:.1f}%", f"{d['food_cost_medio']:.1f}%"]
        for cat, d in relatorio.items()
    ]
    print(tabulate(
        linhas,
        headers=["Categoria", "Qtd. Fichas", "Custo Médio", "Preço Médio", "Margem Média", "Food Cost Médio"],
        tablefmt="fancy_grid",
    ))


# ---------------------- Submenu de estoque ---------------------- #

def fluxo_estoque(gerenciador: GerenciadorFichas):
    while True:
        cabecalho("CONTROLE DE ESTOQUE")
        print("  1. Ver estoque atual")
        print("  2. Adicionar/repor estoque de um ingrediente")
        print("  3. Verificar quantas porções dá para produzir (ficha)")
        print("  4. Dar baixa no estoque (registrar produção)")
        print("  0. Voltar ao menu principal")
        opcao = ler_opcao_menu("Opção: ", {"0", "1", "2", "3", "4"})

        if opcao == "0":
            return
        elif opcao == "1":
            itens = gerenciador.listar_estoque()
            if not itens:
                print("\nNenhum item em estoque ainda.")
            else:
                linhas = [[i["nome"], f"{i['quantidade']:g}", i["unidade"]] for i in itens]
                print(tabulate(linhas, headers=["Ingrediente", "Quantidade", "Unidade"], tablefmt="fancy_grid"))
        elif opcao == "2":
            nome = ler_texto("Nome do ingrediente: ")
            quantidade = ler_float("Quantidade a adicionar: ", minimo=0.001)
            unidade = ler_unidade()
            try:
                gerenciador.adicionar_estoque(nome, quantidade, unidade)
                print("✅ Estoque atualizado com sucesso!")
            except ValueError as erro:
                print(f"❌ {erro}")
        elif opcao == "3":
            ficha = _selecionar_ficha(gerenciador)
            if ficha:
                resultado = gerenciador.verificar_estoque_ficha(ficha.id)
                print(f"\nCom o estoque atual, é possível produzir "
                      f"{resultado['porcoes_possiveis']} porção(ões) de '{resultado['ficha']}'.")
                if resultado["ingredientes_faltando"]:
                    print("\nIngredientes insuficientes para mais porções:")
                    linhas = [[i["ingrediente"], f"{i['necessario']:g}", f"{i['disponivel']:g}", i["unidade"]]
                              for i in resultado["ingredientes_faltando"]]
                    print(tabulate(linhas, headers=["Ingrediente", "Necessário", "Disponível", "Unidade"], tablefmt="grid"))
        elif opcao == "4":
            ficha = _selecionar_ficha(gerenciador)
            if ficha:
                porcoes = ler_int("Quantas porções serão produzidas? ", minimo=1, padrao=1)
                resultado = gerenciador.dar_baixa_estoque(ficha.id, porcoes)
                if resultado["sucesso"]:
                    print(f"✅ Baixa de estoque registrada para {porcoes} porção(ões) de '{ficha.nome}'.")
                else:
                    print("\n❌ Estoque insuficiente para essa produção. Itens faltantes:")
                    linhas = [[i["ingrediente"], f"{i['necessario']:g}", f"{i['disponivel']:g}", i["unidade"]]
                              for i in resultado["ingredientes_insuficientes"]]
                    print(tabulate(linhas, headers=["Ingrediente", "Necessário", "Disponível", "Unidade"], tablefmt="grid"))
        pausar()


def fluxo_configuracoes(gerenciador: GerenciadorFichas):
    cabecalho("CONFIGURAÇÕES PADRÃO DO SISTEMA")
    print(f"Margem de lucro padrão atual: {gerenciador.config['margem_padrao']}%")
    print(f"Custo de mão de obra por hora padrão atual: R$ {gerenciador.config['custo_mao_de_obra_hora_padrao']:.2f}")
    if ler_confirmacao("\nDeseja alterar essas configurações?"):
        margem = ler_float("Nova margem de lucro padrão (%): ", minimo=0,
                            padrao=gerenciador.config["margem_padrao"])
        custo_hora = ler_float("Novo custo de mão de obra por hora (R$): ", minimo=0,
                                padrao=gerenciador.config["custo_mao_de_obra_hora_padrao"])
        gerenciador.atualizar_config(margem_padrao=margem, custo_mao_de_obra_hora_padrao=custo_hora)
        print("✅ Configurações atualizadas com sucesso!")


# ====================================================================== #
# Menu principal
# ====================================================================== #

OPCOES_MENU = {
    "1": ("Adicionar ficha técnica", fluxo_adicionar_ficha),
    "2": ("Listar fichas técnicas", fluxo_listar_fichas),
    "3": ("Ver detalhes de uma ficha", fluxo_ver_detalhes),
    "4": ("Editar ficha técnica", fluxo_editar_ficha),
    "5": ("Excluir ficha técnica", fluxo_excluir_ficha),
    "6": ("Buscar fichas (nome ou categoria)", fluxo_buscar),
    "7": ("Exportar ficha para PDF", fluxo_exportar_pdf),
    "8": ("Exportar todas as fichas para Excel", fluxo_exportar_excel),
    "9": ("Controle de estoque", fluxo_estoque),
    "10": ("Relatório de custo médio por categoria", fluxo_relatorio_categoria),
    "11": ("Configurações padrão (margem / mão de obra)", fluxo_configuracoes),
}


def executar_menu():
    """Loop principal do programa — exibe o menu e despacha para cada fluxo."""
    gerenciador = GerenciadorFichas()

    print("\n🍕 Bem-vindo ao Sistema de Fichas Técnicas! 🍕")
    print(f"({len(gerenciador.fichas)} ficha(s) técnica(s) carregada(s) de '{gerenciador.arquivo_dados}')")

    while True:
        cabecalho("MENU PRINCIPAL — FICHAS TÉCNICAS")
        for chave, (titulo, _) in OPCOES_MENU.items():
            print(f"  {chave}. {titulo}")
        print("  0. Sair")

        opcao = ler_opcao_menu("\nEscolha uma opção: ", set(OPCOES_MENU.keys()) | {"0"})

        if opcao == "0":
            print("\n👋 Até logo! Seus dados foram salvos automaticamente.")
            break

        _, funcao = OPCOES_MENU[opcao]
        try:
            funcao(gerenciador)
        except KeyboardInterrupt:
            raise
        except Exception as erro:
            print(f"\n❌ Ocorreu um erro inesperado: {erro}")
        pausar()


if __name__ == "__main__":
    try:
        executar_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Programa encerrado pelo usuário. Até logo!")
