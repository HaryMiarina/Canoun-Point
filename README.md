# Canon Point

Canon Point est un jeu desktop en Python avec interface graphique PyQt5.

Le projet permet de:

- creer une grille personnalisable
- jouer a 2 joueurs (J1 et J2)
- aligner des points pour marquer
- utiliser le mecanisme de tir
- sauvegarder et charger les parties via MongoDB

## Apercu

Architecture principale:

- modele: gestion des regles et des points
- vue: fenetres PyQt5 et rendu de la grille
- controleur: orchestration de la partie et interactions utilisateur
- db: persistance des sauvegardes dans MongoDB

## Technologies

- Python 3
- PyQt5
- PyMongo
- MongoDB

## Prerequis

- Python 3.10+ recommande
- MongoDB en cours d execution sur localhost:27017
- environnement virtuel Python

## Installation

1. Cloner le depot

git clone <url-du-repo>
cd Canoun-Point

2. Creer puis activer l environnement virtuel

python3 -m venv venv
source venv/bin/activate

3. Installer les dependances

pip install pyqt5 pymongo

## Configuration MongoDB

Le projet lit sa configuration dans db/mongo.py:

- MONGO_URI
- DATABASE_NAME

Valeurs actuelles:

- utilisateur: user_db
- mot de passe: password_user_db
- base: db_name

Exemple de creation rapide dans MongoDB:

mongosh
use admin
db.createUser({
user: "user_db",
pwd: "password_user_db",
roles: [{ role: "root", db: "admin" }]
})
use db_name
db.grantRolesToUser("user_db", [{ role: "dbOwner", db: "db_name" }])

## Lancer l application

Option 1 (direct):

source venv/bin/activate
python main.py

Option 2 (script fourni):

source script/start.sh
python main.py

Pour fermer l environnement virtuel:

source script/close.sh

## Utilisation

1. Ouvrir l application
2. Saisir dimensions et noms des joueurs
3. Cliquer sur Creer la grille
4. Jouer, tirer, enregistrer ou charger une partie

## Structure du projet

main.py: point d entree

controller/

- game_controller.py: logique de controle de partie

model/

- game_model.py: modele de grille et alignements

view/

- dimension_view.py: ecran de configuration
- grid_view.py: ecran principal du jeu

db/

- mongo.py: connexion MongoDB et sauvegardes

script/

- start.sh: activation venv
- close.sh: desactivation venv

tuto_db_connexion/

- pymongo.txt: tutoriel de connexion MongoDB

## Verification rapide MongoDB

Vous pouvez tester la connexion MongoDB depuis Python avec un petit script:

from pymongo import MongoClient

client = MongoClient("mongodb://user_db:password_user_db@localhost:27017/db_name", serverSelectionTimeoutMS=3000)
client.admin.command("ping")
print("Connexion MongoDB OK")

## Depannage

- Erreur de connexion MongoDB:
  verifier que le service MongoDB est demarre et que les identifiants correspondent a db/mongo.py
- Erreur module PyQt5 introuvable:
  reactiver le venv puis relancer pip install pyqt5
- Erreur module pymongo introuvable:
  reactiver le venv puis relancer pip install pymongo

## Licence

Ajouter ici la licence du projet (MIT, Apache-2.0, etc.).
