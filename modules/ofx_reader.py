import hashlib
import io
import re
from ofxparse import OfxParser
from modules.database import executar_query
from datetime import datetime, date

# ============================================================
# 🔹 Geração de assinatura única para cada lançamento
# ============================================================
def gerar_assinatura(lanc):
    base = f"{lanc['data']}{lanc['valor']}{lanc['historico']}{lanc['banco']}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()

# ============================================================
# 🔹 Parser manual para Itaú (OFX SGML)
# ============================================================
def ler_ofx_itau(texto, arquivo):
    lancamentos = []
    transacoes = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", texto, re.DOTALL)
    for trn in transacoes:
        fitid = re.search(r"<FITID>(.*?)\n", trn)
        checknum = re.search(r"<CHECKNUM>(.*?)\n", trn)
        memo = re.search(r"<MEMO>(.*?)\n", trn)
        valor = re.search(r"<TRNAMT>(.*?)\n", trn)
        data = re.search(r"<DTPOSTED>(.*?)\n", trn)

        # Converte data do formato Itaú (YYYYMMDDHHMMSS[-TZ]) para datetime.date
        data_valor = None
        if data:
            raw = data.group(1).strip()
            try:
                data_valor = datetime.strptime(raw[:8], "%Y%m%d").date()
            except Exception:
                data_valor = None

        lanc = {
            "fitid": fitid.group(1).strip() if fitid else None,
            "checknum": checknum.group(1).strip() if checknum else None,
            "historico": memo.group(1).strip() if memo else None,
            "valor": float(valor.group(1)) if valor else 0.0,
            "data": data_valor,
            "banco": "ITAÚ",
            "arquivo_origem": getattr(arquivo, "name", "OFX_ITAU"),
        }
        lanc["assinatura"] = gerar_assinatura(lanc)
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

def _parse_ofx(arquivo):
    ofx = OfxParser.parse(arquivo)
    return _extrair_lancamentos(ofx, arquivo)

# ============================================================
# 🔹 Extração dos lançamentos do OFX (Banco do Brasil, Sicredi)
# ============================================================
def existe_lancamento(lanc):
    # Verifica por fitid + banco + arquivo
    if lanc["fitid"]:
        query = """
            SELECT COUNT(*) FROM lancamentos
            WHERE fitid = %s AND banco = %s AND arquivo_origem = %s
        """
        resultado = executar_query(query, (lanc["fitid"], lanc["banco"], lanc["arquivo_origem"]), fetch=True)
        if resultado[0][0] > 0:
            return True

    # Verifica por checknum/refnum + banco + valor + data
    if lanc["checknum"] and lanc["data"]:
        query = """
            SELECT COUNT(*) FROM lancamentos
            WHERE checknum = %s AND banco = %s AND valor = %s AND data = %s
        """
        valor = float(lanc["valor"]) if lanc["valor"] is not None else None
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
# 🔹 Verificação de duplicidade
# ============================================================


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
        lanc["data"],
        float(lanc["valor"]) if lanc["valor"] is not None else None,
        lanc["historico"],
        lanc["banco"],
        lanc["arquivo_origem"],
        lanc["fitid"],
        lanc["checknum"],
        lanc["assinatura"]
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



