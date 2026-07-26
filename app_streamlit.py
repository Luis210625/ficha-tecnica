"""
app_streamlit.py
==================
Interface web opcional (Streamlit) do Sistema de Fichas Técnicas.

Execute com:
    streamlit run app_streamlit.py

Observação: esta interface cobre cadastro, listagem/busca, exportação,
estoque e relatórios. Para edições mais avançadas (ex.: reeditar a lista
completa de ingredientes de uma ficha já existente), utilize a versão CLI
(`python main.py`), que oferece edição campo a campo mais detalhada.
"""

from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

from gerenciador import GerenciadorFichas
from models import Ingrediente, CATEGORIAS_PADRAO, UNIDADES_VALIDAS, ALERGENICOS_COMUNS
from exportador_pdf import exportar_ficha_pdf
from exportador_excel import exportar_todas_excel

def verificar_senha():
    """Pede uma senha antes de liberar o acesso ao app."""
    def senha_correta():
        if st.session_state["senha_digitada"] == st.secrets["senha_acesso"]:
            st.session_state["autenticado"] = True
            del st.session_state["senha_digitada"]
        else:
            st.session_state["autenticado"] = False

    if st.session_state.get("autenticado", False):
        return True

    st.text_input("Senha de acesso", type="password", key="senha_digitada", on_change=senha_correta)
    if st.session_state.get("autenticado") is False:
        st.error("Senha incorreta.")
    return False

if not verificar_senha():
    st.stop()

st.set_page_config(page_title="Fichas Técnicas", page_icon="🍕", layout="wide")

PASTA_EXPORTACAO = Path("exportados")
PASTA_EXPORTACAO.mkdir(exist_ok=True)


# ---------------------------------------------------------------- #
# Gerenciador: recarregado do disco a cada execução do script, para
# sempre refletir o estado mais atual salvo em JSON.
# ---------------------------------------------------------------- #
@st.cache_resource
def obter_gerenciador():
    return GerenciadorFichas()


def gerenciador_atualizado() -> GerenciadorFichas:
    """Recarrega os dados do disco (o cache_resource mantém a mesma instância)."""
    g = obter_gerenciador()
    g.carregar_dados()
    return g


if "ingredientes_form" not in st.session_state:
    st.session_state.ingredientes_form = [{"nome": "", "quantidade": 0.0, "unidade": "g", "custo_unitario": 0.0}]


# ================================================================== #
# Barra lateral — navegação
# ================================================================== #
st.sidebar.title("🍕 Fichas Técnicas")
pagina = st.sidebar.radio(
    "Navegação",
    ["📋 Fichas Cadastradas", "➕ Nova Ficha", "📦 Estoque", "📊 Relatórios", "⚙️ Configurações"],
)

g = gerenciador_atualizado()
st.sidebar.markdown("---")
st.sidebar.caption(f"{len(g.fichas)} ficha(s) técnica(s) cadastrada(s)")


