import requests
import time
import xml.etree.ElementTree as ET
import json
import re

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import pandas as pd
from datetime import datetime
import pymongo
import os
import mysql.connector
from dotenv import load_dotenv 


# I. Extraction des données
# I.1 interrogation de l'API et extraction des URL 


def extract_urls_from_xml(xml_data):
    """Cette fonction extrait les URLs des notices détaillées de la réponse XML de Gallica et les stocke dans la liste URL"""
    urls = []
    root = ET.fromstring(xml_data)
    
    # L'élément <record> contient l'URL de la notice détaillée
    for record in root.findall(".//{http://www.loc.gov/zing/srw/}record"):
        url_elem = record.find(".//{http://purl.org/dc/elements/1.1/}identifier")
        if url_elem is not None and "gallica.bnf.fr" in url_elem.text:
            urls.append(url_elem.text)

    return urls

# application de la fonction à l'API de recherche
BASE_URL = "https://gallica.bnf.fr/SRU"
QUERY = '(dc.type all "fascicule") and (ocr.quality all "Texte disponible")'  
MAX_RECORDS = 50      # Limite imposée par l'API
TOTAL_RESULTS = 5000  # Nombre d'URL que je souhaite extraire
start_record = 0
results = []

while len(results) < TOTAL_RESULTS:
    params = {
        "operation": "searchRetrieve",
        "version": "1.2",
        "startRecord": start_record,
        "maximumRecords": MAX_RECORDS,
        "collapsing": "true",
        "exactSearch": "false",
        "query": QUERY
    }


    response = requests.get(BASE_URL, params=params)
    if response.status_code == 200:
        data = response.text  # Réponse en XML
        # Extraction des URLs des notices détaillées à partir du XML
        urls = [url for url in extract_urls_from_xml(data)] 
        results.extend(urls)
        start_record += MAX_RECORDS
        time.sleep(0.5)  # Pause pour éviter le blocage par l'API
    else:
        print(f"Erreur {response.status_code}")
        break

print(f"Nombre total de résultats récupérés : {len(results)}")



#I. 2 scapping des métadonnées à partir des URLs

# Configuration de Selenium
chrome_options = Options()
chrome_options.add_argument("--headless")  # headless = mode sans interface graphique
driver = webdriver.Chrome( options=chrome_options)
wait = WebDriverWait(driver, 10)


def get_metadata_from_notice(url):
    """Cette fonction permet de récupérer des métadonnées d'une revue Gallica après avoir cliqué sur le dropdown."""
    try:
        driver.set_page_load_timeout(15)  # Timeout à 15 secondes
        driver.get(url)
    except Exception as e:
        print(f"⏳ Timeout dépassé pour {url}, passage à l'URL suivante...")
        return None

    start_time = time.time()  # Démarrage du chrono

    try:
        print(f" {url} - Vérification du bouton 'Informations détaillées'...")
        details = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div#moreInfosRegion")))
        details.click()
        print(" Dropdown cliqué !")

        print(" Attente du chargement des métadonnées...")
        metadata_section = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "dl.noticeDetailsArea")))
        time.sleep(1)  # Pause supplémentaire

        
        # Vérifie si on récupère bien toutes les clés <dt>
        titles = metadata_section.find_elements(By.XPATH, "./dt")
        print(f" {len(titles)} métadonnées trouvées sur {url}")

        data = {"url": url}

        for title in titles:
            key = title.text.strip().replace("\n", " ")  # Nettoyage clé

            if key:  # Filtre des clés vides
                try:
                    content_elements = title.find_elements(By.XPATH, "./following-sibling::dd")
                    print(f" Clé détectée : {key} - {len(content_elements)} éléments dd trouvés")

                    content = "; ".join([c.text.strip() for c in content_elements if c.text.strip()])
                    data[key] = content if content else "Valeur vide"
                except Exception:
                    print(f" Métadonnée sans valeur pour {key}")
                    data[key] = "Valeur manquante"
            else:
                print(f" Clé vide ignorée pour {url}")  # Nouvelle alerte

        elapsed_time = time.time() - start_time
        print(f" Données récupérées en {elapsed_time:.2f} secondes pour {url}")

        return data

    except Exception as e:
        print(f"ATTENTION! Erreur sur {url} : {e}")
        time.sleep(5)
        return None



# Chargement de 50 URLs de test
with open("urls_gallica.json", "r") as f:
    urls = json.load(f)

