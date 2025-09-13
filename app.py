import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def registrar_entrada():
    conexao = sqlite3.connect("estacionamento.db")
    cursor = conexao.cursor()

    if request.method == "POST":
        placa = request.form.get("placa","").strip()
        veiculos = request.form.get("veiculos", "")
        hora_entrada = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


        cursor.execute(
        "INSERT INTO veiculos (placa, veiculos, hora_entrada) VALUES (?, ?, ?)",
        (placa, veiculos, hora_entrada))
        conexao.commit()
        conexao.close()
        print(f"✅ Veículo {placa} registrado às {hora_entrada}")

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)