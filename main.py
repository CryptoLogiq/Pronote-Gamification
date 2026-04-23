from playwright.sync_api import sync_playwright
import time
import json
import sys
import os
import csv


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

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=4)

        print("✅ Fichier credentials.json créé")
        print("👉 Remplis-le puis relance le script")
        sys.exit(1)

    # 🔐 lecture du fichier
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        login = data.get("login", "").strip()
        password = data.get("password", "").strip()
        jj = data.get("jj", "").strip()
        mm = data.get("mm", "").strip()
        aa = data.get("aa", "").strip()
        url = data.get("url", "").strip()

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
            url == template["url"]
        ):
            print("❌ credentials.json non configuré correctement")
            print("👉 Remplis les champs login / password / jj / mm / aa / url")
            sys.exit(1)

        if set(data.keys()) != required_keys:
            print("❌ credentials.json mal formé")
            sys.exit(1)

        credentials = {
            "login": login,
            "password": password,
            "jj": jj,
            "mm": mm,
            "aa": aa,
            "url": url
        }
        return credentials

    except json.JSONDecodeError:
        print("❌ credentials.json invalide (JSON corrompu)")
        sys.exit(1)


# 🔐 LOAD CONFIG/SETTINGS SCRIPT
Creds = load_credentials()
DEBUG = True

# 🧠 STATES
STATE_WAYF = "WAYF"
STATE_LOGIN = "LOGIN"
STATE_PROFILE = "PROFILE"
STATE_PRONOTE = "PRONOTE"

# CSV
raw_responses = []
notes_rows = []


def debug_hold(page, reason=""):
    if DEBUG:
        print("\n================ DEBUG HOLD ================")
        if reason:
            print(reason)
        try:
            print("URL :", page.url)
        except Exception:
            pass
        try:
            print("Titre :", page.title())
        except Exception:
            pass
        print("La fenêtre reste ouverte. Appuie sur Entrée pour fermer...")
        input()


# 🔍 DETECTION D'ÉTAT
def detect_state(page):
    url = page.url.lower()

    if "pronote" in url and "cas" not in url:
        return STATE_PRONOTE

    if "cas" in url and page.locator('label[for="idp-EDU"]').count() > 0:
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
        page.wait_for_timeout(500)
        btn.click()
    except Exception:
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
        page.mouse.move(50, 50)
        page.mouse.click(50, 50)
        page.wait_for_timeout(200)
        btn.click(force=True)

def detect_connection_refused(page):
    try:
        body_text = page.locator("body").inner_text().lower()
    except Exception:
        return False

    refused_markers = [
        "connexion refusée",
        "accès refusé",
        "authentification refusée",
        "identifiant ou mot de passe incorrect",
        "identifiant incorrect",
        "mot de passe incorrect",
        "erreur d'authentification",
        "compte bloqué",
        "compte désactivé",
        "vous ne pouvez pas accéder",
        "accès non autorisé"
    ]

    return any(marker in body_text for marker in refused_markers)


# 🔁 MACHINE À ÉTATS
def run_auth_flow(page, creds, timeout=60):
    start = time.time()
    step = 0
    loop = 0

    while True:
        if time.time() - start > timeout:
            print("❌ TIMEOUT GLOBAL")
            return False

        page.wait_for_timeout(500)

        print(f"🔎 STEP {step} | URL → {page.url}")

        if detect_connection_refused(page):
            print("❌ Connexion refusée détectée")
            return False

        # 0️⃣ WAYF
        if step == 0:
            if page.locator('#idp-EDU').count() > 0:
                print("➡️ WAYF eleves ou Parent [case a cocher]")
                page.locator('label[for="idp-EDU"]').click()
                page.locator('#button-submit').click()
                step += 1
                page.wait_for_timeout(1200)
                continue

        # 1️⃣ PROFILE
        elif step == 1:
            btn = page.locator('#bouton_responsable')

            if btn.count() > 0:
                print("➡️ PROFILE [Parent Responsable]")

                try:
                    btn.click(timeout=2000)
                except Exception:
                    page.evaluate("document.querySelector('#bouton_responsable').click()")

                step += 1
                page.wait_for_timeout(1200)
                continue

        # 2️⃣ LOGIN
        elif step == 2:
            if page.locator('input[name="j_username"]').count() > 0:
                print("➡️ LOGIN + MDP")

                page.fill('input[name="j_username"]', creds["login"])
                page.wait_for_timeout(150)

                page.fill('input[name="j_password"]', creds["password"])
                page.wait_for_timeout(150)

                btn = page.locator('#bouton_valider')

                if btn.count() > 0:
                    print("➡️ LOGIN submit")

                    try:
                        btn.wait_for(state="visible", timeout=5000)
                        btn.scroll_into_view_if_needed()
                        btn.click(timeout=3000)
                    except Exception:
                        print("⚠️ click normal échoué → force")
                        try:
                            btn.click(force=True)
                            page.keyboard.press("Enter")
                        except Exception:
                            print("⚠️ force échoué → JS click")
                            page.evaluate("document.querySelector('#bouton_valider').click()")

                step += 1
                page.wait_for_timeout(1200)
                continue

        # 3️⃣ VERIFY (optionnel)
        elif step == 3:
            if page.locator('input[name="jour"]').count() > 0:
                print("➡️ VERIF identité (date naissance d'un de vos enfant)")
                fill_identity_and_validate(page, creds)
                step += 1
                continue
            else:
                step += 1
                page.wait_for_timeout(1200)
                continue

        # 4️⃣ PRONOTE
        elif step == 4:
            if "pronote" in page.url.lower() or "identifiant" in page.url.lower() or creds["url"] in page.url :
                print("✅ PRONOTE OK")
                return True

            print("⚠️ fallback, tentative d'acces direct a PRONOTE en rechargeant la page url cible")
            page.goto(creds["url"])
            step += 1
            page.wait_for_timeout(1200)
            continue

        # 5️⃣ Validation après fallback
        elif step == 5:
            print(f"🔎 STEP {step} | URL → {page.url}")
            if "pronote" in page.url.lower() or "identifiant" in page.url.lower() or creds["url"] in page.url :
                print("✅ PRONOTE OK")
                return True

            print("❌ fallback effectué mais PRONOTE non atteint")
            step = 0
            if loop == 0:
                loop += 1
                page.wait_for_timeout(1200)
                continue
            else:
                return False


        page.wait_for_timeout(500)