urls = urls[:50]  # Sélection de 50 URLs pour le test



# Scrapping de toutes les URL et stokage des résultats
metadata_list = []
error_log = []

for i, url in enumerate(urls, start=1):
    print(f"🔹 {i}/{len(urls)} - Scraping {url}")
    metadata = get_metadata_from_notice(url)

    if metadata:
        metadata_list.append(metadata)
    else:
        error_log.append(url)

    time.sleep(0.5)  # Pause pour éviter le blocage

# Sauvegarde en JSON
with open("metadata_gallica_test.json", "w", encoding="utf-8") as f:
    json.dump(metadata_list, f, indent=4, ensure_ascii=False)

# Sauvegarde en CSV
df = pd.DataFrame(metadata_list)
df.to_csv("metadata_gallica_test.csv", index=False, encoding="utf-8")

# Sauvegarde des erreurs
with open("erreurs_urls_test.txt", "w") as f:
    for url in error_log:
        f.write(url + "\n")

# Fermeture de Selenium
driver.quit()

print(f" Test terminé ! {len(metadata_list)} résultats enregistrés.")
print(f"ATTENTION! {len(error_log)} erreurs enregistrées dans erreurs_urls_test.txt")



# II Construction du Dataframe et nettoyage des données


# **Construction du DataFrame**
with open("metadata_gallica.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

print(f"Nombre d'entrées : {len(raw_data)}")

all_keys = sorted(set().union(*(entry.keys() for entry in raw_data)))
df = pd.DataFrame([{key: entry.get(key, "") for key in all_keys} for entry in raw_data])

df.to_json("metadata_gallica_clean.json", orient="records", indent=4, force_ascii=False)
df.to_csv("metadata_gallica_clean.csv", index=False, encoding="utf-8")

print(f"Export terminé ! {df.shape[0]} lignes et {df.shape[1]} colonnes générées.")



# II. 1. vérification et effacement des doublons
df.duplicated()
df.drop_duplicates(inplace=True)


# II. 2. Formatage des données pour chaque colonne


df["Conservation numérique :"] = df["Conservation numérique :"].apply(
    lambda x: "Bibliothèque nationale de France" if x != "" and x != "Bibliothèque nationale de France" else x
)
df["Auteur :"] = df["Auteur :"].str.split(". Auteur du texte").str[0]
# str.split(". Auteur du texte") : Cette méthode divise chaque chaîne de la colonne "Auteur :" en deux parties, en utilisant ". Auteur du texte" comme séparateur.
# .str[0] : Après la division, nous sélectionnons la première partie (celle à gauche du séparateur).

df["Contributeur :"] = df["Contributeur :"].str.extract(r'^([^.(]+(?:\s*\([^)]*\))?)')
# Utilisation d'une regex pour extraire le texte avant le premier point de chaque ligne, en ignorant d'éventuels points dans les parenthèses (années de naissance et mort)
print(df["Contributeur :"].value_counts())


df["Date d'édition :"] = df["Date d'édition :"].str.split("-").str[0]
# Ceci permet d'extraire le texte à gauche du premier tiret "-"

df["Date d'édition :"] = pd.to_numeric(df["Date d'édition :"], errors="coerce")
# Ceci transforme le texte en valeur numérique

# transformation en entiers --> Les NaNs sont remplacés par la valeur "2040"
df["Date d'édition :"] = df["Date d'édition :"].fillna(2040).astype(int)

df["Date de mise en ligne :"] = pd.to_datetime(
    df["Date de mise en ligne :"], format="%d/%m/%Y"
).dt.strftime("%Y-%m-%d")
# Ceci permet de convertir la colonne "Date de mise en ligne :" au format YYYY-MM-DD

df["Langue :"] = df["Langue :"].str.split(";").str[0].str.lower()
# Extraction du texte à gauche du point-virgule ";" et suppression des majuscules




# GESTION DE LA SERIE "SOURCE"

# Fonction pour extraire ce qui est APRÈS la première ponctuation
def extract_after_punctuation(text):
    """Cette fonction permet d'extraire le texte après le premier caractère de ponctuation rencontré"""
    if pd.isna(text):  # Gérer les NaN
        return ""
    
    match = re.search(r"[,:;.-]\s*(.*)", text)  # Capture après la ponctuation
    return match.group(1) if match else ""  

# Fonction pour extraire ce qui est AVANT la première ponctuation
def extract_before_punctuation(text):
    """Cette fonction permet d'extraire le texte avant le premier caractère de ponctuation rencontré"""
    if pd.isna(text):  # Gérer les NaN
        return ""

    match = re.search(r"^(.*?)[,:;.-]", text)  # Capture avant la ponctuation
    return match.group(1).strip() if match else text  # Si pas de ponctuation, garder tout


# Application de la fonction sur la colonne "Source :"

df["Source (détail)"] = df["Source :"].apply(extract_after_punctuation)  # Partie après la ponctuation
df["Source :"] = df["Source :"].apply(extract_before_punctuation)  # Partie avant la ponctuation

# Localisation de la position de la colonne "Source :"
source_col_index = df.columns.get_loc("Source :")

# Insértion de la colonne "Source (détail)" juste après "Source :"
df.insert(source_col_index + 1, "Source (détail)", df.pop("Source (détail)"))


# Gestion de la série "Sujet"

def extraction_sujet(text):
    """Cette fonction permet d'extraire le sujet en fonction du pattern que j'ai défini selon 3 règles"""
    if pd.isna(text):  # Gestion des NaN
        return text
    
    # Condition 1 : Extraction à gauche de " Relancer" (espace inclus)
    if " Relancer" in text:
        return text.split(" Relancer")[0].strip()
    
    # Condition 2 : Extraction à gauche de " --" (espace inclus)
    if " --" in text:
        return text.split(" --")[0].strip()
    
    # Condition 3 : Si aucune des conditions n'est remplie, retourner le texte original
    return text

# Application de la fonction à la colonne "Sujet :"
df["Sujet :"] = df["Sujet :"].apply(extraction_sujet)



# Gestion de la série "Editeur"

def extract_lieu(text):
    """ Extrait le lieu d'édition s'il est entre parenthèses ou après 'A' et avant la première virgule """
    if pd.isna(text) or text.strip() == "":
        return ""

    # Cas 1 : Lieu dans des parenthèses "(Lieu)"
    match = re.search(r"\(([^)]+)\)", text)
    if match:
        return match.group(1).strip()

    # Cas 2 : Lieu après "A " et avant la première virgule
    match = re.search(r"A ([^,]+),", text)
    if match:
        return match.group(1).strip()

    return ""

def extract_editeur(text):
    """ Extrait le nom de l'éditeur en fonction de la structure du texte """
    if pd.isna(text) or text.strip() == "":
        return ""

    # Cas 1 : Éditeur avant la première parenthèse "(Lieu)"
    match = re.search(r"^(.+?)\s*\(", text)
    if match:
        return match.group(1).strip()

    # Cas 2 : Éditeur entre la première et la deuxième virgule après "A"
    match = re.search(r"A [^,]+, ([^,]+),", text)
    if match:
        return match.group(1).strip()

    return text.split(";")[0].strip()  # Par défaut, prendre avant le premier ';'

def extract_details(text):
    """ Extrait les détails en supprimant les infos déjà extraites et les liens """
    if pd.isna(text) or text.strip() == "":
        return ""

    # Supprimer les liens
    cleaned_text = re.sub(r"\| Liens?: .*", "", text)

    # Supprimer le lieu et l'éditeur si extraits
    lieu = extract_lieu(text)
    editeur = extract_editeur(text)

    if lieu:
        cleaned_text = cleaned_text.replace(f"({lieu})", "").strip()
    if editeur:
        cleaned_text = cleaned_text.replace(editeur, "").strip()

    return cleaned_text

# Application des fonctions
df["Lieu"] = df["Éditeur :"].apply(extract_lieu)
df["Éditeur"] = df["Éditeur :"].apply(extract_editeur)
df["Éditeur (détails)"] = df["Éditeur :"].apply(extract_details)



# export des versions finales du DF nettoyé en local
df.to_json("metadata_gallica_cleanV2.json", orient="records", indent=4, force_ascii=False)
df.to_csv("metadata_gallica_cleanV2.csv", index=False, encoding="utf-8")

# III  Création et remplissage des bases de données

load_dotenv() # chargement des variables d'environnement 

# Connexion à MySQL
mysql_conn = mysql.connector.connect(
    host="localhost",
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database="Revues_numerisees"
)

mysql_cursor = mysql_conn.cursor()


# Connexion MongoDB via les variables d'environnement
mongo_client = pymongo.MongoClient(os.getenv("MONGO_URI"))  
mongo_db = mongo_client[os.getenv("MONGO_DB")]
notices_collection = mongo_db[os.getenv("MONGO_COLLECTION")]


# Chargement du dataframe
df = pd.read_csv("metadata_gallica_cleanV2.csv")


# Remplacement des NaN par des None dans le DataFrame  --> En effet, MySQL ne sait pas gérer les Nans mais "None" est géré par les deux: équivaut à "Null" en SQL et "Nan" en Python
df = df.where(pd.notna(df), None)


# Troncature des colonnes VARCHAR avec un slicing à 254 caractères   --> Permet de limiter la data insérée en nombre de charactères et de rester en dessous de la limite de Varchar (255) 
varchar_columns = ["Titre :", "Contributeur :", "Langue :", "Identifiant :", "Source :", 
                   "Conservation numérique :", "Date d'édition :", "url"]

for col in varchar_columns:
    if col in df.columns:
        df[col] = df[col].apply(lambda x: x[:254] if isinstance(x, str) else x)



# Insertion des données SQL
for _, row in df.iterrows():
    # Insertion dans la table Revue
    sql_insert_revue = """
    INSERT INTO Revue (Titre, Contributeur, Langue, Identifiant, Source, Date_de_mise_en_ligne, 
                       Conservation_numerique, Date_d_edition, URL) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    mysql_cursor.execute(sql_insert_revue, (
        row["Titre :"], row["Contributeur :"], row["Langue :"], row["Identifiant :"], 
        row["Source :"], row["Date de mise en ligne :"], row["Conservation numérique :"], 
        row["Date d'édition :"], row["url"]
    ))

    mysql_conn.commit()

    # Récupérer l'ID de la revue insérée
    mysql_cursor.execute("SELECT LAST_INSERT_ID()")
    id_titre = mysql_cursor.fetchone()[0]

    # Insertion des Auteurs
    sql_insert_auteur = "INSERT INTO Auteur (Auteur) VALUES (%s)"
    if pd.notna(row["Auteur :"]):  # Vérifier si la colonne n'est pas vide
        mysql_cursor.execute(sql_insert_auteur, (row["Auteur :"],))
        mysql_conn.commit()

    # Insertion des sujets
    sql_insert_sujet = "INSERT INTO Sujet (Sujet) VALUES (%s)"
    if pd.notna(row["Sujet :"]):  # Vérifier si la colonne n'est pas vide
        mysql_cursor.execute(sql_insert_sujet, (row["Sujet :"],))
        mysql_conn.commit()

    # Insértion des notices correspondantes dans MongoDB
    notices_collection.insert_one({
        "id_Titre": id_titre,
        "Notice_ensemble": row["Notice d'ensemble :"],
        "Notice_catalogue": row["Notice du catalogue :"]
    })

# Fermeture des connexions
mysql_cursor.close()
mysql_conn.close()
mongo_client.close()

print("OK! Données insérées avec succès dans MySQL et MongoDB !")


# IV Requêtes READ

sql_query_1 = """
SELECT * FROM Revue 
WHERE Source IN ('Cité Internationale Universitaire de Paris', 'Bibliothèque nationale et universitaire de Strasbourg') 
ORDER BY Titre ASC;
"""
mysql_cursor.execute(sql_query_1)
result_1 = mysql_cursor.fetchall()
print(" Revues des sources universitaires :", result_1)


# 3 Requête SQL pour les revues entre 1939-1945 sans sujet spécifique
sql_query_2 = """
SELECT * FROM Revue 
WHERE Date_d_edition BETWEEN 1939 AND 1960
AND sujet = 'Guerre mondiale (1914-1918) -- Aspect religieux';
;
"""
mysql_cursor.execute(sql_query_2)
result_2 = mysql_cursor.fetchall()
print("Revues entre 1939 et 1960 concernant le sujet 'Guerre mondiale (1914-1918) -- Aspect religieux' :", result_2)

mysql_cursor.close()
mysql_conn.close()



# Connexion à MongoDB (logiciel):  Requête pour trouver les revues contenant "ISSN" dans "Notice du catalogue"
mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["revues_mongo"]
notices_collection = mongo_db["Notices"]

doc = notices_collection.find_one()
print(doc)


query = { "Notice_catalogue": { "$regex": "ISSN"} }
result = notices_collection.find(query)

# Affichage des résultats
for doc in result:
    print(doc)

mongo_client.close()