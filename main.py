from pip._internal.utils import retry
from playwright.sync_api import sync_playwright
import json
import csv
import time

LOGIN = "f.simonin128"
PASSWORD = "FloFs131102&"
URL = "https://0383301g.index-education.net/pronote/mobile.parent.html"
current_page = ""

MYDEBUG = True

notes_data = []

notes = []

def in_auth_flow(page):
    if "cas" in page.url.lower():
        if "login" in page.url.lower():
            return "cas login"
        elif "redirect" in page.url.lower():
            return "cas client redirect"
    elif "educonnect" in page.url.lower():
        return "educonnect"
    elif "saml" in page.url.lower():
        return "saml"
    else:
        return "page inconnu : " + page.url.lower()


def is_logged_in(page):
    return "0383301g.index-education.net/" in page.url.lower()

def cas_login(page, login, password):

    if "cas.ent.auvergnerhonealpes.fr" in page.url.lower():
        print("PAGE de connection à l'ENT en tant que : Elève ou parent")
        # case a cocher
        if page.locator('label[for="idp-EDU"]'):
            print("input#idp-EDU : detecte")
            page.locator('label[for="idp-EDU"]').click()
        # boutons a cliquer :
        if page.locator('#button-submit') :
            print("#bouton_submit : detecte")
            page.locator('#button-submit').hover()
            page.wait_for_timeout(50)
            page.locator('#button-submit').click()
        return True

    elif "SAML2" in page.url.lower():
        if page.locator('#bouton_responsable'):
            print("PAGE de selection du profil Pronote a utiliser (parent responsable)")
            # PAGE de login SAML2
            # PAGE de selection du profil Pronote a utiliser (parent responsable)
            # boutons a cliquer :
            print("#bouton_responsable : detecte")
            page.locator('#bouton_responsable').hover()
            page.locator('#bouton_responsable').click()
            return True

        elif page.locator('input[name="username"]') and page.locator('input[name="password"]'):
            print("PAGE de login a Pronote [login/pass]")
            # PAGE de login SAML2
            print("page d indent et pass detectee")
            # champ a remplir :
            # ident
            page.fill('input[name="username"]', login)
            # pass
            page.fill('input[name="password"]', password)
            # boutons a cliquer :
            if page.locator('#bouton_valider'):
                print("#bouton_valider : detecte")
                page.locator('#bouton_valider').hover()
                page.wait_for_timeout(50)
                page.locator('#bouton_valider').click()
            return True

        return True
    return False


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
        current_url = page.url
        nbloop = 0

        while not is_logged_in(page):
            if current_url == page.url and nbloop >= 1:
                print("⏳ auth en cours (stage 2):", page.url)
            else:
                page.wait_for_load_state("domcontentloaded")
                print("⏳ auth en cours:", page.url)
            # WAIT GLOBAL AUTH FLOW
            nbloop += 1
            loop = True
            while loop :
                if cas_login(page, LOGIN, PASSWORD):
                    loop = False


        print("✅ sortie auth:", page.url)
        print("✅ connecté PRONOTE")

        # Attendre le chargement de la page
        page.wait_for_load_state("domcontentloaded")

        if MYDEBUG:
            print("-----------------------------")
            print("URL:", page.url)
            print("-----------------------------")
            print(page.content())
            print("-----------------------------")
            print("boutons:", page.locator("button").count())
            print("-----------------------------")


        if MYDEBUG:
            # detection des frames
            print("-----------------------------")
            print("FRAMES List:")
            for frame in page.frames:
                print("-----------------------------")
                print(frame.url)
                print("-----------------------------")
            print("-----------------------------")



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