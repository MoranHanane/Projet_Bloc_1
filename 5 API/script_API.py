import os
import jwt
import datetime
import nest_asyncio
from fastapi import FastAPI, Query, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import mysql.connector
from pymongo import MongoClient
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

nest_asyncio.apply()
load_dotenv()

app = FastAPI()

# Configuration de la sécurité
security = HTTPBearer()

# Modèle pour l'authentification
class TokenRequest(BaseModel):
    password: str
    duration: Optional[int] = 3600  # Durée en secondes (1h par défaut)

# Configuration des variables d'environnement
SECRET_KEY = os.getenv("SECRET_KEY")
API_PASSWORD = os.getenv("API_PASSWORD")
USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION")

def create_jwt(duration: int) -> str:
    """
    Fonction qui permet de générer un token JWT
    
    :param duration: Durée de validité du token en secondes
    :return: Token JWT encodé
    """
    expiration = datetime.datetime.utcnow() + datetime.timedelta(seconds=duration)
    return jwt.encode(
        {"exp": expiration},
        SECRET_KEY,
        algorithm="HS256"
    )

@app.post("/token")
def generate_token(request: TokenRequest):
    """
    Route qui permet de générer un token pour un utilisateur qui saisit son mot de passe
    
    :param request: Objet TokenRequest contenant le mot de passe et la durée
    :return: Token JWT
    """
    if request.password != API_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    token = create_jwt(request.duration)
    return {"token": token}

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Fonction qui permet de vérifier le token JWT
    
    :param credentials: Credentials fournis via le bearer token
    :return: None
    :raises: HTTPException si le token est invalide ou expiré
    """
    try:
        jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_db_connection():
    """
    Fonction qui permet de se connecter à la base de données MySQL
    
    :return: Objet connexion à la base de données
    """
    return mysql.connector.connect(
        host="localhost",
        user=USER,
        password=PASSWORD,
        database="employees"
    )

def get_mongo_connection():
    """
    Fonction qui permet de se connecter à la base de données MongoDB
    
    :return: Objet collection MongoDB
    """
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    return db[MONGO_COLLECTION]



@app.get("/revues")
async def get_revues(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    titre: Optional[str] = Query(None, alias="titre"),
    langue: Optional[str] = Query(None, alias="langue"),
    source: Optional[str] = Query(None, alias="source"),
    date_edition: Optional[int] = Query(None, alias="date_edition"),
    limit: Optional[int] = Query(10, alias="limit")
):
    """
    Route qui permet de récupérer les revues en fonction de différents critères
    
    :param credentials: Credentials pour l'authentification
    :param titre: Titre de la revue (optionnel)
    :param langue: Langue de la revue (optionnel)
    :param source: Source de la revue (optionnel)
    :param date_edition: Année d'édition de la revue (optionnel)
    :param limit: Nombre de revues à retourner (optionnel, 10 par défaut)
    :return: Liste des revues
    """
    # Vérification du token
    await verify_token(credentials)
    
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Requête de base pour récupérer les revues
    query = """
        SELECT 
            Revue.id_Titre,
            Revue.Titre,
            Revue.Contributeur,
            Revue.Langue,
            Revue.Identifiant,
            Revue.Source,
            Revue.Source_détail,
            Revue.Date_de_mise_en_ligne,
            Revue.Conservation_numerique,
            Revue.Date_d_edition,
            Revue.URL,
            GROUP_CONCAT(DISTINCT Auteur.Auteur) AS Auteurs,
            GROUP_CONCAT(DISTINCT Editeur.Nom) AS Editeurs,
            GROUP_CONCAT(DISTINCT Sujet.Sujet) AS Sujets
        FROM Revue
        LEFT JOIN Revue_Auteur ON Revue.id_Titre = Revue_Auteur.id_Titre
        LEFT JOIN Auteur ON Revue_Auteur.id_Auteur = Auteur.id_Auteur
        LEFT JOIN Revue_Editeur ON Revue.id_Titre = Revue_Editeur.id_Titre
        LEFT JOIN Editeur ON Revue_Editeur.id_Editeur = Editeur.id_Editeur
        LEFT JOIN Revue_Sujet ON Revue.id_Titre = Revue_Sujet.id_Titre
        LEFT JOIN Sujet ON Revue_Sujet.id_Sujet = Sujet.id_Sujet
        WHERE 1=1
    """
    params = []

    # Ajout des filtres optionnels
    if titre:
        query += " AND Revue.Titre LIKE %s"
        params.append(f"%{titre}%")
    if langue:
        query += " AND Revue.Langue = %s"
        params.append(langue)
    if source:
        query += " AND Revue.Source = %s"
        params.append(source)
    if date_edition:
        query += " AND Revue.Date_d_edition = %s"
        params.append(date_edition)

    # Groupement et limite
    query += " GROUP BY Revue.id_Titre LIMIT %s"
    params.append(limit)

    # Exécution de la requête
    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    connection.close()

    return results


@app.get("/mongo-data")
async def get_mongo_data(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    limit: Optional[int] = Query(10, alias="limit")
):
    """
    Route qui permet de récupérer des données depuis MongoDB
    
    :param credentials: Credentials pour l'authentification
    :param limit: Nombre de documents limite à retourner
    :return: Liste des documents MongoDB
    """
    # Vérification du token
    await verify_token(credentials)
    
    collection = get_mongo_connection()
    results = list(collection.find().limit(limit))
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)