# ================================================================== #
# Página: Fichas Cadastradas (listar, buscar, ver, exportar, excluir)
# ================================================================== #
if pagina == "📋 Fichas Cadastradas":
    st.title("📋 Fichas Técnicas Cadastradas")

    col_busca, col_categoria, col_export = st.columns([2, 1, 1])
    termo_busca = col_busca.text_input("Buscar por nome ou categoria", "")
    categorias_presentes = ["Todas"] + sorted({f.categoria for f in g.fichas})
    categoria_filtro = col_categoria.selectbox("Categoria", categorias_presentes)

    col_export.write("")
    col_export.write("")
    if col_export.button("📊 Exportar todas p/ Excel", use_container_width=True):
        if not g.fichas:
            st.warning("Não há fichas cadastradas para exportar.")
        else:
            data_str = datetime.now().strftime("%Y-%m-%d_%H%M")
            caminho = PASTA_EXPORTACAO / f"fichas_tecnicas_{data_str}.xlsx"
            relatorio = g.relatorio_custo_medio_por_categoria()
            exportar_todas_excel(g.fichas, relatorio, str(caminho))
            with open(caminho, "rb") as arq:
                st.download_button("⬇️ Baixar planilha Excel", arq, file_name=caminho.name, use_container_width=True)

    # Aplica filtros
    fichas_exibidas = g.fichas
    if termo_busca:
        fichas_exibidas = g.buscar(termo_busca)
    if categoria_filtro != "Todas":
        fichas_exibidas = [f for f in fichas_exibidas if f.categoria == categoria_filtro]

    if not fichas_exibidas:
        st.info("Nenhuma ficha técnica encontrada.")
    else:
        for f in fichas_exibidas:
            with st.expander(f"**{f.nome}** — {f.categoria}  |  💰 R$ {f.preco_venda_final:.2f}  |  Margem {f.margem_lucro_percentual:.1f}%"):
                col_a, col_b = st.columns([2, 1])

                with col_a:
                    st.markdown(f"**Porção/Rendimento:** {f.porcao_rendimento}")
                    st.markdown(f"**Tempo de preparo:** {f.tempo_preparo_min} min")
                    st.markdown(f"**Alergênicos:** {', '.join(f.alergenicos) if f.alergenicos else 'Nenhum'}")

                    st.markdown("**Ingredientes:**")
                    df_ing = pd.DataFrame([{
                        "Ingrediente": i.nome, "Quantidade": f"{i.quantidade:g} {i.unidade}",
                        "Custo unit. (R$)": f"{i.custo_unitario:.4f}", "Custo total (R$)": f"{i.custo_total:.2f}",
                    } for i in f.ingredientes])
                    st.dataframe(df_ing, hide_index=True, use_container_width=True)

                    st.markdown("**Modo de preparo:**")
                    for i, passo in enumerate(f.modo_preparo, start=1):
                        st.markdown(f"{i}. {passo}")

                    if f.observacoes:
                        st.markdown(f"**Observações:** {f.observacoes}")

                with col_b:
                    st.metric("Custo total", f"R$ {f.custo_total_producao:.2f}")
                    st.metric("Preço de venda", f"R$ {f.preco_venda_final:.2f}")
                    st.metric("Margem de lucro", f"{f.margem_lucro_percentual:.1f}%")
                    st.metric("Food Cost %", f"{f.food_cost_percentual:.1f}%")

                    if st.button("📄 Exportar PDF", key=f"pdf_{f.id}", use_container_width=True):
                        nome_arquivo = f"{f.id:03d}_{f.nome}".replace(" ", "_").replace("/", "-")
                        caminho = PASTA_EXPORTACAO / f"{nome_arquivo}.pdf"
                        exportar_ficha_pdf(f, str(caminho))
                        with open(caminho, "rb") as arq:
                            st.download_button(
                                "⬇️ Baixar PDF", arq, file_name=caminho.name,
                                mime="application/pdf", key=f"dl_pdf_{f.id}", use_container_width=True,
                            )

                    with st.form(key=f"editar_rapido_{f.id}"):
                        st.caption("Ajuste rápido")
                        nova_margem = st.number_input("Margem de lucro (%)", value=f.margem_lucro_desejada, min_value=0.0, max_value=99.0, key=f"margem_{f.id}")
                        novo_custo_hora = st.number_input("Mão de obra (R$/h)", value=f.custo_mao_de_obra_hora, min_value=0.0, key=f"mo_{f.id}")
                        salvar = st.form_submit_button("💾 Salvar ajustes")
                        if salvar:
                            g.editar_ficha(f.id, margem_lucro_desejada=nova_margem, custo_mao_de_obra_hora=novo_custo_hora)
                            st.success("Atualizado!")
                            st.rerun()

                    if st.button("🗑️ Excluir ficha", key=f"del_{f.id}", use_container_width=True):
                        g.excluir_ficha(f.id)
                        st.success(f"Ficha '{f.nome}' excluída.")
                        st.rerun()


