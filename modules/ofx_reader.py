import hashlib
import io
from ofxparse import OfxParser
from modules.database import executar_query
from datetime import date
from decimal import Decimal

# ============================================================
# 🔹 Geração de assinatura única para cada lançamento
# ============================================================
def gerar_assinatura(lanc):
    base = f"{lanc['data']}{lanc['valor']}{lanc['historico']}{lanc['banco']}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()

# ============================================================
# 🔹 Normalização de OFX SGML (Itaú, Bradesco, etc.)
# ============================================================
def normalizar_ofx_sgml(conteudo):
    """
    Converte OFX SGML (v1.02) em XML válido para o OfxParser.
    """
    # Remove cabeçalho
    if conteudo.startswith("OFXHEADER"):
        conteudo = conteudo.split("<OFX>", 1)[1]
        conteudo = "<OFX>" + conteudo

    # Fecha tags corretamente
    linhas = []
    for linha in conteudo.splitlines():
        if linha.strip() and linha.strip().startswith("<") and not linha.strip().endswith(">"):
            # Exemplo: <FITID>20250102001 -> vira <FITID>20250102001</FITID>
            if ">" in linha:
                tag, valor = linha.split(">", 1)
                tagname = tag.replace("<", "").strip()
                linhas.append(f"<{tagname}>{valor.strip()}</{tagname}>")
            else:
                linhas.append(linha)
        else:
            linhas.append(linha)
    return "\n".join(linhas)

# ============================================================
# 🔹 Leitura do arquivo OFX
# ============================================================
def ler_ofx(arquivo):
    try:
        return _parse_ofx(arquivo)
    except UnicodeDecodeError:
        content = arquivo.read()
        encodings = ["utf-8", "latin-1", "cp1252"]
        for enc in encodings:
            try:
                text = content.decode(enc)
                # Normaliza SGML -> XML se necessário
                if "OFXHEADER" in text:
                    text = normalizar_ofx_sgml(text)
                ofx = OfxParser.parse(io.StringIO(text))
                return _extrair_lancamentos(ofx, arquivo)
            except Exception as e:
                print("[DEBUG] Falha ao parsear com encoding", enc, "erro:", e)
                continue
        return []

def _parse_ofx(arquivo):
    ofx = OfxParser.parse(arquivo)
    return _extrair_lancamentos(ofx, arquivo)

# ============================================================
# 🔹 Extração dos lançamentos do OFX
# ============================================================
def _extrair_lancamentos(ofx, arquivo):
    lancamentos = []

    # tenta encontrar qualquer atributo que seja uma lista de transações
    transacoes = None
    possiveis = [
        getattr(ofx, "transactions", None),
        getattr(ofx, "transaction_list", None),
        getattr(getattr(ofx, "account", None), "transactions", None),
        getattr(getattr(ofx, "account", None), "statement", None) and getattr(ofx.account.statement, "transactions", None),
        getattr(getattr(ofx, "statement", None), "transactions", None),
        getattr(getattr(ofx, "bank_account", None), "statement", None) and getattr(ofx.bank_account.statement, "transactions", None),
    ]

    for lista in possiveis:
        if lista:
            transacoes = lista
            break

    if not transacoes:
        print("[DEBUG] Nenhuma lista de transações encontrada. Atributos disponíveis:", dir(ofx))
        if hasattr(ofx, "account"):
            print("[DEBUG] ofx.account:", dir(ofx.account))
        if hasattr(ofx.account, "statement"):
            print("[DEBUG] ofx.account.statement:", dir(ofx.account.statement))
        return []

    for t in transacoes:
        lanc = {
            "data": t.date,
            "valor": float(t.amount),
            "historico": t.memo,
            "banco": getattr(ofx.account.institution, "organization", "BANCO_DESCONHECIDO"),
            "arquivo_origem": getattr(arquivo, "name", "OFX_DESCONHECIDO"),
            "fitid": getattr(t, "id", None),
            # Sicredi pode usar REFNUM em vez de CHECKNUM
            "checknum": getattr(t, "checknum", None) or getattr(t, "refnum", None)
        }
        lanc["assinatura"] = gerar_assinatura(lanc)
        lancamentos.append(lanc)

    return lancamentos

# ============================================================
# 🔹 Verificação de duplicidade
# ============================================================
def existe_lancamento(lanc):
    # Verifica por fitid + banco + arquivo
    query = """
        SELECT COUNT(*) FROM lancamentos
        WHERE fitid = %s AND banco = %s AND arquivo_origem = %s
    """
    resultado = executar_query(query, (lanc["fitid"], lanc["banco"], lanc["arquivo_origem"]), fetch=True)
    if resultado[0][0] > 0:
        return True

    # Verifica por checknum/refnum + banco + valor + data
    query = """
        SELECT COUNT(*) FROM lancamentos
        WHERE checknum = %s AND banco = %s AND valor = %s AND data = %s
    """
    valor = Decimal(str(lanc["valor"])) if lanc["valor"] is not None else None
    data = lanc["data"].date() if hasattr(lanc["data"], "date") else lanc["data"]

    resultado = executar_query(query, (lanc["checknum"], lanc["banco"], valor, data), fetch=True)
    if resultado[0][0] > 0:
        return True

    # Verifica por assinatura + banco
    query = """
        SELECT COUNT(*) FROM lancamentos
        WHERE assinatura = %s AND banco = %s
    """
    resultado = executar_query(query, (lanc["assinatura"], lanc["banco"]), fetch=True)
    return resultado[0][0] > 0

# ============================================================
# 🔹 Inserção de lançamento (ignora duplicados)
# ============================================================
def salvar_lancamento(lanc):
    query = """
        INSERT INTO lancamentos (data, valor, historico, banco, arquivo_origem, fitid, checknum, assinatura)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (fitid, banco, arquivo_origem) DO NOTHING
    """
    executar_query(query, (
        lanc["data"], lanc["valor"], lanc["historico"], lanc["banco"],
        lanc["arquivo_origem"], lanc["fitid"], lanc["checknum"], lanc["assinatura"]
    ))

# ============================================================
# 🔹 Importação do arquivo OFX
# ============================================================
def importar_ofx(arquivo):
    lancamentos = ler_ofx(arquivo)

    inseridos, ignorados = 0, 0
    for lanc in lancamentos:
        if not existe_lancamento(lanc):
            salvar_lancamento(lanc)
            inseridos += 1
        else:
            ignorados += 1

    print(f"Arquivo {getattr(arquivo, 'name', 'OFX')} importado: {inseridos} novos, {ignorados} ignorados.")
    return inseridos, ignorados
