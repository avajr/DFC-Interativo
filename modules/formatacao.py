def moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def percentual(valor):
    return f"{valor:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")

def data_br(data):

    return data.strftime("%d/%m/%Y")

def data_br(data):
    import pandas as pd
    if pd.isnull(data) or data is None:
        return ""
    try:
        return pd.to_datetime(data).strftime("%d/%m/%Y")
    except Exception:
        return str(data)
