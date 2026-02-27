import io
import re
from ofxparse import OfxParser
from modules.database import executar_query
from datetime import datetime

# ============================================================
# 🔹 Parser manual para Itaú (OFX SGML)
# ============================================================
def ler_ofx_itau(texto, arquivo):
    lancamentos = []
    transacoes = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", texto, re.DOTALL)

    for trn in transacoes:
        memo = re.search(r"<MEMO>(.*?)\n", trn)
        valor = re.search(r"<TRNAMT>(.*?)\n", trn)
        data = re.search(r"<DTPOSTED>(.*?)\n", trn)

        data_valor = None
        if data:
            raw = data.group(1).strip()
            try:
                data_valor = datetime.strptime(raw[:8], "%Y%m%d").date()
            except Exception:
                data_valor = None

        lanc = {
            "historico": memo.group(1).strip() if memo else None,
            "valor": float(valor.group(1)) if valor else 0.0,
            "data": str(data_valor) if data_valor else None,
            "banco": "ITAÚ",
            "arquivo_origem": getattr(arquivo, "name", "OFX_ITAU"),
        }
        lancamentos.append(lanc)

    return lancamentos


# ============================================================
# 🔹 Parser manual para Banco do Brasil (OFX SGML)
# ============================================================
def ler_ofx_bb(texto, arquivo):
    lancamentos = []
    transacoes = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", texto, re.DOTALL)

    for trn in transacoes:
        memo = re.search(r"<MEMO>(.*?)\n", trn)
        valor = re.search(r"<TRNAMT>(.*?)\n", trn)
        data = re.search(r"<DTPOSTED>(.*?)\n", trn)

        data_valor = None
        if data:
            raw = data.group(1).strip()
            try:
                data_valor = datetime.strptime(raw[:8], "%Y%m%d").date()
            except Exception:
                data_valor = None

        lanc = {
            "historico": memo.group(1).strip() if memo else None,
            "valor": float(valor.group(1)) if valor else 0.0,
            "data": str(data_valor) if data_valor else None,
            "banco": "BANCO DO BRASIL",
            "arquivo_origem": getattr(arquivo, "name", "OFX_BB"),
        }
        lancamentos.append(lanc)

    return lancamentos


# ============================================================
# 🔹 Parser manual para Sicredi (OFX SGML)
# ============================================================
def ler_ofx_sicredi(texto, arquivo):
    lancamentos = []
    transacoes = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", texto, re.DOTALL | re.IGNORECASE)

    for trn in transacoes:
        memo = re.search(r"<MEMO>(.*?)</MEMO>", trn, re.DOTALL)
        valor = re.search(r"<TRNAMT>(.*?)</TRNAMT>", trn, re.DOTALL)
        data = re.search(r"<DTPOSTED>(.*?)</DTPOSTED>", trn, re.DOTALL)

        data_valor = None
        if data:
            raw = data.group(1).strip()
            try:
                data_valor = datetime.strptime(raw[:8], "%Y%m%d").date()
            except Exception:
                data_valor = None

        lanc = {
            "historico": memo.group(1).strip() if memo else None,
            "valor": float(valor.group(1)) if valor else 0.0,
            "data": str(data_valor) if data_valor else None,
            "banco": "SICREDI",
            "arquivo_origem": getattr(arquivo, "name", "OFX_SICREDI"),
        }
        lancamentos.append(lanc)

    return lancamentos

# ============================================================
# 🔹 Parser manual para Santander (OFX SGML)
# ============================================================
def ler_ofx_santander(texto, arquivo):
    lancamentos = []
    transacoes = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", texto, re.DOTALL | re.IGNORECASE)

    for trn in transacoes:
        memo = re.search(r"<MEMO>([^<]*)", trn)   # pega até o próximo <
        valor = re.search(r"<TRNAMT>([^<]*)", trn)
        data = re.search(r"<DTPOSTED>([^<]*)", trn)

        # Converte data
        data_valor = None
        if data:
            raw = data.group(1).strip()
            try:
                data_valor = datetime.strptime(raw[:8], "%Y%m%d").date()
            except Exception:
                data_valor = None

        # Converte valor (vírgula para ponto)
        valor_num = 0.0
        if valor:
            raw_valor = valor.group(1).strip().replace(",", ".")
            try:
                valor_num = float(raw_valor)
            except Exception:
                valor_num = 0.0

        lanc = {
            "historico": memo.group(1).strip() if memo else None,
            "valor": valor_num,
            "data": str(data_valor) if data_valor else None,
            "banco": "SANTANDER",
            "arquivo_origem": getattr(arquivo, "name", "OFX_SANTANDER"),
        }
        lancamentos.append(lanc)

    return lancamentos

