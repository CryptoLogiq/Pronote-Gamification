from playwright.sync_api import sync_playwright
import time
import json
import sys
import os

def load_credentials():
    filename = "credentials.json"
    template = {
        "login": "your_login_here",
        "password": "your_password_here",
        "jj": "00",
        "mm": "00",
        "aa": "0000",
        "url": "https://your_pronote_url_here"
    }
    required_keys = {"login", "password", "url", "jj", "mm", "aa"}

    # 🆕 créer le fichier s'il n'existe pas
    if not os.path.exists(filename):
        print("⚠️ credentials.json introuvable → création d'un fichier modèle")

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
            jj = data.get("jj", "").strip()
            mm = data.get("mm", "").strip()
            aa = data.get("aa", "").strip()
            url = data.get("url", "").strip()

        # ❌ détecter si utilisateur n'a pas rempli
        if (
            not login or
            not password or
            not jj or
            not mm or
            not aa or
            not url or
            login == template["login"] or
            password == template["password"] or
            jj == template["jj"] or
            mm == template["mm"] or
            aa == template["aa"] or
            password == template["password"] or
            url == template["url"]

        ):
            print("❌ credentials.json non configuré correctement")
            print("👉 Remplis les champs login / password / url")
            sys.exit(1)

        if set(data.keys()) != required_keys:
            print("❌ credentials.json mal formé")
            sys.exit(1)


        credentials = {"login":login, "password":password, "jj":jj, "mm":mm, "aa":aa, "url":url}
        return credentials

    except json.JSONDecodeError:
        print("❌ credentials.json invalide (JSON corrompu)")
        sys.exit(1)

# JSON FILE PARAMETERS
# for use script you need to create a credentials.json file in your racine script (where your main.py is located)
# {
#   "login": "your_login_here",
#   "password": "your_password_here",
#   "url": "your_url_login_here" example : "https://0383301g.index-education.net/pronote/mobile.parent.html"
# }


# 🔐 LOAD CONFIG/SETTINGS SCRIPT
Creds = load_credentials()
DEBUG = True



# 🧠 STATES
STATE_WAYF = "WAYF"
STATE_LOGIN = "LOGIN"
STATE_PROFILE = "PROFILE"
STATE_PRONOTE = "PRONOTE"


# 🔍 DETECTION D'ÉTAT
def detect_state(page):
    url = page.url.lower()

    if "pronote" in url and not "cas" in url :
        return STATE_PRONOTE

    if "cas" in url  and page.locator('label[for="idp-EDU"]').count() > 0:
        return STATE_WAYF

    if page.locator('input[name="username"]').count() > 0:
        return STATE_LOGIN

    if page.locator('#bouton_responsable').count() > 0:
        return STATE_PROFILE

    return None


# 🎯 ACTIONS PAR ÉTAT
def handle_wayf(page):
    print("➡️ WAYF (ENT)")
    page.locator('label[for="idp-EDU"]').click()
    page.locator('#button-submit').click()


def handle_login(page, login, password):
    print("➡️ LOGIN (EduConnect)")
    page.fill('input[name="username"]', login)
    page.fill('input[name="password"]', password)
    page.locator('button[type="submit"]').click()


def handle_profile(page):
    print("➡️ PROFILE (Parent d'élèves)")
    btn = page.locator('#bouton_responsable')

    try:
        btn.wait_for(state="visible", timeout=3000)
        page.wait_for_timeout(500)  # laisse le DOM respirer
        btn.click()
    except:
        print("⚠️ bouton profil non prêt, retry...")

def fill_identity_and_validate(page, creds):
    day = page.locator('input[name="jour"]')
    month = page.locator('input[name="mois"]')
    year = page.locator('input[name="annee"]')

    # Jour
    day.click()
    day.press("Control+A")
    day.press("Backspace")
    page.keyboard.type(creds["jj"], delay=80)
    page.keyboard.press("Tab")

    # Mois
    month.click()
    month.press("Control+A")
    month.press("Backspace")
    page.keyboard.type(creds["mm"], delay=80)
    page.keyboard.press("Tab")

    # Année
    year.click()
    year.press("Control+A")
    year.press("Backspace")
    page.keyboard.type(creds["aa"], delay=80)
    page.keyboard.press("Tab")

    page.wait_for_timeout(400)

    btn = page.locator('button:has-text("Confirmer")')

    try:
        btn.wait_for(state="visible", timeout=5000)
        btn.hover()
        page.wait_for_timeout(150)
        btn.click(timeout=3000)
    except Exception:
        # fallback : petit clic ailleurs pour déclencher blur/change
        page.mouse.move(50, 50)
        page.mouse.click(50, 50)
        page.wait_for_timeout(200)
        btn.click(force=True)

