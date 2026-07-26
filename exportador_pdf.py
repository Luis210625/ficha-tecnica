"""
exportador_pdf.py
===================
Geração de PDF profissional para uma ficha técnica individual,
usando reportlab (Platypus).
"""

from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem, HRFlowable
)

from models import FichaTecnica

# Paleta de cores do documento (tons de vermelho/laranja, remetendo a pizzaria)
COR_PRIMARIA = colors.HexColor("#B23A2E")
COR_SECUNDARIA = colors.HexColor("#F4E9E1")
COR_TEXTO = colors.HexColor("#2B2B2B")
COR_LINHA = colors.HexColor("#D9C7BC")


def _construir_estilos():
    """Cria os estilos de parágrafo usados no documento."""
    estilos = getSampleStyleSheet()

    estilos.add(ParagraphStyle(
        name="TituloPrato",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=COR_PRIMARIA,
        alignment=TA_LEFT,
        spaceAfter=2,
    ))
    estilos.add(ParagraphStyle(
        name="Subtitulo",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=11,
        textColor=colors.grey,
        spaceAfter=10,
    ))
    estilos.add(ParagraphStyle(
        name="SecaoTitulo",
        parent=estilos["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=COR_PRIMARIA,
        spaceBefore=14,
        spaceAfter=6,
    ))
    estilos.add(ParagraphStyle(
        name="TextoNormal",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=COR_TEXTO,
        leading=14,
    ))
    estilos.add(ParagraphStyle(
        name="Rodape",
        parent=estilos["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        textColor=colors.grey,
    ))
    return estilos


def _tabela_info_geral(ficha: FichaTecnica, estilos) -> Table:
    """Tabela com as informações gerais do prato (porção, tempo, categoria etc.)."""
    dados = [
        ["Categoria", ficha.categoria, "Porção/Rendimento", ficha.porcao_rendimento],
        ["Tempo de preparo", f"{ficha.tempo_preparo_min} min", "Alergênicos",
         ", ".join(ficha.alergenicos) if ficha.alergenicos else "Nenhum informado"],
    ]
    tabela = Table(dados, colWidths=[3.2 * cm, 5.3 * cm, 3.2 * cm, 5.3 * cm])
    tabela.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTNAME", (3, 0), (3, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), COR_TEXTO),
        ("BACKGROUND", (0, 0), (0, -1), COR_SECUNDARIA),
        ("BACKGROUND", (2, 0), (2, -1), COR_SECUNDARIA),
        ("GRID", (0, 0), (-1, -1), 0.5, COR_LINHA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tabela


def _tabela_ingredientes(ficha: FichaTecnica, estilos) -> Table:
    """Tabela com todos os ingredientes e seus custos."""
    cabecalho = ["Ingrediente", "Quantidade", "Unid.", "Custo unit. (R$)", "Custo total (R$)"]
    linhas = [cabecalho]
    for ing in ficha.ingredientes:
        linhas.append([
            ing.nome,
            f"{ing.quantidade:g}",
            ing.unidade,
            f"{ing.custo_unitario:.4f}",
            f"{ing.custo_total:.2f}",
        ])
    linhas.append(["", "", "", "Total dos ingredientes:", f"R$ {ficha.custo_ingredientes:.2f}"])

    tabela = Table(linhas, colWidths=[5.8 * cm, 2.6 * cm, 1.6 * cm, 3.5 * cm, 3.5 * cm], repeatRows=1)
    estilo = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COR_PRIMARIA),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -2), 0.5, COR_LINHA),
        ("LINEABOVE", (0, -1), (-1, -1), 1, COR_PRIMARIA),
        ("FONTNAME", (3, -1), (4, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])
    # Zebra striping nas linhas de ingredientes
    for i in range(1, len(linhas) - 1):
        if i % 2 == 0:
            estilo.add("BACKGROUND", (0, i), (-1, i), COR_SECUNDARIA)
    tabela.setStyle(estilo)
    return tabela


