import re
from datetime import datetime
from modules.database import executar_query


class OFXParser:

    def __init__(self, texto):
        self.texto = texto.replace("\r", "").replace("\n", "")
        self.banco = self.detectar_banco()

    def detectar_banco(self):
        t = self.texto.upper()
        if "SANTANDER" in t:
            return "SANTANDER"
        if "ITAU" in t or "341" in t:
            return "ITAÚ"
        if "BANCO DO BRASIL" in t or "<BANKID>001" in t:
            return "BANCO DO BRASIL"
        if "SICREDI" in t or "<BANKID>748" in t:
            return "SICREDI"
        return "DESCONHECIDO"

    def extrair(self, tag):
        padrao = f"<{tag}>([^<]+)"
        return re.findall(padrao, self.texto)

    def parse(self):
        transacoes = []

        datas = self.extrair("DTPOSTED")
        valores = self.extrair("TRNAMT")
        memos = self.extrair("MEMO")

        for i in range(len(valores)):

            data = self.converter_data(datas[i]) if i < len(datas) else None
            valor = self.converter_valor(valores[i])
            memo = memos[i] if i < len(memos) else ""

            transacoes.append({
                "banco": self.banco,
                "data": str(data.date()) if data else None,
                "valor": valor,
                "historico": memo.strip(),
            })

        return transacoes

    def converter_data(self, d):
        d = d.split("[")[0].strip()
        if len(d) >= 14:
            return datetime.strptime(d[:14], "%Y%m%d%H%M%S")
        if len(d) == 8:
            return datetime.strptime(d, "%Y%m%d")
        return None

    def converter_valor(self, v):
        v = v.replace(",", ".")
        try:
            return float(v)
        except:
            return 0.0


def ler_ofx(arquivo):
    arquivo.seek(0)
    content = arquivo.read()

    if not content:
        print("[DEBUG] Arquivo vazio.")
        return []

    for enc in ["utf-8", "latin-1", "cp1252"]:
        try:
            text = content.decode(enc)

            parser = OFXParser(text)
            lancamentos = parser.parse()

            for l in lancamentos:
                l["arquivo_origem"] = getattr(arquivo, "name", "OFX")

            print(f"[DEBUG] Banco detectado: {parser.banco}")
            print(f"[DEBUG] Lançamentos encontrados: {len(lancamentos)}")

            return lancamentos

        except Exception as e:
            print(f"[DEBUG] Falha encoding {enc}: {e}")
            continue

    return []


def existe_lancamento(lanc):
    query = """
        SELECT COUNT(*) FROM lancamentos
        WHERE data = %s AND valor = %s AND historico = %s
    """
    resultado = executar_query(
        query,
        (lanc["data"], lanc["valor"], lanc["historico"]),
        fetch=True
    )
    return resultado and resultado[0][0] > 0


def salvar_lancamento(lanc):
    query = """
        INSERT INTO lancamentos (data, valor, historico, banco, arquivo_origem)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (data, valor, historico) DO NOTHING
    """
    executar_query(query, (
        lanc["data"],
        lanc["valor"],
        lanc["historico"],
        lanc["banco"],
        lanc["arquivo_origem"]
    ))


def importar_ofx(arquivo):
    lancamentos = ler_ofx(arquivo)

    if not lancamentos:
        print("[DEBUG] Nenhum lançamento encontrado.")
        return 0, 0

    inseridos = 0
    ignorados = 0

    for lanc in lancamentos:
        if not existe_lancamento(lanc):
            salvar_lancamento(lanc)
            inseridos += 1
        else:
            ignorados += 1

    return inseridos, ignorados
