import pandas as pd
import re
import pdfplumber
import os
from datetime import datetime

def extrair_texto_pdf(pdf_path):
    """Extrai texto de um arquivo PDF."""
    texto_completo = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            texto_completo += page.extract_text() + "\n"
    return texto_completo


"""Processa o texto do extrato Asaas e retorna um DataFrame."""
def processar_extrato_asaas(texto_extrato):

    linhas = texto_extrato.split('\n')
    
    empresa = linhas[0].strip()
    cnpj_info = linhas[1].strip()
    periodo = linhas[2].strip()
    
    # Localizar saldos
    saldo_inicial = None
    saldo_final = None
    for i, linha in enumerate(linhas[:10]):
        if "Saldo inicial do período" in linha:
            match = re.search(r"R\$\s+([-]?\d+,\d{2})", linha)
            if match:
                saldo_inicial = match.group(1)
        if "Saldo final do período" in linha:
            match = re.search(r"R\$\s+([-]?\d+,\d{2})", linha)
            if match:
                saldo_final = match.group(1)
    
    # Encontrar onde começa a tabela de movimentações
    indice_inicio = None
    for i, linha in enumerate(linhas):
        if "Data Movimentações Valor" in linha:
            indice_inicio = i + 1
            break
    
    if indice_inicio is None:
        raise ValueError("Não foi possível encontrar a tabela de movimentações no extrato.")
    
    movimentacoes = []
    
    # Expressão regular para extrair data, descrição e valor
    pattern = r"(\d{2}/\d{2}/\d{4})\s+(.*?)\s+R\$\s+([-]?\d+,\d{2})"
    
    # Processar cada linha da tabela de movimentações
    for linha in linhas[indice_inicio:]:
        if not linha.strip():
            continue 
        
        match = re.search(pattern, linha)
        if match:
            data, descricao, valor = match.groups()
            data_obj = datetime.strptime(data, "%d/%m/%Y")
            valor_float = float(valor.replace(".", "").replace(",", "."))
            
            movimentacoes.append({
                "Data": data_obj,
                "Descrição": descricao.strip(),
                "Valor": valor_float
            })
        else:
            print(f"Aviso: Linha não processada: {linha}")
    
    # Criar DataFrame
    df = pd.DataFrame(movimentacoes)
    
    # Adicionar metadados como atributos do DataFrame
    df.attrs["empresa"] = empresa
    df.attrs["cnpj_info"] = cnpj_info
    df.attrs["periodo"] = periodo
    df.attrs["saldo_inicial"] = saldo_inicial
    df.attrs["saldo_final"] = saldo_final
    
    return df
    """Adiciona categorias às movimentações baseadas nos padrões."""
def categorizar_movimentacoes(df):
    
    # Função para determinar categoria
    def get_categoria(descricao):
        descricao = descricao.lower()
        if "antecipação" in descricao:
            return "Antecipação"
        elif "taxa de cartão" in descricao:
            return "Taxa de Cartão"
        elif "taxa de antecipação" in descricao:
            return "Taxa de Antecipação"
        elif "pix" in descricao:
            return "Transferência PIX"
        elif "cobrança recebida" in descricao:
            return "Cobrança Recebida"
        elif "estorno" in descricao:
            return "Estorno"
        elif "baixa da antecipação" in descricao:
            return "Baixa de Antecipação"
        elif "bloqueio" in descricao:
            return "Bloqueio de Saldo"
        elif "cancelamento" in descricao:
            return "Cancelamento de Bloqueio"
        else:
            return "Outros"
    
    # Aplicar a função a cada linha
    df["Categoria"] = df["Descrição"].apply(get_categoria)
    
    # Adicionar coluna de Tipo (Entrada ou Saída)
    df["Tipo"] = df["Valor"].apply(lambda x: "Entrada" if x >= 0 else "Saída")
    
    return df

def extrair_cliente(descricao):
    """Extrai o nome do cliente da descrição da transação, quando disponível."""
    # Padrão comum: algo como "fatura nr. 123456789 Nome Cliente"
    match = re.search(r"fatura nr\.\s+\d+\s+(.*?)$", descricao)
    if match:
        return match.group(1).strip()
    return None

def analisar_fluxo_caixa(df):
    """Analisa o fluxo de caixa por dia e categoria."""
    # Resumo por dia
    resumo_diario = df.groupby(df["Data"].dt.date)["Valor"].sum().reset_index()
    
    # Resumo por categoria
    resumo_categoria = df.groupby("Categoria")["Valor"].agg(["sum", "count"]).reset_index()
    resumo_categoria.columns = ["Categoria", "Valor Total", "Quantidade"]
    
    # Top clientes (se tiver informação de cliente)
    if "Cliente" in df.columns:
        top_clientes = df.groupby("Cliente")["Valor"].sum().sort_values(ascending=False).head(10)
    else:
        top_clientes = None
    
    return {
        "resumo_diario": resumo_diario,
        "resumo_categoria": resumo_categoria,
        "top_clientes": top_clientes
    }


    """
    Cria um resumo diário agrupado por data e categoria,
    mostrando entradas e saídas separadamente.
    """
