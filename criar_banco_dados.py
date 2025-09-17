import sqlite3

conexao = sqlite3.connect("estacionamento.db")
cursor = conexao.cursor()

cursor.execute(""" 
CREATE TABLE IF NOT EXISTS veiculos(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               placa TEXT UNIQUE,
               veiculos TEXT NOT NULL,
               hora_entrada TEXT NOT NULL,
               hora_saida TEXT,
               valor REAL
               )

""")

conexao.commit()
conexao.close()