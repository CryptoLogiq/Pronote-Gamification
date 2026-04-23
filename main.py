from playwright.sync_api import sync_playwright
import time
import json
import sys

import json
import sys
import os

TEMPLATE = {
    "login": "your_login_here",
    "password": "your_password_here",
    "url": "https://your_pronote_url_here"
}

required_keys = {"login", "password", "url"}

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
            login == TEMPLATE["login"] or
            password == TEMPLATE["password"] or
            url == TEMPLATE["url"]
        ):
            print("❌ credentials.json non configuré correctement")
            print("👉 Remplis les champs login / password / url")
            sys.exit(1)
        elif set(data.keys()) != required_keys:
            print("❌ credentials.json mal formé")
            sys.exit(1)

        return login, password, url

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
LOGIN, PASSWORD, URL = load_credentials()
DEBUG = True



# 🧠 STATES
STATE_WAYF = "WAYF"
STATE_LOGIN = "LOGIN"
STATE_PROFILE = "PROFILE"
STATE_PRONOTE = "PRONOTE"


# 🔍 DETECTION D'ÉTAT
def detect_state(page):
    url = page.url.lower()

    if "pronote" in url:
        return STATE_PRONOTE

    if page.locator('label[for="idp-EDU"]').count() > 0:
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


# 🔁 MACHINE À ÉTATS
def run_auth_flow(page, login, password, timeout=60):
    start = time.time()
    last_state = None

    while True:
        if time.time() - start > timeout:
            print("❌ TIMEOUT GLOBAL")
            return False

        page.wait_for_timeout(500)

        state = detect_state(page)

        # DEBUG propre
        if state != last_state:
            print(f"🔎 STATE → {state} | URL → {page.url}")
            last_state = state

        if state == STATE_WAYF:
            handle_wayf(page)
            continue

        if state == STATE_LOGIN:
            handle_login(page, login, password)
            continue

        if state == STATE_PROFILE:
            handle_profile(page)
            continue

        if state == STATE_PRONOTE:
            print("✅ PRONOTE atteint")
            return True

        # état inconnu → on attend
        # utile pendant les transitions SAML
        pass


# 🚀 MAIN
with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(
        user_data_dir="./profile",
        headless=not DEBUG,
        args=["--start-maximized"]
    )

    # ⚠️ important avec persistent context
    page = context.pages[0] if context.pages else context.new_page()

    print("🌐 ouverture URL")
    page.goto(URL)

    success = run_auth_flow(page, LOGIN, PASSWORD)

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