# ============================================================
# 🔹 Parser universal (usa OfxParser)
# ============================================================
def ler_ofx_universal(texto, arquivo):
    try:
        ofx = OfxParser.parse(io.StringIO(texto))
        return _extrair_lancamentos(ofx, arquivo)
    except Exception as e:
        print(f"[DEBUG] Falha no parser universal: {e}")
        return []


# ============================================================
# 🔹 Extração dos lançamentos do OFX (genérico)
# ============================================================
def _extrair_lancamentos(ofx, arquivo):
    lancamentos = []
    transacoes = getattr(ofx, "transactions", None) or getattr(ofx.account, "transactions", None)

    if not transacoes:
        print("[DEBUG] Nenhuma lista de transações encontrada.")
        return []

    for t in transacoes:
        lanc = {
            "data": str(t.date.date()) if hasattr(t.date, "date") else str(t.date),
            "valor": float(t.amount),
            "historico": t.memo,
            "banco": getattr(ofx.account.institution, "organization", "BANCO_DESCONHECIDO"),
            "arquivo_origem": getattr(arquivo, "name", "OFX_DESCONHECIDO"),
        }
        lancamentos.append(lanc)

    return lancamentos


# ============================================================
# 🔹 Leitura do arquivo OFX (roteador de parsers)
# ============================================================
def ler_ofx(arquivo):
    arquivo.seek(0)
    content = arquivo.read()
    if not content:
        print("[DEBUG] Arquivo vazio ao tentar ler.")
        return []

    encodings = ["utf-8", "latin-1", "cp1252"]

    for enc in encodings:
        try:
            text = content.decode(enc)

            if "OFXHEADER" in text and "DATA:OFXSGML" in text:
                if "ITAÚ" in text or "ITAU" in text:
                    return ler_ofx_itau(text, arquivo)
                elif "BANCO DO BRASIL" in text or "BB" in text:
                    return ler_ofx_bb(text, arquivo)
                elif "SICREDI" in text or "COOP DE CRED" in text:
                    return ler_ofx_sicredi(text, arquivo)
                elif "SANTANDER" in text:
                    return ler_ofx_santander(text, arquivo)
                else:
                    print("[DEBUG] SGML não identificado, usando parser universal.")
                    return ler_ofx_universal(text, arquivo)

            # Se não for SGML, usa universal direto
            return ler_ofx_universal(text, arquivo)

        except Exception as e:
            print(f"[DEBUG] Falha ao parsear com encoding {enc}: {e}")
            continue

    print("[DEBUG] Não foi possível decodificar o arquivo.")
    return []


# ============================================================
# 🔹 Verificação de duplicidade (data + valor + historico)
# ============================================================
def existe_lancamento(lanc):
    query = """
        SELECT COUNT(*) FROM lancamentos
        WHERE data = %s AND valor = %s AND historico = %s
    """
    resultado = executar_query(
        query,
        (lanc["data"], float(lanc["valor"]) if lanc["valor"] is not None else None, lanc["historico"]),
        fetch=True
    )
    return resultado and resultado[0][0] > 0


# ============================================================
# 🔹 Inserção de lançamento
# ============================================================
def salvar_lancamento(lanc):
    query = """
        INSERT INTO lancamentos (data, valor, historico, banco, arquivo_origem)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (data, valor, historico) DO NOTHING
    """
    executar_query(query, (
        str(lanc["data"]),
        float(lanc["valor"]) if lanc["valor"] is not None else None,
        lanc["historico"],
        lanc["banco"],
        lanc["arquivo_origem"]
    ))


# ============================================================
# 🔹 Importação do arquivo OFX
# ============================================================
def importar_ofx(arquivo):
    arquivo.seek(0)
    lancamentos = ler_ofx(arquivo)

    if not lancamentos:
        print("[DEBUG] Nenhum lançamento encontrado no arquivo.")
        return 0, 0

    inseridos = 0
    ignorados = 0

    for lanc in lancamentos:
        if not existe_lancamento(lanc):
            salvar_lancamento(lanc)
            inseridos += 1
        else:
            ignorados += 1

    print(f"Arquivo {getattr(arquivo, 'name', 'OFX')} importado: {inseridos} novos, {ignorados} ignorados.")
    return inseridos, ignorados





