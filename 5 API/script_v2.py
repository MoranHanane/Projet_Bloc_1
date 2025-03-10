import os
from flask import Flask, jsonify, request
import mysql.connector
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()

# Configuration de la connexion MySQL
db_config = {
'user':os.getenv("DB_USER"),
'password': os.getenv("DB_PASSWORD"),
'host':'localhost',
'database':'Revues_numerisees'
}

# Fonction pour se connecter à la base de données
def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except mysql.connector.Error as err:
        return err

# Exemple d'une route pour récupérer des données d'une table "users"
@app.route("/revues", methods=['GET'])
def get_revues():
    print("####  Acces ok route")
    date_start = int(request.args.get('date_start'))
    date_end = int(request.args.get('date_end'))

    try:
        # Connexion à la base de données

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)  # pour récupérer des résultats sous forme de dictionnaire
        
        query = "SELECT * FROM Revue WHERE Date_d_edition"

        if date_start and date_end:
            query += f" BETWEEN {date_start} AND {date_end}"
        else:
            return "Error, please provide dates"

        query += " LIMIT 50;"

        cursor.execute(query)
        results = cursor.fetchall()

        print(results)

        cursor.close()
        conn.close()

        return jsonify(results)
    except Exception as e:
        print(e)
        return e

if __name__ == '__main__':
    app.run(debug=True)