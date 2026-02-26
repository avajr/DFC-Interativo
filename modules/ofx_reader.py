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
# 🔹 Leitura do arquivo OFX (detecta Itaú vs outros bancos)
# ============================================================
def ler_ofx(arquivo):
    content = arquivo.read()
    encodings = ["utf-8", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            text = content.decode(enc)
            if "OFXHEADER" in text and "DATA:OFXSGML" in text:
                print("[DEBUG] Detectado arquivo SGML (Itaú). Usando parser manual.")
                return ler_ofx_itau(text, arquivo)
            else:
                ofx = OfxParser.parse(io.StringIO(text))
                return _extrair_lancamentos(ofx, arquivo)
        except Exception as e:
            print("[DEBUG] Falha ao parsear com encoding", enc, "erro:", e)
            continue
    return []

# ============================================================
# 🔹 Extração dos lançamentos do OFX (Santander, BB, Sicredi)
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
# 🔹 Verificação de duplicidade (data + valor + historico)
# ============================================================
def existe_lancamento(lanc):
    query = """
        SELECT COUNT(*) FROM lancamentos
        WHERE data = %s AND valor = %s AND historico = %s
    """
    resultado = executar_query(query, (
        lanc["data"],
        float(lanc["valor"]) if lanc["valor"] is not None else None,
        lanc["historico"]
    ), fetch=True)
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
        lanc["data"],
        float(lanc["valor"]) if lanc["valor"] is not None else None,
        lanc["historico"],
        lanc["banco"],
        lanc["arquivo_origem"]
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
