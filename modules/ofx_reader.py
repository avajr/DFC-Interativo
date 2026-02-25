import hashlib
import io
from ofxparse import OfxParser
from modules.database import executar_query

def gerar_assinatura(lanc):
    base = f"{lanc['data']}{lanc['valor']}{lanc['historico']}{lanc['banco']}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()

def ler_ofx(arquivo):
    try:
        return _parse_ofx(arquivo)
    except UnicodeDecodeError:
        content = arquivo.read()
        encodings = ["utf-8", "latin-1", "cp1252"]
        for enc in encodings:
            try:
                text = content.decode(enc)
                ofx = OfxParser.parse(io.StringIO(text))
                return _extrair_lancamentos(ofx, arquivo)
            except Exception:
                continue
        return []

def _parse_ofx(arquivo):
    ofx = OfxParser.parse(arquivo)
    return _extrair_lancamentos(ofx, arquivo)

def _extrair_lancamentos(ofx, arquivo):
    lancamentos = []
    caminhos = [
        "account.statement.transactions",
        "account.transactions",
        "statement.transactions",
        "bank.account.statement.transactions"
    ]

    transacoes = None
    for caminho in caminhos:
        try:
            obj = ofx
            for parte in caminho.split("."):
                obj = getattr(obj, parte)
            transacoes = obj
            break
        except:
            pass

    if not transacoes:
        return []

    for t in transacoes:
        lanc = {
            "data": t.date,
            "valor": float(t.amount),
            "historico": t.memo,
            "banco": getattr(ofx.account.institution, "organization", "BANCO_DESCONHECIDO"),
            "arquivo_origem": getattr(arquivo, "name", "OFX_DESCONHECIDO"),
            "fitid": getattr(t, "id", None),
            "checknum": getattr(t, "checknum", None)
        }
        lanc["assinatura"] = gerar_assinatura(lanc)
        lancamentos.append(lanc)

    return lancamentos

def existe_lancamento(lanc):
    query = """
        SELECT COUNT(*) FROM lancamentos
        WHERE fitid = %s AND checknum = %s AND banco = %s AND arquivo_origem = %s
    """
    resultado = executar_query(query, (lanc["fitid"], lanc["checknum"], lanc["banco"], lanc["arquivo_origem"]), fetch=True)
    if resultado[0][0] > 0:
        return True

    query = """
        SELECT COUNT(*) FROM lancamentos
        WHERE assinatura = %s AND banco = %s
    """
    resultado = executar_query(query, (lanc["assinatura"], lanc["banco"]), fetch=True)
    return resultado[0][0] > 0

def arquivo_ja_importado(lancamentos):
    for lanc in lancamentos:
        if not existe_lancamento(lanc):
            return False
    return True

def salvar_lancamento(lanc):
    query = """
        INSERT INTO lancamentos (data, valor, historico, banco, arquivo_origem, fitid, checknum, assinatura)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """
    executar_query(query, (
        lanc["data"], lanc["valor"], lanc["historico"], lanc["banco"],
        lanc["arquivo_origem"], lanc["fitid"], lanc["checknum"], lanc["assinatura"]
    ))

def importar_ofx(arquivo):
    lancamentos = ler_ofx(arquivo)

    if arquivo_ja_importado(lancamentos):
        print(f"Arquivo {getattr(arquivo, 'name', 'OFX')} já foi importado, ignorando...")
        return 0, len(lancamentos)

    inseridos, ignorados = 0, 0
    for lanc in lancamentos:
        if not existe_lancamento(lanc):
            salvar_lancamento(lanc)
            inseridos += 1
        else:
            ignorados += 1

    return inseridos, ignorados
