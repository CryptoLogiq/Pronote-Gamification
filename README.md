# Pronote Gamification

Script personnel permettant de se connecter à PRONOTE / EduConnect et d’exporter les notes au format CSV.

> Ce projet est prévu pour un usage personnel, avec votre propre compte parent PRONOTE / EduConnect.

## Fonctionnalités

- Connexion à PRONOTE via EduConnect / ENT
- Sélection automatique des élèves liés au compte
- Récupération des dernières notes
- Export CSV propre et exploitable
- Génération d’un fichier CSV par élève
- Gestion des erreurs d’authentification
- Affichage d’une page d’erreur claire en cas de problème

## Installation

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python main.py
```

### Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python main.py
```

## Configuration

Au premier lancement, le script génère automatiquement un fichier :

```txt
credentials.json
```

Il faut ensuite modifier ce fichier avec vos informations personnelles.

Exemple :

```json
{
    "login": "your_login_here",
    "password": "your_password_here",
    "jj": "00",
    "mm": "00",
    "aa": "0000",
    "url": "https://your_pronote_url_here"
}
```

### Champs à remplir

- `login` : identifiant EduConnect / ENT
- `password` : mot de passe EduConnect / ENT
- `jj` : jour de naissance de l’enfant
- `mm` : mois de naissance de l’enfant
- `aa` : année de naissance de l’enfant
- `url` : URL d’accès à PRONOTE version mobile web

L’URL doit pointer vers la version mobile web de PRONOTE, par exemple :

```txt
https://votre-etablissement.index-education.net/pronote/mobile.parent.html
```

## Exports générés

Le script génère les exports dans un dossier dédié, avec un fichier CSV par élève.

Exemple :

```txt
exports_eleves/
├── notes_brutes_ELEVE_1_CLASSE.csv
└── notes_brutes_ELEVE_2_CLASSE.csv
```

Chaque fichier CSV contient une ligne par note, avec des colonnes séparées pour :

- élève
- classe
- moyenne générale
- matière
- moyenne de la matière
- sujet du contrôle
- note
- barème
- note sur 20
- coefficient
- date
- période
- commentaires éventuels

## Sécurité

Ne partagez jamais les fichiers suivants :

- `credentials.json`
- les fichiers CSV exportés
- les fichiers JSON bruts
- le dossier `debug_exports/`
- les captures HTML ou PNG générées en debug

Ces fichiers peuvent contenir des données personnelles : noms, classes, notes, moyennes, identifiants, captures HTML ou autres informations privées.

## Fichiers à ignorer avec Git

Le projet doit conserver un `.gitignore` strict pour éviter de publier des données personnelles.

Exemple :

```gitignore
# Credentials
credentials.json
.env

# Debug / captures sensibles
debug_exports/
*.html
*.png

# Exports PRONOTE
*.csv
*.json
exports_eleves/
pronote_raw_responses*.json

# Playwright / profils
profile/
.playwright/

# Python
__pycache__/
*.pyc
.venv/
venv/
```

Si vous souhaitez ajouter un fichier d’exemple comme `credentials.example.json`, pensez à l’autoriser explicitement dans le `.gitignore` :

```gitignore
!credentials.example.json
```

## Debug

Les options de debug se trouvent dans `debug.py`.

Exemple :

```python
DEBUG = False
DEBUG_PRINT = False
SHOW_BROWSER = True
```

- `DEBUG` : active les pauses de debug en cas d’échec
- `DEBUG_PRINT` : active les sorties console détaillées
- `SHOW_BROWSER` : affiche ou masque le navigateur Playwright

Pour un usage normal, il est conseillé de garder :

```python
DEBUG = False
DEBUG_PRINT = False
SHOW_BROWSER = True
```

## Avertissement

Ce script ne doit être utilisé que sur un compte auquel vous avez légitimement accès.

Il ne doit pas être utilisé pour collecter, surveiller ou exporter les données d’autres personnes sans autorisation.

L’auteur du script n’est pas responsable d’un mauvais usage, d’une mauvaise configuration ou d’une publication accidentelle de données personnelles.
