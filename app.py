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
        padrao = re.compile(r"^(?:[A-Z]{3}-?[0-9]{4}|[A-Z]{3}[0-9][A-Z0-9][0-9]{2})$")
        
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
                flash ("Erro ao registrar: {e}", "erro")
    return render_template("index.html")

@app.route("/buscar", methods=["GET", "POST"])
def buscar_placa():
    placa = request.form.get("placa_buscar", "").strip().upper()
    resultado = None
    monstrar_resultado = False

    if placa:
        with sqlite3.connect("estacionamento.db") as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                "SELECT placa, hora_entrada FROM veiculos WHERE placa = ?", (placa,)
            )
            registro = cursor.fetchone()
            if registro:
                hora_entrada = datetime.strptime(registro[1], "%Y-%m-%d %H:%M:%S")
                agora = datetime.now()
                delta = agora - hora_entrada
                horas = delta.seconds // 3600
                minutos = (delta.seconds % 3600) // 60
                permanencia = f"{horas}h {minutos}min"
                valor = 12 +(horas * 8)
                resultado = {
                    "placa": registro[0],
                    "entrada": hora_entrada.strftime("%H:%M"),
                    "agora" : agora.strftime("%H:%M"),
                    "permanencia" : permanencia,
                    "valor": f"R$ {valor:.2f}"
                }
           
    
        monstrar_resultado = True
                
    return render_template("index.html", resultado=resultado, monstrar_resultado=monstrar_resultado)

@app.route("/finalizar", methods=["POST"])
def finalizar():
    placa = request.form.get("placa_buscar")
    if placa:
        with sqlite3.connect('estacionamento.db') as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                "DELETE FROM veiculos WHERE placa = ?", (placa,)
            )
            conexao.commit()
            print(f"DELETE executado, linhas afetadas: {cursor.rowcount}")
    return redirect(url_for("registrar_entrada"))

if __name__ == "__main__":
    app.run(debug=True)
