def moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def percentual(valor):
    return f"{valor:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")

def data_br(data):
    return data.strftime("%d/%m/%Y")