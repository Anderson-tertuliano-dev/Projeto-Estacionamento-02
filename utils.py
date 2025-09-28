import sqlite3
from datetime import datetime
import qrcode
import base64
from io import BytesIO

def get_info_estacionamento():
    with sqlite3.connect("estacionamento.db") as conexao:
        cursor = conexao.cursor()
        cursor.execute("""
            SELECT placa, veiculos, hora_entrada, hora_saida, permanencia, valor
            FROM historico 
            WHERE hora_saida IS NOT NULL
            ORDER BY id DESC 
            LIMIT 10
        """)
        registro = cursor.fetchall()

        vagas_totais = 50
        cursor.execute("SELECT COUNT(*) FROM veiculos")
        vagas_ocupadas = cursor.fetchone()[0]
        vagas_disponiveis = vagas_totais - vagas_ocupadas

        cursor.execute("SELECT SUM(valor) FROM historico")
        faturamento = cursor.fetchone()[0] or 0
        faturamento = float(faturamento)

    return registro, vagas_totais, vagas_ocupadas, vagas_disponiveis, faturamento


def calcular_valor_e_permanencia(registro):
    if registro:
        hora_entrada = datetime.strptime(
            registro[2], "%Y-%m-%d %H:%M:%S")
        hora_saida = datetime.now()
        delta = hora_saida - hora_entrada
        total_segundos = delta.total_seconds()
        horas = int(total_segundos // 3600)
        minutos = int((total_segundos % 3600) // 60)
        if horas:
            permanencia = f"{horas} h {minutos} min"
        else:
            permanencia = f"{minutos} min"

        total_horas_inteiras = int(total_segundos // 3600)
        if total_segundos % 3600 > 0:
            total_horas_inteiras += 1

        tipo_veiculo = registro[1].lower()
        valor = 0
        if tipo_veiculo == "moto":
            valor = total_horas_inteiras * 5
        else:
            if total_horas_inteiras <= 1:
                valor = 12
            elif total_horas_inteiras < 24:
                if hora_entrada.hour < 6 or hora_saida.hour > 18:
                    valor = 30
                else:
                    valor = 12 + (total_horas_inteiras - 1) * 8
            else:
                dias = total_horas_inteiras // 24
                horas_restantes = total_horas_inteiras % 24
                valor = dias * 55
                if horas_restantes <= 1:
                    valor += 12
                elif horas_restantes > 1:
                    valor += 12 + (horas_restantes - 1) * 8
                if horas_restantes >= 24:
                    valor = (dias + 1) * 55
    return  float(valor), permanencia, hora_entrada, hora_saida

def ticket_entrada(placa):
    # Buscar o veículo no banco
    with sqlite3.connect("estacionamento.db") as conexao:
        cursor = conexao.cursor()
        cursor.execute("SELECT placa, veiculos, hora_entrada FROM veiculos WHERE placa = ?", (placa,))
        registro = cursor.fetchone()
    
    if not registro:
        return None

    placa, tipo_veiculo, hora_entrada = registro

    # Gerar QR Code com a placa
    qr = qrcode.QRCode(box_size=5, border=2)
    qr.add_data(placa)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Converter imagem para base64 para enviar ao HTML
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode("ascii")
    qr_code_data = f"data:image/png;base64,{img_str}"

    return placa, tipo_veiculo, hora_entrada ,qr_code_data

def ticket_saida(placa):
    with sqlite3.connect("estacionamento.db") as conexao:
        cursor = conexao.cursor()
        cursor.execute("SELECT placa, veiculos, hora_entrada, hora_saida, permanencia, valor FROM historico WHERE placa = ?",(placa,))
        registro = cursor.fetchone()

        if not registro:
            return None
        
        placa, tipo_veiculo, hora_entrada, hora_saida, permanencia, valor = registro

        return placa, tipo_veiculo, hora_entrada, hora_saida, permanencia, valor

