import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages
from datetime import datetime
import re
from utils import get_info_estacionamento, calcular_valor_e_permanencia, ticket_entrada, ticket_saida
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
                        return redirect(url_for("exibir_ticket", placa=placa))

            except sqlite3.IntegrityError:
                flash("A placa {placa} já está registrada! (conflito)", "erro")
            except Exception as e:
                flash("Erro ao registrar: {e}", "erro")

    registro, vagas_totais, vagas_ocupadas, vagas_disponiveis, faturamento = get_info_estacionamento()

    return render_template("index.html", registro=registro, resultado=None, mostrar_resultado=False, vagas_totais=vagas_totais, vagas_ocupadas=vagas_ocupadas, vagas_disponiveis=vagas_disponiveis, faturamento=faturamento)


@app.route("/buscar", methods=["GET", "POST"])
def buscar_placa():
    placa = request.form.get("placa_buscar", "").strip().upper()
    resultado = None
    msg_busca = None

    if placa:
        with sqlite3.connect("estacionamento.db") as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                "SELECT placa, veiculos, hora_entrada FROM veiculos WHERE placa = ?", (
                    placa,)
            )

            registro_busca = cursor.fetchone()
            if registro_busca:
                agora = datetime.now()
                valor, permanencia, hora_entrada, hora_saida = calcular_valor_e_permanencia(
                    registro_busca)
                resultado = {
                    "placa": registro_busca[0],
                    "entrada": hora_entrada.strftime("%H:%M"),
                    "agora": agora.strftime("%H:%M"),
                    "permanencia": permanencia,
                    "valor": float(valor)
                }
            else:
                msg_busca =f"Nenhum veículo encontrado para a placa <span style='color:red'>{placa}</span>"
    else:
        msg_busca="Informe a placa do veículo!"
        

    registro, vagas_totais, vagas_ocupadas, vagas_disponiveis, faturamento = get_info_estacionamento()

    return render_template("index.html", registro=registro, resultado=resultado, msg_busca=msg_busca, mostrar_resultado=True, vagas_totais=vagas_totais, vagas_ocupadas=vagas_ocupadas, vagas_disponiveis=vagas_disponiveis, faturamento=faturamento)


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
                valor, permanencia, hora_entrada, hora_saida = calcular_valor_e_permanencia(
                    registro)

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
            return redirect(url_for("exibir_ticket_saida", placa=placa))
            

    return redirect(url_for("registrar_entrada"))

@app.route("/ticket/<placa>")
def exibir_ticket(placa):
    placa, tipo_veiculo, hora_entrada, qr_code = ticket_entrada(placa)
    if not placa:
        return "Veículo não encontrado", 404
    return render_template("ticket.html", placa=placa, tipo_veiculo=tipo_veiculo, hora_entrada=hora_entrada, qr_code=qr_code)

@app.route("/ticket_saida/<placa>")
def exibir_ticket_saida(placa):
    placa, tipo_veiculo, hora_entrada, hora_saida, permanencia, valor = ticket_saida(placa)
    if not placa:
        return None
    return render_template("ticket_saida.html", placa=placa, tipo_veiculo=tipo_veiculo, hora_entrada=hora_entrada, hora_saida=hora_saida, permanencia=permanencia, valor=valor)

if __name__ == "__main__":
    app.run(debug=True)
