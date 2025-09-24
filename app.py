import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages
from datetime import datetime
import re
app = Flask(__name__)
app.secret_key = "chave_secreta"


@app.route("/", methods=["GET", "POST"])
def registrar_entrada():

    if request.method == "POST":
        placa = request.form.get("placa", "").strip().upper()
        veiculos = request.form.get("veiculos", "")
        hora_entrada = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        placa = placa.strip().upper()
        padrao = re.compile(
            r"^(?:[A-Z]{3}-?[0-9]{4}|[A-Z]{3}[0-9][A-Z0-9][0-9]{2})$")

        if not placa:
            flash("Informe a placa do veículo!", "warning")
            return redirect(url_for("registrar_entrada"))

        elif not padrao.match(placa):
            flash("placa inválida!", "warning")
            return redirect(url_for("registrar_entrada"))

        else:
            try:
                with sqlite3.connect("estacionamento.db") as conexao:
                    cursor = conexao.cursor()
                    cursor.execute(
                        "SELECT 1 FROM veiculos WHERE placa = ?", (placa,)
                    )
                    if cursor.fetchone():
                        flash(f"A placa {placa} já está registrada!")
                    else:
                        cursor.execute(
                            "INSERT INTO veiculos (placa, veiculos, hora_entrada) VALUES (?, ?, ?)",
                            (placa, veiculos, hora_entrada))
                        flash(f"Veículo {placa} registrado ", "success")
                        return redirect(url_for("registrar_entrada"))

            except sqlite3.IntegrityError:
                flash("A placa {placa} já está registrada! (conflito)", "erro")
            except Exception as e:
                flash("Erro ao registrar: {e}", "erro")

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
    
    with sqlite3.connect("estacionamento.db") as conexao:
        cursor = conexao.cursor()
        vagas_totais = 50
        cursor.execute("SELECT COUNT(*) FROM veiculos")
        vagas_ocupadas = cursor.fetchone()[0]
        vagas_disponiveis = vagas_totais - vagas_ocupadas

        cursor.execute("SELECT SUM(valor) FROM historico")
        faturamento = cursor.fetchone()[0] or 0
        faturamento = float(faturamento)
    

    return render_template("index.html", registro=registro, resultado=None, mostrar_resultado=False,vagas_totais=vagas_totais,vagas_ocupadas=vagas_ocupadas,vagas_disponiveis=vagas_disponiveis,faturamento=faturamento)




@app.route("/buscar", methods=["GET", "POST"])
def buscar_placa():
    placa = request.form.get("placa_buscar", "").strip().upper()
    resultado = None
    mostrar_resultado = True

    if placa:
        with sqlite3.connect("estacionamento.db") as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                "SELECT placa, hora_entrada FROM veiculos WHERE placa = ?", (
                    placa,)
            )
            registro_busca = cursor.fetchone()
            if registro_busca:
                hora_entrada = datetime.strptime(
                    registro_busca[1], "%Y-%m-%d %H:%M:%S")
                agora = datetime.now()
                delta = agora - hora_entrada
                horas = delta.seconds // 3600
                minutos = (delta.seconds % 3600) // 60
                permanencia = f"{horas}h {minutos}min"
                valor = 12 + (horas * 8)
                resultado = {
                    "placa": registro_busca[0],
                    "entrada": hora_entrada.strftime("%H:%M"),
                    "agora": agora.strftime("%H:%M"),
                    "permanencia": permanencia,
                    "valor": float(valor)
                }
                

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

    with sqlite3.connect("estacionamento.db") as conexao:
        cursor = conexao.cursor()
        cursor.execute("SELECT SUM(valor) FROM historico")
        faturamento = cursor.fetchone()[0] or 0
        faturamento = float(faturamento)

    


    return render_template("index.html", registro=registro, resultado=resultado, mostrar_resultado=mostrar_resultado, faturamento=faturamento)

@app.route("/finalizar", methods=["POST"])
def finalizar():
    placa = request.form.get("placa_buscar")
    if placa:
        with sqlite3.connect('estacionamento.db') as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                "SELECT placa, veiculos, hora_entrada FROM veiculos where placa = ?", (
                    placa,)
            )
            registro = cursor.fetchone()

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
            

            cursor.execute(
                "INSERT INTO historico (placa, veiculos, hora_entrada, hora_saida, permanencia, valor) VALUES (?, ?, ?, ?, ?, ?)",
                (

                    registro[0],
                    registro[1],
                    registro[2],
                    hora_saida.strftime("%H:%M"),
                    permanencia,
                    valor
                ))

            cursor.execute(
                "DELETE FROM veiculos WHERE placa = ?", (placa,)
            )
            conexao.commit()

    return redirect(url_for("registrar_entrada"))



if __name__ == "__main__":
    app.run(debug=True)
