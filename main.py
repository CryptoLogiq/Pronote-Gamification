from playwright.sync_api import sync_playwright
import time

# 🔐 CONFIG
LOGIN = "f.simonin128"
PASSWORD = "FloFs131102&"
URL = "https://0383301g.index-education.net/pronote/mobile.parent.html"

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