# ================================================================== #
# Página: Nova Ficha
# ================================================================== #
elif pagina == "➕ Nova Ficha":
    st.title("➕ Nova Ficha Técnica")

    nome = st.text_input("Nome do prato *")
    col1, col2 = st.columns(2)
    categoria = col1.selectbox("Categoria *", CATEGORIAS_PADRAO)
    porcao = col2.text_input("Porção/Rendimento *", placeholder="ex.: 1 pizza de 35cm / 8 fatias")

    st.subheader("Ingredientes")
    for idx, ing in enumerate(st.session_state.ingredientes_form):
        c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1, 1.5, 0.5])
        ing["nome"] = c1.text_input("Nome", value=ing["nome"], key=f"ing_nome_{idx}", label_visibility="collapsed", placeholder="Nome do ingrediente")
        ing["quantidade"] = c2.number_input("Qtd.", value=ing["quantidade"], min_value=0.0, key=f"ing_qtd_{idx}", label_visibility="collapsed")
        ing["unidade"] = c3.selectbox("Unid.", UNIDADES_VALIDAS, index=UNIDADES_VALIDAS.index(ing["unidade"]), key=f"ing_un_{idx}", label_visibility="collapsed")
        ing["custo_unitario"] = c4.number_input("Custo unit. (R$)", value=ing["custo_unitario"], min_value=0.0, format="%.4f", key=f"ing_custo_{idx}", label_visibility="collapsed")
        if c5.button("❌", key=f"ing_del_{idx}") and len(st.session_state.ingredientes_form) > 1:
            st.session_state.ingredientes_form.pop(idx)
            st.rerun()

    if st.button("➕ Adicionar ingrediente"):
        st.session_state.ingredientes_form.append({"nome": "", "quantidade": 0.0, "unidade": "g", "custo_unitario": 0.0})
        st.rerun()

    st.subheader("Modo de preparo")
    texto_preparo = st.text_area("Um passo por linha *", height=120, placeholder="Abra a massa em disco de 35cm.\nEspalhe o molho de tomate...\n...")

    st.subheader("Outras informações")
    col3, col4, col5 = st.columns(3)
    tempo_preparo = col3.number_input("Tempo de preparo (min) *", min_value=0, value=15)
    margem = col4.number_input("Margem de lucro desejada (%)", min_value=0.0, max_value=99.0, value=float(g.config["margem_padrao"]))
    custo_hora = col5.number_input("Custo mão de obra (R$/hora)", min_value=0.0, value=float(g.config["custo_mao_de_obra_hora_padrao"]))

    alergenicos = st.multiselect("Alergênicos", ALERGENICOS_COMUNS)
    outros_alergenicos = st.text_input("Outros alergênicos (separados por vírgula)", "")
    observacoes = st.text_area("Observações (validade após preparo, temperatura de armazenamento etc.)", "")

    usar_preco_manual = st.checkbox("Definir preço de venda fixo (em vez do sugerido automaticamente)")
    preco_manual = st.number_input("Preço de venda (R$)", min_value=0.0, value=0.0, disabled=not usar_preco_manual)

    if st.button("💾 Salvar Ficha Técnica", type="primary"):
        erros = []
        if not nome.strip():
            erros.append("Informe o nome do prato.")
        if not porcao.strip():
            erros.append("Informe a porção/rendimento.")
        ingredientes_validos = [i for i in st.session_state.ingredientes_form if i["nome"].strip()]
        if not ingredientes_validos:
            erros.append("Cadastre pelo menos um ingrediente.")
        passos = [p.strip() for p in texto_preparo.split("\n") if p.strip()]
        if not passos:
            erros.append("Informe pelo menos um passo do modo de preparo.")

        if erros:
            for e in erros:
                st.error(e)
        else:
            try:
                lista_ingredientes = [
                    Ingrediente(i["nome"], i["quantidade"], i["unidade"], i["custo_unitario"])
                    for i in ingredientes_validos
                ]
                lista_alergenicos = list(alergenicos)
                if outros_alergenicos.strip():
                    lista_alergenicos += [a.strip() for a in outros_alergenicos.split(",") if a.strip()]

                nova_ficha = g.adicionar_ficha(
                    nome=nome, categoria=categoria, porcao_rendimento=porcao,
                    ingredientes=lista_ingredientes, modo_preparo=passos,
                    tempo_preparo_min=tempo_preparo, alergenicos=lista_alergenicos,
                    observacoes=observacoes, margem_lucro_desejada=margem,
                    custo_mao_de_obra_hora=custo_hora,
                    preco_venda_manual=preco_manual if usar_preco_manual and preco_manual > 0 else None,
                )
                st.success(f"✅ Ficha '{nova_ficha.nome}' criada com sucesso! Custo total: R$ {nova_ficha.custo_total_producao:.2f} | Preço sugerido: R$ {nova_ficha.preco_venda_sugerido:.2f}")
                st.session_state.ingredientes_form = [{"nome": "", "quantidade": 0.0, "unidade": "g", "custo_unitario": 0.0}]
            except ValueError as erro:
                st.error(f"Erro ao criar ficha: {erro}")


