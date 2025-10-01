import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages, session
from datetime import datetime
import re
from utils import get_info_estacionamento, calcular_valor_e_permanencia, ticket_entrada, ticket_saida

# Cria a aplicação Flask
app = Flask(__name__)
# Necessária para usar 'session' e 'flash' (cookies seguros)
app.secret_key = "chave_secreta"


@app.route("/", methods=["GET", "POST"])
def registrar_entrada():
    """
    Página inicial: registra a entrada de veículos no estacionamento.
    """

    if request.method == "POST":
        # Captura dados do formulário
        placa = request.form.get("placa", "").strip().upper()
        veiculos = request.form.get("veiculos", "")
        hora_entrada = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        placa = placa.strip().upper()
        # Regex para validar formato da placa (padrão antigo e Mercosul)
        padrao = re.compile(
            r"^(?:[A-Z]{3}-?[0-9]{4}|[A-Z]{3}[0-9][A-Z0-9][0-9]{2})$")

        # Caso não tenha placa
        if not placa:
            flash("Informe a placa do veículo!", "warning")
            return redirect(url_for("registrar_entrada"))

        # Caso placa não corresponda ao formato válido
        elif not padrao.match(placa):
            flash("placa inválida!", "warning")
            return redirect(url_for("registrar_entrada"))

        else:
            try:
                with sqlite3.connect("estacionamento.db") as conexao:
                    cursor = conexao.cursor()
                    # Verifica se a placa já está registrada
                    cursor.execute(
                        "SELECT 1 FROM veiculos WHERE placa = ?", (placa,)
                    )
                    if cursor.fetchone():
                        flash(f"A placa {placa} já está registrada!")

                    else:
                        # Insere novo veículo no banco
                        cursor.execute(
                            "INSERT INTO veiculos (placa, veiculos, hora_entrada) VALUES (?, ?, ?)",
                            (placa, veiculos, hora_entrada))
                        flash(f"Veículo {placa} registrado ", "success")

                        # Redireciona para a página de ticket de entrada
                        return redirect(url_for("exibir_ticket", placa=placa))

            except sqlite3.IntegrityError:
                flash("A placa {placa} já está registrada! (conflito)", "erro")
            except Exception as e:
                flash("Erro ao registrar: {e}", "erro")
    # Busca informações gerais (ocupação, vagas, faturamento etc.)
    registro, vagas_totais, vagas_ocupadas, vagas_disponiveis, faturamento = get_info_estacionamento()

    return render_template("index.html", registro=registro, resultado=None, mostrar_resultado=False, vagas_totais=vagas_totais, vagas_ocupadas=vagas_ocupadas, vagas_disponiveis=vagas_disponiveis, faturamento=faturamento)


@app.route("/buscar", methods=["GET", "POST"])
def buscar_placa():
    """
    Permite buscar um veículo pela placa para verificar tempo de permanência e valor até o momento.
    """

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
                # Calcula valor e tempo de permanência
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
                msg_busca = f"Nenhum veículo encontrado para a placa <span style='color:red'>{placa}</span>"
    else:
        msg_busca = f"Informe a placa do veículo!"

    # Recupera mensagem de finalização se existir (vinda da rota /finalizar)
    msg_finalizar = session.pop("msg_finalizar", None)

    registro, vagas_totais, vagas_ocupadas, vagas_disponiveis, faturamento = get_info_estacionamento()

    return render_template("index.html", registro=registro, resultado=resultado, msg_busca=msg_busca,
                           msg_finalizar=msg_finalizar,
                           mostrar_resultado=True, vagas_totais=vagas_totais, vagas_ocupadas=vagas_ocupadas, vagas_disponiveis=vagas_disponiveis, faturamento=faturamento)


@app.route("/finalizar", methods=["POST"])
def finalizar():
    """
    Finaliza o estacionamento de um veículo:
    - Calcula tempo e valor
    - Move o registro para o histórico
    - Remove da tabela 'veiculos'
    """

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
            # Grava no histórico
            cursor.execute(
                "INSERT INTO historico (placa, veiculos, hora_entrada, hora_saida, permanencia, valor) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    registro[0],
                    registro[1],
                    registro[2],
                    hora_saida.strftime("%Y-%m-%d %H:%M:%S"),
                    permanencia,
                    valor
                ))

            # Remove da tabela principal
            cursor.execute(
                "DELETE FROM veiculos WHERE placa = ?", (placa,)
            )

            # Mensagem para ser exibida na tela de busca
            session["msg_finalizar"] = f"Veículo {placa} finalizado com sucesso!"

            # Redireciona para o ticket de saída
            return redirect(url_for("exibir_ticket_saida", placa=placa))

    return redirect(url_for("registrar_entrada"))


@app.route("/ticket/<placa>")
def exibir_ticket(placa):
    """
    Exibe o ticket de entrada com QR code.
    """

    placa, tipo_veiculo, hora_entrada, qr_code = ticket_entrada(placa)
    hora_entrada_formatada = datetime.strptime(hora_entrada, "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S %d/%m/%Y")
    if not placa:
        return None
    return render_template("ticket.html", placa=placa, tipo_veiculo=tipo_veiculo, hora_entrada=hora_entrada_formatada, qr_code=qr_code)


@app.route("/ticket_saida/<placa>")
def exibir_ticket_saida(placa):
    """
    Exibe o ticket de saída com resumo da permanência e valor.
    """
    placa, tipo_veiculo, hora_entrada, hora_saida, permanencia, valor = ticket_saida(
        placa)
    hora_entrada_formatada = datetime.strptime(hora_entrada, "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S %d/%m/%Y")
    hora_saida_formatada = datetime.strptime(hora_saida, "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S %d/%m/%Y")
    

    if not placa:
        return None
    return render_template("ticket_saida.html", placa=placa, tipo_veiculo=tipo_veiculo, hora_entrada=hora_entrada_formatada, hora_saida=hora_saida_formatada, permanencia=permanencia, valor=valor)


# ---------------- MAIN ----------------
if __name__ == "__main__":
    app.run(debug=True)     # Executa a aplicação