def capture(response):
    if "appelfonction" not in response.url:
        return
    try:
        raw_responses.append({
            "url": response.url,
            "data": response.json()
        })
    except Exception:
        pass

def save_all_responses_to_json(filename="pronote_raw_responses.json"):
    grouped = {}

    for item in raw_responses:
        data = item.get("data", {})
        response_id = data.get("id", "UNKNOWN")

        if response_id not in grouped:
            grouped[response_id] = []

        grouped[response_id].append({
            "url": item.get("url"),
            "data": data
        })

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(grouped, f, indent=2, ensure_ascii=False)

    print(f"✅ JSON brut sauvegardé dans : {filename}")

def save_raw_responses_flat(filename="pronote_raw_responses_flat.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(raw_responses, f, indent=2, ensure_ascii=False)

    print(f"✅ JSON brut à plat sauvegardé dans : {filename}")

def go_to_notes(context, page, timeout=30):
    start = time.time()

    page.on("response", extract_notes)
    page.on("response", log_all_responses)
    page.on("response", capture)

    clicked = False

    while time.time() - start <= timeout:
        for frame in page.frames:
            btn = frame.locator('#id_77id_44')
            if btn.count() > 0:
                try:
                    btn.wait_for(state="visible", timeout=3000)
                    btn.scroll_into_view_if_needed()
                    page.wait_for_timeout(300)
                    btn.click(timeout=3000)
                    clicked = True
                    print("✅ bouton 'Tout voir' cliqué")
                    page.wait_for_timeout(1200)
                    break
                except Exception:
                    try:
                        frame.evaluate("document.querySelector('#id_77id_44').click()")
                        clicked = True
                        print("✅ bouton 'Tout voir' cliqué via JS")
                        break
                    except Exception:
                        pass

        if clicked:
            break

        page.wait_for_timeout(500)

    if not clicked:
        print("❌ bouton #id_77id_44 introuvable ou non cliquable")
        return False

    # laisse le temps aux requêtes de partir et revenir
    page.wait_for_timeout(5000)

    # sauvegarde tout ce qu'on a reçu
    save_all_responses_to_json()
    save_raw_responses_flat()

    print("✅ dump JSON terminé")
    return True


def log_all_responses(response):
    try:
        if "appelfonction" in response.url:
            print("\n=== URL ===")
            print(response.url)
            print(response.text()[:300])
    except Exception:
        pass
def export_notes_csv(raw_responses, filename="notes.csv"):
    rows = []

    for item in raw_responses:
        data = item.get("data", {})
        if data.get("id") != "DernieresNotes":
            continue

        payload = data.get("dataSec", {}).get("data", {})
        devoirs = payload.get("listeDevoirs", {}).get("V", [])

        for devoir in devoirs:
            rows.append({
                "matiere": devoir.get("service", {}).get("V", {}).get("L", ""),
                "note": devoir.get("note", {}).get("V", ""),
                "bareme": devoir.get("bareme", {}).get("V", ""),
                "date": devoir.get("date", {}).get("V", ""),
                "periode": devoir.get("periode", {}).get("V", {}).get("L", ""),
                "moyenne_matiere": devoir.get("moyenne", {}).get("V", ""),
                "coefficient": devoir.get("coefficient", ""),
                "note_max": devoir.get("noteMax", {}).get("V", ""),
                "note_min": devoir.get("noteMin", {}).get("V", ""),
                "commentaire": devoir.get("commentaire", ""),
                "commentaire_sur_note": devoir.get("commentaireSurNote", ""),
                "est_bonus": devoir.get("estBonus", False),
                "est_facultatif": devoir.get("estFacultatif", False),
                "est_en_groupe": devoir.get("estEnGroupe", False),
                "couleur_matiere": devoir.get("service", {}).get("V", {}).get("couleur", ""),
                "libelle_sujet": devoir.get("libelleSujet", ""),
                "libelle_corrige": devoir.get("libelleCorrige", "")
            })

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "matiere", "note", "bareme", "date", "periode",
            "moyenne_matiere", "coefficient", "note_max", "note_min",
            "commentaire", "commentaire_sur_note",
            "est_bonus", "est_facultatif", "est_en_groupe",
            "couleur_matiere", "libelle_sujet", "libelle_corrige"
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ {filename} généré ({len(rows)} lignes)")

def export_services_csv(raw_responses, filename="services.csv"):
    rows = []

    for item in raw_responses:
        data = item.get("data", {})
        if data.get("id") != "DernieresNotes":
            continue

        payload = data.get("dataSec", {}).get("data", {})
        services = payload.get("listeServices", {}).get("V", [])

        for service in services:
            rows.append({
                "matiere": service.get("L", ""),
                "ordre": service.get("ordre", ""),
                "est_service_en_groupe": service.get("estServiceEnGroupe", False),
                "moy_eleve": service.get("moyEleve", {}).get("V", ""),
                "bareme_moy_eleve": service.get("baremeMoyEleve", {}).get("V", ""),
                "moy_classe": service.get("moyClasse", {}).get("V", ""),
                "moy_min": service.get("moyMin", {}).get("V", ""),
                "moy_max": service.get("moyMax", {}).get("V", ""),
                "couleur": service.get("couleur", "")
            })

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "matiere", "ordre", "est_service_en_groupe",
            "moy_eleve", "bareme_moy_eleve", "moy_classe",
            "moy_min", "moy_max", "couleur"
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ {filename} généré ({len(rows)} lignes)")

def export_resume_csv(raw_responses, filename="resume.csv"):
    rows = []

    for item in raw_responses:
        data = item.get("data", {})
        if data.get("id") != "DernieresNotes":
            continue

        payload = data.get("dataSec", {}).get("data", {})

        rows.append({
            "moy_generale": payload.get("moyGenerale", {}).get("V", ""),
            "moy_generale_classe": payload.get("moyGeneraleClasse", {}).get("V", ""),
            "bareme_moy_generale": payload.get("baremeMoyGenerale", {}).get("V", ""),
            "bareme_moy_generale_defaut": payload.get("baremeMoyGeneraleParDefaut", {}).get("V", ""),
            "avec_detail_devoir": payload.get("avecDetailDevoir", False),
            "avec_detail_service": payload.get("avecDetailService", False)
        })

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "moy_generale", "moy_generale_classe",
            "bareme_moy_generale", "bareme_moy_generale_defaut",
            "avec_detail_devoir", "avec_detail_service"
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ {filename} généré ({len(rows)} lignes)")

def go_to_notes(context, page, timeout=30):
    start = time.time()

    # étape 1 : on capture tout, sans parser les notes
    page.on("response", log_all_responses)
    page.on("response", capture)

    clicked = False

    while time.time() - start <= timeout:
        for frame in page.frames:
            btn = frame.locator('#id_77id_44')
            if btn.count() > 0:
                try:
                    btn.wait_for(state="visible", timeout=3000)
                    btn.scroll_into_view_if_needed()
                    page.wait_for_timeout(300)
                    btn.click(timeout=3000)
                    clicked = True
                    print("✅ bouton 'Tout voir' cliqué")
                    break
                except Exception:
                    try:
                        frame.evaluate("document.querySelector('#id_77id_44').click()")
                        clicked = True
                        print("✅ bouton 'Tout voir' cliqué via JS")
                        break
                    except Exception:
                        pass

        if clicked:
            break

        page.wait_for_timeout(500)

        export_notes_csv(raw_responses)
        export_services_csv(raw_responses)
        export_resume_csv(raw_responses)

    if not clicked:
        print("❌ bouton #id_77id_44 introuvable ou non cliquable")
        return False

    # on laisse le temps aux réponses de revenir
    page.wait_for_timeout(5000)

    save_all_responses_to_json()
    save_raw_responses_flat()

    print("✅ dump JSON terminé")
    return True


# 🚀 MAIN
with sync_playwright() as p:
    browser = p.chromium.launch(headless=not DEBUG)
    context = browser.new_context()
    page = context.new_page()

    print("🌐 ouverture URL")
    page.goto(Creds["url"])

    success = run_auth_flow(page, Creds)

    if not success:
        print("❌ login échoué")
        debug_hold(page, "Échec pendant l'authentification")
        context.close()
        browser.close()
        sys.exit(1)

    print("🎯 PRONOTE prêt !")

    notes_success = go_to_notes(context, page)

    if not notes_success:
        print("❌ échec accès notes")
        debug_hold(page, "Échec pendant l'accès aux notes")
        context.close()
        browser.close()
        sys.exit(1)

    print("✅ tout est OK")

    # Optionnel : garder ouvert aussi quand tout marche
    # if DEBUG:
    #     debug_hold(page, "Fin normale du script")

    context.close()
    browser.close()