def criar_resumo_diario_categoria(df):
   
    df_copy = df.copy()
    df_copy["Data"] = df_copy["Data"].dt.date
    
    entradas = df_copy[df_copy["Valor"] >= 0].copy()
    saidas = df_copy[df_copy["Valor"] < 0].copy()
    
    entradas_agrupadas = entradas.groupby(["Data", "Categoria"])["Valor"].agg([
        ("Valor_Entrada", "sum"), 
        ("Quantidade_Entrada", "count")
    ]).reset_index()
    
    saidas_agrupadas = saidas.groupby(["Data", "Categoria"])["Valor"].agg([
        ("Valor_Saída", lambda x: abs(x.sum())), 
        ("Quantidade_Saída", "count")
    ]).reset_index()
    
    # Mesclar os dois DataFrames (entradas e saídas)
    resultado = pd.merge(
        entradas_agrupadas, 
        saidas_agrupadas, 
        on=["Data", "Categoria"], 
        how="outer"
    ).fillna(0)
    
    resultado["Saldo"] = resultado["Valor_Entrada"] - resultado["Valor_Saída"]
    resultado = resultado.sort_values(["Data", "Categoria"])
    
    # Calcular totais por dia
    totais_diarios = df_copy.groupby("Data").agg(
        Valor_Total_Entrada=("Valor", lambda x: x[x >= 0].sum()),
        Valor_Total_Saída=("Valor", lambda x: abs(x[x < 0].sum())),
        Saldo_Diário=("Valor", "sum")
    ).reset_index()
    
    return resultado, totais_diarios


"""Salva os resultados em formatos úteis."""
def salvar_resultados(df, caminho_saida, analise=None):
    os.makedirs(caminho_saida, exist_ok=True)
    df.to_csv(os.path.join(caminho_saida, "movimentacoes.csv"), index=False, encoding="utf-8-sig")
    
    resumo_diario_categoria, totais_diarios = criar_resumo_diario_categoria(df)
    resumo_diario_categoria.to_csv(
        os.path.join(caminho_saida, "resumo_diario_categoria.csv"), 
        index=False, 
        encoding="utf-8-sig"
    )
    
    totais_diarios.to_csv(
        os.path.join(caminho_saida, "totais_diarios.csv"), 
        index=False, 
        encoding="utf-8-sig"
    )
    
    # Salvar Excel com múltiplas abas
    with pd.ExcelWriter(os.path.join(caminho_saida, "extrato_processado.xlsx")) as writer:
        df.to_excel(writer, sheet_name="Movimentações", index=False)
        
        resumo_diario_categoria.to_excel(writer, sheet_name="Resumo Diário por Categoria", index=False)
        totais_diarios.to_excel(writer, sheet_name="Totais Diários", index=False)
        
        if analise:
            analise["resumo_diario"].to_excel(writer, sheet_name="Resumo Diário", index=False)
            analise["resumo_categoria"].to_excel(writer, sheet_name="Resumo por Categoria", index=False)
            
            if analise["top_clientes"] is not None:
                analise["top_clientes"].to_excel(writer, sheet_name="Top Clientes")
        
        pd.DataFrame([
            ["Empresa", df.attrs.get("empresa", "")],
            ["CNPJ/Conta", df.attrs.get("cnpj_info", "")],
            ["Período", df.attrs.get("periodo", "")],
            ["Saldo Inicial", df.attrs.get("saldo_inicial", "")],
            ["Saldo Final", df.attrs.get("saldo_final", "")],
        ], columns=["Informação", "Valor"]).to_excel(writer, sheet_name="Metadados", index=False)



def main(pdf_path, caminho_saida="resultados_extrato"):
    
    print(f"Extraindo texto do arquivo: {pdf_path}")
    texto_extrato = extrair_texto_pdf(pdf_path)
    
    # Processar o extrato
    print("Processando extrato...")
    df = processar_extrato_asaas(texto_extrato)
    
    # Adicionar categorias
    print("Categorizando movimentações...")
    df = categorizar_movimentacoes(df)
    
    # Adicionar informação de cliente quando disponível
    df["Cliente"] = df["Descrição"].apply(extrair_cliente)
    
    # Analisar fluxo de caixa
    print("Analisando fluxo de caixa...")
    analise = analisar_fluxo_caixa(df)
    
    print(f"Salvando resultados em: {caminho_saida}")
    salvar_resultados(df, caminho_saida, analise)
    
    print(f"Processamento concluído! Foram extraídas {len(df)} movimentações.")
    
    # Gerar resumo visual do fluxo de caixa diário
    resumo, totais = criar_resumo_diario_categoria(df)
    print(f"Resumo diário por categoria gerado com {len(resumo)} linhas.")
    print(f"Totais diários gerados com {len(totais)} dias.")
    
    return df

if __name__ == "__main__":
    pdf_path = '/seu_caminho_aqui'
    main(pdf_path)
    