# 🔁 MACHINE À ÉTATS
def run_auth_flow(page, creds, timeout=60):
    start = time.time()
    step = 0

    while True:
        if time.time() - start > timeout:
            print("❌ TIMEOUT GLOBAL")
            return False

        page.wait_for_timeout(500)

        print(f"🔎 STEP {step} | URL → {page.url}")

        # 0️⃣ WAYF
        if step == 0:
            if page.locator('#idp-EDU').count() > 0:
                print("➡️ WAYF eleves ou Parent [case a cocher]")

                page.locator('label[for="idp-EDU"]').click()
                page.locator('#button-submit').click()

                step += 1
                continue

        # 1️⃣ PROFILE
        elif step == 1:
            btn = page.locator('#bouton_responsable')

            if btn.count() > 0:
                print("➡️ PROFILE [Parent Responsable]")

                try:
                    btn.click(timeout=2000)
                except:
                    page.evaluate("document.querySelector('#bouton_responsable').click()")

                step += 1
                continue

        # 2️⃣ LOGIN
        elif step == 2:
            if page.locator('input[name="j_username"]').count() > 0:

                print("➡️ LOGIN + MDP")

                # champ identifiant
                #< input class ="fr-input" type="text" id="username" name="j_username" placeholder="Identifiant au format p.nomXX" autocapitalize="off" required="" autocomplete="off" >
                page.fill('input[name="j_username"]', creds["login"])
                page.wait_for_timeout(150)

                #champ password
                #<input class="fr-input" type="password" id="password" name="j_password" required="" autocomplete="off">
                page.fill('input[name="j_password"]', creds["password"])
                page.wait_for_timeout(150)

                btn = page.locator('#bouton_valider')

                if btn.count() > 0:
                    print("➡️ LOGIN submit")

                    try:
                        btn.wait_for(state="visible", timeout=5000)
                        btn.scroll_into_view_if_needed()
                        btn.click(timeout=3000)

                    except:
                        print("⚠️ click normal échoué → force")

                        try:
                            btn.click(force=True)
                            page.keyboard.press("Enter")
                        except:
                            print("⚠️ force échoué → JS click")
                            page.evaluate("document.querySelector('#bouton_valider').click()")

                step += 1
                continue

        # 3️⃣ VERIFY (optionnel)
        elif step == 3:
            # champs date naissance
            if page.locator('input[name="jour"]').count() > 0:
                print("➡️ VERIF identité (date naissance d'un de vos enfant)")

                fill_identity_and_validate(page, creds)

                step += 1
                continue
            else:
                # pas de vérif → skip
                step += 1
                continue

        # 4️⃣ PRONOTE
        elif step == 4:
            if "pronote" in page.url.lower() or creds["url"] in page.url:
                print("✅ PRONOTE OK")
                return True

            # fallback si stuck
            print("⚠️ fallback accès PRONOTE direct")
            page.goto(creds["url"])
            step += 1
            continue

        elif step == 5:
            print(f"🔎 STEP {step} | URL → {page.url}")
            print("✅ PRONOTE OK")
            return True

        # on wait si pas de conditions valide (page/dom pas fini de chargé ou pas synchro)
        page.wait_for_timeout(500)


# 🚀 MAIN
with sync_playwright() as p:

    browser = p.chromium.launch(headless=not DEBUG)
    context = browser.new_context()

    # ⚠️ important avec persistent context
    page = context.new_page()

    print("🌐 ouverture URL")
    page.goto(Creds["url"])

    success = run_auth_flow(page, Creds)

    if not success:
        print("❌ login échoué")
        context.close()
        exit()

    print("🎯 PRONOTE prêt !")

    # ⏳ laisse ouvert pour debug
    if DEBUG:
        print("👀 navigateur laissé ouvert pour inspection")
        time.sleep(9999)

    context.close()