# ================================================================== #
# Página: Estoque
# ================================================================== #
elif pagina == "📦 Estoque":
    st.title("📦 Controle de Estoque")

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Estoque atual")
        itens = g.listar_estoque()
        if itens:
            df_estoque = pd.DataFrame([
                {"Ingrediente": i["nome"], "Quantidade": i["quantidade"], "Unidade": i["unidade"]}
                for i in itens
            ])
            st.dataframe(df_estoque, hide_index=True, use_container_width=True)
        else:
            st.info("Nenhum item em estoque ainda.")

        st.subheader("Repor estoque")
        with st.form("form_estoque"):
            nome_ing = st.text_input("Nome do ingrediente")
            qtd_ing = st.number_input("Quantidade a adicionar", min_value=0.0, value=0.0)
            unid_ing = st.selectbox("Unidade", UNIDADES_VALIDAS)
            if st.form_submit_button("➕ Adicionar ao estoque"):
                if not nome_ing.strip() or qtd_ing <= 0:
                    st.error("Informe nome e quantidade válida.")
                else:
                    try:
                        g.adicionar_estoque(nome_ing, qtd_ing, unid_ing)
                        st.success("Estoque atualizado!")
                        st.rerun()
                    except ValueError as erro:
                        st.error(str(erro))

    with col_b:
        st.subheader("Produção / baixa de estoque")
        if not g.fichas:
            st.info("Cadastre alguma ficha técnica primeiro.")
        else:
            opcoes = {f"#{f.id} — {f.nome}": f.id for f in g.fichas}
            escolha = st.selectbox("Ficha técnica", list(opcoes.keys()))
            id_escolhido = opcoes[escolha]
            porcoes = st.number_input("Porções a produzir", min_value=1, value=1, step=1)

            if st.button("🔎 Verificar disponibilidade"):
                resultado = g.verificar_estoque_ficha(id_escolhido)
                st.info(f"É possível produzir até **{resultado['porcoes_possiveis']}** porção(ões) com o estoque atual.")
                if resultado["ingredientes_faltando"]:
                    st.dataframe(pd.DataFrame(resultado["ingredientes_faltando"]), hide_index=True, use_container_width=True)

            if st.button("✅ Confirmar produção (dar baixa no estoque)", type="primary"):
                resultado = g.dar_baixa_estoque(id_escolhido, porcoes)
                if resultado["sucesso"]:
                    st.success(f"Baixa registrada para {porcoes} porção(ões)!")
                    st.rerun()
                else:
                    st.error("Estoque insuficiente para essa produção:")
                    st.dataframe(pd.DataFrame(resultado["ingredientes_insuficientes"]), hide_index=True, use_container_width=True)


# ================================================================== #
# Página: Relatórios
# ================================================================== #
elif pagina == "📊 Relatórios":
    st.title("📊 Relatório de Custo Médio por Categoria")

    relatorio = g.relatorio_custo_medio_por_categoria()
    if not relatorio:
        st.info("Nenhuma ficha técnica cadastrada ainda.")
    else:
        df_relatorio = pd.DataFrame([
            {"Categoria": cat, "Qtd. Fichas": d["quantidade_fichas"], "Custo Médio (R$)": d["custo_medio"],
             "Preço Médio (R$)": d["preco_medio"], "Margem Média (%)": d["margem_media"],
             "Food Cost Médio (%)": d["food_cost_medio"]}
            for cat, d in relatorio.items()
        ])
        st.dataframe(df_relatorio, hide_index=True, use_container_width=True)

        col1, col2 = st.columns(2)
        col1.bar_chart(df_relatorio.set_index("Categoria")[["Custo Médio (R$)", "Preço Médio (R$)"]])
        col2.bar_chart(df_relatorio.set_index("Categoria")[["Food Cost Médio (%)", "Margem Média (%)"]])


# ================================================================== #
# Página: Configurações
# ================================================================== #
elif pagina == "⚙️ Configurações":
    st.title("⚙️ Configurações Padrão do Sistema")
    st.caption("Esses valores são usados como sugestão inicial ao cadastrar uma nova ficha técnica.")

    with st.form("form_config"):
        margem_padrao = st.number_input("Margem de lucro padrão (%)", min_value=0.0, max_value=99.0, value=float(g.config["margem_padrao"]))
        custo_hora_padrao = st.number_input("Custo de mão de obra padrão (R$/hora)", min_value=0.0, value=float(g.config["custo_mao_de_obra_hora_padrao"]))
        if st.form_submit_button("💾 Salvar configurações"):
            g.atualizar_config(margem_padrao=margem_padrao, custo_mao_de_obra_hora_padrao=custo_hora_padrao)
            st.success("Configurações atualizadas!")
