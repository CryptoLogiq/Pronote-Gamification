from pip._internal.utils import retry
from playwright.sync_api import sync_playwright
import json
import csv
import time
import json
import sys
import os

def load_credentials():
    filename = "credentials.json"

    # 🆕 créer le fichier s'il n'existe pas
    if not os.path.exists(filename):
        print("⚠️ credentials.json introuvable → création d'un fichier modèle")

        template = {
            "login": "your_login_here",
            "password": "your_password_here",
            "url": "https://your_pronote_url_here"
        }

        with open(filename, "w") as f:
            json.dump(template, f, indent=4)

        print("✅ Fichier credentials.json créé")
        print("👉 Remplis-le puis relance le script")

        sys.exit(1)

    # 🔐 lecture du fichier
    try:
        with open(filename, "r") as f:
            data = json.load(f)

        login = data.get("login", "").strip()
        password = data.get("password", "").strip()
        url = data.get("url", "").strip()

        # ❌ détecter si utilisateur n'a pas rempli
        if (
            not login or
            not password or
            not url or
            "your_" in login or
            "your_" in password
        ):
            print("❌ credentials.json non configuré correctement")
            print("👉 Remplis les champs login / password / url")
            sys.exit(1)

        return login, password, url

    except json.JSONDecodeError:
        print("❌ credentials.json invalide (JSON corrompu)")
        sys.exit(1)

LOGIN, PASSWORD, URL = load_credentials()

MYDEBUG = True

notes_data = []

notes = []

def in_auth_flow(page):
    if   "cas" in page.url.lower():
        return "cas"
    elif "educonnect" in page.url.lower():
        return "educonnect"
    elif "saml" in page.url.lower():
        return "saml"
    elif "login" in page.url.lower():
        return "login"
    else:
        return "inconnu" + page.url.lower()


def is_logged_in(page):
    return "pronote" in page.url.lower() and "cas" not in page.url.lower()

def cas_login(page, login, password, currentpage):

    print("Page actuelle detectee comme : " + currentpage)

    # champ a remplir :
    if page.locator('input[name="username"]').count() > 0:
        page.fill('input[name="username"]', login)
        page.wait_for_timeout(100)

    if page.locator('input[name="password"]').count() > 0:
        page.fill('input[name="password"]', login)
        page.wait_for_timeout(100)

    # boutons a cliquer :
    if page.locator('input#idp-EDU').count() > 0:
        print("input#idp-EDU : detecte")
        page.locator('label[for="idp-EDU"]').click()
        page.wait_for_timeout(100)

    if page.locator('#bouton_valider').count() > 0:
        print("#bouton_valider : detecte")
        #page.locator('#bouton_valider').click()
        #page.wait_for_timeout(100)
        btn = page.locator('#bouton_valider')
        btn.wait_for(state="visible", timeout=1000)
        page.wait_for_timeout(100)
        btn.hover()
        btn.click()
        page.wait_for_timeout(100)

    if page.locator('#bouton_responsable').count() > 0:
        print("#bouton_responsable : detecte")
        btn = page.locator('#bouton_responsable')
        btn.wait_for(state="visible", timeout=1000)
        page.wait_for_timeout(100)
        btn.hover()
        btn.click()
        page.wait_for_timeout(100)

    if page.locator('#button-submit').count() > 0:
        print("#bouton_submit : detecte")
        page.locator('#button-submit').click()
        page.wait_for_timeout(100)


def capture(response):
    if "appelfonction" not in response.url:
        return

    try:
        data = response.json()

        # debug obligatoire
        print("URL:", response.url)

        # sauvegarde brute pour analyse
        notes.append({
            "url": response.url,
            "data": data
        })
    finally:
        pass



def extract_notes(response):
    global notes_data

    try:
        if "DernieresNotes" in response.url:
            data = response.json()

            # DEBUG : voir la structure réelle
            print(json.dumps(data, indent=2))

            # ⚠️ à adapter selon structure réelle
            for matiere in data.get("donnees", {}).get("listeMatieres", []):
                nom_matiere = matiere.get("nom")

                for note in matiere.get("listeNotes", []):
                    notes_data.append({
                        "matiere": nom_matiere,
                        "note": note.get("note"),
                        "bareme": note.get("bareme"),
                        "date": note.get("date")
                    })

    except Exception as e:
        print("Erreur extraction:", e)

def log_all_responses(response):
    try:
        if "appelfonction" in response.url:
            print("\n=== URL ===")
            print(response.url)
            print(response.text()[:300])
    finally:
        pass


def main():
    with sync_playwright() as p:

        context = p.chromium.launch_persistent_context(
            user_data_dir="./profile",  # dossier local
            headless= not MYDEBUG
        )
        page = context.new_page()
        page.wait_for_load_state("domcontentloaded")

        page.goto(URL)
        page.wait_for_load_state("domcontentloaded")

        while not is_logged_in(page):
            # WAIT CAS
            page.wait_for_load_state("domcontentloaded")
            pagestart = page.url
            print("⏳ auth en cours:", pagestart)


            # 2. WAIT GLOBAL AUTH FLOW
            loop = True
            while loop :
                cas_login(page, LOGIN, PASSWORD, in_auth_flow(page))
                newpage = page.url
                if pagestart != newpage:
                    loop = False

        print("✅ sortie auth:", page.url)

        # 🔁 re-check si on est bien connecte
        if not is_logged_in(page):
            print("✅ sortie auth:", page.url)
            print(page.url)
            print(page.locator("button").count())
            print("❌ login échoué")
            context.close()
            exit()
        else:
            print("✅ connecté PRONOTE")

        # Attendre le chargement de la page
        page.wait_for_load_state("domcontentloaded")

        # 🔥 IMPORTANT : attendre navigation réelle
        page.wait_for_url("**cas.ent**")

        if MYDEBUG:
            print("URL:", page.url)
            print("-----------------------------")
            print(page.content())
            print("-----------------------------")
            print("boutons:", page.locator("button").count())

        # attendre redirection PRONOTE
        page.wait_for_timeout(3000)
        page.wait_for_load_state("networkidle")


        if MYDEBUG:
            # detection des frames
            print("FRAMES List:")
            for frame in page.frames:
                print(frame.url)

        # cliquer sur l’onglet notes (très important)
        # page.locator("#id_77id_44").click() # id du bouton pour voir les notes =)
        # page.get_by_text("Notes").click() # n'existe pas en mode "mobile"

        for frame in page.frames:
            btn = frame.locator('button[aria-label="Tout voir"]')
            if btn.count() > 0:
                print("Trouvé dans frame:", frame.url)
                btn.first.click()
                break

        if MYDEBUG:
            print(page.content()[:2000])


        #page.on("response", extract_notes)
        page.on("response", log_all_responses)
        page.on("response", capture)

        # attendre chargement des données
        time.sleep(100)

        context.close()

main()

#Apres la navigation
print(json.dumps(notes[:1], indent=2))

# 💾 Export CSV
with open("notes.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["matiere", "note", "bareme", "date"])
    writer.writeheader()
    writer.writerows(notes_data)

print("✅ CSV généré !")