def _tabela_custos(ficha: FichaTecnica, estilos) -> Table:
    """Tabela-resumo com todos os indicadores financeiros do prato."""
    dados = [
        ["Custo dos ingredientes", f"R$ {ficha.custo_ingredientes:.2f}"],
        ["Custo de mão de obra", f"R$ {ficha.custo_mao_de_obra:.2f}"],
        ["Custo total de produção", f"R$ {ficha.custo_total_producao:.2f}"],
        ["Preço de venda sugerido", f"R$ {ficha.preco_venda_sugerido:.2f}"],
        ["Preço de venda praticado", f"R$ {ficha.preco_venda_final:.2f}"],
        ["Margem de lucro", f"{ficha.margem_lucro_percentual:.1f}%  (R$ {ficha.margem_lucro_valor:.2f})"],
        ["Food Cost %", f"{ficha.food_cost_percentual:.1f}%"],
    ]
    tabela = Table(dados, colWidths=[8 * cm, 6 * cm])
    tabela.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, -1), COR_TEXTO),
        ("GRID", (0, 0), (-1, -1), 0.5, COR_LINHA),
        ("BACKGROUND", (0, 2), (-1, 2), COR_SECUNDARIA),
        ("BACKGROUND", (0, 4), (-1, 4), COR_SECUNDARIA),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tabela


def exportar_ficha_pdf(ficha: FichaTecnica, caminho_saida: str) -> str:
    """
    Gera o PDF da ficha técnica informada e salva em `caminho_saida`.
    Retorna o caminho final do arquivo gerado.
    """
    caminho = Path(caminho_saida)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    estilos = _construir_estilos()
    doc = SimpleDocTemplate(
        str(caminho),
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        title=f"Ficha Técnica - {ficha.nome}",
    )

    elementos = []

    # Cabeçalho
    elementos.append(Paragraph("FICHA TÉCNICA", estilos["Subtitulo"]))
    elementos.append(Paragraph(ficha.nome, estilos["TituloPrato"]))
    elementos.append(HRFlowable(width="100%", thickness=1.2, color=COR_PRIMARIA, spaceAfter=10))

    # Informações gerais
    elementos.append(_tabela_info_geral(ficha, estilos))
    elementos.append(Spacer(1, 12))

    # Ingredientes
    elementos.append(Paragraph("Ingredientes", estilos["SecaoTitulo"]))
    if ficha.ingredientes:
        elementos.append(_tabela_ingredientes(ficha, estilos))
    else:
        elementos.append(Paragraph("Nenhum ingrediente cadastrado.", estilos["TextoNormal"]))

    # Modo de preparo
    elementos.append(Paragraph("Modo de Preparo", estilos["SecaoTitulo"]))
    if ficha.modo_preparo:
        itens = [
            ListItem(Paragraph(passo, estilos["TextoNormal"]), spaceAfter=4)
            for passo in ficha.modo_preparo
        ]
        elementos.append(ListFlowable(itens, bulletType="1", start="1"))
    else:
        elementos.append(Paragraph("Nenhum passo cadastrado.", estilos["TextoNormal"]))

    # Custos e precificação
    elementos.append(Paragraph("Custos e Precificação", estilos["SecaoTitulo"]))
    elementos.append(_tabela_custos(ficha, estilos))

    # Observações
    elementos.append(Paragraph("Observações", estilos["SecaoTitulo"]))
    texto_obs = ficha.observacoes.strip() if ficha.observacoes and ficha.observacoes.strip() else "Nenhuma observação registrada."
    elementos.append(Paragraph(texto_obs, estilos["TextoNormal"]))

    # Rodapé
    elementos.append(Spacer(1, 16))
    elementos.append(HRFlowable(width="100%", thickness=0.5, color=COR_LINHA, spaceAfter=6))
    elementos.append(Paragraph(
        f"Documento gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} "
        f"• Ficha #{ficha.id} • Última atualização: {ficha.data_atualizacao}",
        estilos["Rodape"],
    ))

    doc.build(elementos)
    return str(caminho)
