from playwright.sync_api import sync_playwright
import pathlib
from datetime import datetime
import time
import json
import sys
import os
import csv


# =========================
# CONFIG / CREDENTIALS
# =========================
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
    def writeFil():
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=4, ensure_ascii=False)

        print("✅ Fichier credentials.json créé")
        print("👉 Remplis-le puis relance le script")
        sys.exit(1)

    if not os.path.exists(filename):
        print("⚠️ credentials.json introuvable → création d'un fichier modèle")
        writeFil()

    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        login = data.get("login", "").strip()
        password = data.get("password", "").strip()
        jj = data.get("jj", "").strip()
        mm = data.get("mm", "").strip()
        aa = data.get("aa", "").strip()
        url = data.get("url", "").strip()

        if set(data.keys()) != required_keys:
            print("❌ credentials.json mal formé")
            writeFil()
            sys.exit(1)

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
            writeFil()
            sys.exit(1)

        return {
            "login": login,
            "password": password,
            "jj": jj,
            "mm": mm,
            "aa": aa,
            "url": url
        }

    except json.JSONDecodeError:
        print("❌ credentials.json invalide (JSON corrompu)")
        sys.exit(1)


Creds = load_credentials()
DEBUG = True


# =========================
# GLOBAL DATA STORAGE
# =========================
raw_responses = []

CURRENT_STUDENT = {
    "name": "",
    "class": ""
}

RESPONSE_HOOKS_ATTACHED = False


# =========================
# DEBUG
# =========================
def _debug_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

def _debug_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

def export_debug_state(page, root, prefix="debug", student=None):
    debug_dir = pathlib.Path("debug_exports")
    debug_dir.mkdir(exist_ok=True)

    stamp = _debug_stamp()
    student_name = ""
    if student:
        student_name = f"_{student.get('name', '').replace(' ', '_')}"

    base = debug_dir / f"{stamp}_{prefix}{student_name}"

    meta = {
        "page_url": "",
        "root_url": "",
        "student": student or {},
        "current_student": get_current_student(),
        "combo_count": 0,
        "tree_count": 0,
        "treeitem_count": 0,
        "tout_voir_count": 0,
        "combo_label": "",
        "combo_expanded": "",
    }

    try:
        meta["page_url"] = page.url
    except Exception:
        pass

    try:
        meta["root_url"] = getattr(root, "url", "")
    except Exception:
        pass

    try:
        combo = root.locator('.ie-btnselecteur[aria-label="Sélectionnez un élève"][role="combobox"]').first
        if combo.count() > 0:
            meta["combo_count"] = root.locator('.ie-btnselecteur[aria-label="Sélectionnez un élève"][role="combobox"]').count()
            try:
                meta["combo_label"] = combo.locator('.bs-libelle').first.inner_text().strip()
            except Exception:
                pass
            try:
                meta["combo_expanded"] = combo.get_attribute("aria-expanded")
            except Exception:
                pass
    except Exception:
        pass

    try:
        meta["tree_count"] = root.locator('div[role="tree"][aria-label="Liste"]').count()
    except Exception:
        pass

    try:
        meta["treeitem_count"] = root.locator('div[role="treeitem"]').count()
    except Exception:
        pass

    try:
        meta["tout_voir_count"] = root.locator('#id_77id_44').count()
    except Exception:
        pass

    # meta json
    with open(f"{base}_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # page html
    try:
        with open(f"{base}_page.html", "w", encoding="utf-8") as f:
            f.write(page.content())
    except Exception:
        pass

    # root html (important si root = frame)
    try:
        with open(f"{base}_root.html", "w", encoding="utf-8") as f:
            f.write(root.content())
    except Exception:
        pass

    # page screenshot
    try:
        page.screenshot(path=f"{base}_page.png", full_page=True)
    except Exception:
        pass

    # root body screenshot
    try:
        body = root.locator("body").first
        if body.count() > 0:
            body.screenshot(path=f"{base}_root.png")
    except Exception:
        pass

    # combo outerHTML
    try:
        combo = root.locator('.ie-btnselecteur[aria-label="Sélectionnez un élève"][role="combobox"]').first
        if combo.count() > 0:
            with open(f"{base}_combo.html", "w", encoding="utf-8") as f:
                f.write(combo.evaluate("el => el.outerHTML"))
    except Exception:
        pass

    # tree outerHTML
    try:
        tree = root.locator('div[role="tree"][aria-label="Liste"]').first
        if tree.count() > 0:
            with open(f"{base}_tree.html", "w", encoding="utf-8") as f:
                f.write(tree.evaluate("el => el.outerHTML"))
    except Exception:
        pass

    print(f"🪲 Debug export créé : {base}")

def dump_treeitems_debug(root):
    try:
        items = root.locator('div[role="treeitem"]')
        count = items.count()
        print(f"🪲 treeitem count = {count}")

        for i in range(count):
            item = items.nth(i)
            name = ""
            klass = ""
            try:
                if item.locator('.titre-principal').count() > 0:
                    name = item.locator('.titre-principal').first.inner_text().strip()
            except Exception:
                pass
            try:
                if item.locator('.infos-supp').count() > 0:
                    klass = item.locator('.infos-supp').first.inner_text().strip()
            except Exception:
                pass

            print(f"   [{i}] {name} ({klass})")
    except Exception as e:
        print("🪲 dump_treeitems_debug error:", e)


# =========================
# STUDENT CONTEXT
# =========================
def set_current_student(name="", klass=""):
    CURRENT_STUDENT["name"] = (name or "").strip()
    CURRENT_STUDENT["class"] = (klass or "").strip()


def get_current_student():
    return {
        "name": CURRENT_STUDENT.get("name", "").strip(),
        "class": CURRENT_STUDENT.get("class", "").strip()
    }


def normalize_student(student_dict=None):
    student_dict = student_dict or {}
    return {
        "name": (student_dict.get("name") or "").strip(),
        "class": (student_dict.get("class") or "").strip()
    }


def student_key(student_dict=None):
    s = normalize_student(student_dict)
    return f"{s['name']}|{s['class']}"


# =========================
# DEBUG HELPERS
# =========================
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


# =========================
# AUTH FLOW HELPERS
# =========================
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
                print("➡️ WAYF eleves ou Parent [case à cocher]")
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

                user = page.locator('input[name="j_username"]')
                pwd = page.locator('input[name="j_password"]')

                user.click()
                user.press("Control+A")
                user.press("Backspace")
                user.fill(creds["login"])
                page.wait_for_timeout(150)

                pwd.click()
                pwd.press("Control+A")
                pwd.press("Backspace")
                pwd.fill(creds["password"])
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
                print("➡️ VERIF identité (date naissance d'un de vos enfants)")
                fill_identity_and_validate(page, creds)
                step += 1
                page.wait_for_timeout(1200)
                continue
            else:
                step += 1
                page.wait_for_timeout(1200)
                continue

        # 4️⃣ PRONOTE
        elif step == 4:
            if (
                "pronote" in page.url.lower() or
                "identifiant" in page.url.lower() or
                creds["url"] in page.url
            ):
                print("✅ PRONOTE OK")
                return True

            print("⚠️ fallback, tentative d'accès direct à PRONOTE en rechargeant l'URL cible")
            page.goto(creds["url"])
            step += 1
            page.wait_for_timeout(1200)
            continue

        # 5️⃣ Validation après fallback
        elif step == 5:
            print(f"🔎 STEP {step} | URL → {page.url}")

            if (
                "pronote" in page.url.lower() or
                "identifiant" in page.url.lower() or
                creds["url"] in page.url
            ):
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


# =========================
# NETWORK CAPTURE
# =========================
def attach_response_hooks(page):
    global RESPONSE_HOOKS_ATTACHED

    if RESPONSE_HOOKS_ATTACHED:
        return

    page.on("response", log_all_responses)
    page.on("response", capture)
    RESPONSE_HOOKS_ATTACHED = True


def capture(response):
    if "appelfonction" not in response.url:
        return

    try:
        raw_responses.append({
            "student": get_current_student(),
            "url": response.url,
            "data": response.json()
        })
    except Exception:
        pass

def log_all_responses(response):
    try:
        if "appelfonction" in response.url:
            print("\n=== URL ===")
            print(response.url)
            print(response.text()[:300])
    except Exception:
        pass

# =========================
# PRONOTE ROOT / STUDENTS
# =========================
def find_pronote_root(page, timeout=10000):
    selector_combo = '.ie-btnselecteur[aria-label="Sélectionnez un élève"][role="combobox"]'
    selector_notes = '#id_77id_44'

    start = time.time()

    while time.time() - start <= timeout / 1000:
        candidates = [page] + list(page.frames)

        # priorité absolue : root avec le sélecteur élève
        for root in candidates:
            try:
                if root.locator(selector_combo).count() > 0:
                    return root
            except Exception:
                pass

        # fallback secondaire seulement si rien d'autre
        for root in candidates:
            try:
                if root.locator(selector_notes).count() > 0:
                    return root
            except Exception:
                pass

        page.wait_for_timeout(250)

    return page

def get_students_in_order(page):
    root = find_pronote_root(page)
    combo_selector = '.ie-btnselecteur[aria-label="Sélectionnez un élève"][role="combobox"]'

    start = time.time()
    while time.time() - start <= 5:
        try:
            if root.locator(combo_selector).count() > 0:
                break
        except Exception:
            pass
        page.wait_for_timeout(250)

    if root.locator(combo_selector).count() == 0:
        print("❌ Sélecteur élève introuvable")
        return []

    combo = root.locator(combo_selector).first
    combo.click()

    tree = root.locator('div[role="tree"][aria-label="Liste"]').first
    tree.wait_for(state="visible", timeout=5000)

    items = tree.locator('div[role="treeitem"]')
    students = []

    for i in range(items.count()):
        item = items.nth(i)

        name = ""
        klass = ""

        if item.locator('.titre-principal').count() > 0:
            name = item.locator('.titre-principal').first.inner_text().strip()

        if item.locator('.infos-supp').count() > 0:
            klass = item.locator('.infos-supp').first.inner_text().strip()

        if name:
            students.append({
                "index": i,
                "name": name,
                "class": klass
            })

    try:
        page.keyboard.press("Escape")
    except Exception:
        pass

    return students

def selector_dialog_is_open(root):
    try:
        dlg = root.locator('[id="IE.Identite.collection.g13_Fenetre"]').first
        tree = root.locator('div[role="tree"][aria-label="Liste"]').first
        return dlg.count() > 0 and dlg.is_visible() and tree.count() > 0 and tree.is_visible()
    except Exception:
        return False


def open_selector_if_needed(root, page):
    if selector_dialog_is_open(root):
        print("🪲 sélecteur déjà ouvert")
        return True

    combo = root.locator('.ie-btnselecteur[aria-label="Sélectionnez un élève"][role="combobox"]').first
    combo.wait_for(state="visible", timeout=5000)

    try:
        combo.click(timeout=3000)
    except Exception:
        try:
            combo.click(force=True, timeout=3000)
        except Exception:
            try:
                combo.dispatch_event("click")
            except Exception:
                print("❌ impossible d'ouvrir le sélecteur élève")
                return False

    for _ in range(20):
        if selector_dialog_is_open(root):
            return True
        page.wait_for_timeout(250)

    print("❌ sélecteur élève non ouvert")
    return False


def select_student_by_index(page, student):
    root = find_pronote_root(page)

    print("\n🪲 --- SELECT STUDENT DEBUG ---")
    print(f"🪲 root_url = {getattr(root, 'url', 'page')}")
    print(f"🪲 target student = {student}")

    export_debug_state(page, root, prefix="before_select_student", student=student)

    ok = open_selector_if_needed(root, page)
    if not ok:
        export_debug_state(page, root, prefix="selector_not_open", student=student)
        return False

    tree = root.locator('div[role="tree"][aria-label="Liste"]').first
    tree.wait_for(state="visible", timeout=5000)

    items = tree.locator('div[role="treeitem"]')
    count = items.count()
    print(f"🪲 treeitem count = {count}")

    if count <= student["index"]:
        print(f"❌ Index élève invalide : {student}")
        export_debug_state(page, root, prefix="invalid_student_index", student=student)
        return False

    item = items.nth(student["index"])

    try:
        print("🪲 TREEITEM HTML:", item.evaluate("el => el.outerHTML"))
    except Exception:
        pass

    clicked = False

    # Le treeitem est le div interne, la ligne cliquable utile est souvent son parent direct
    try:
        row = item.locator("xpath=..").first
        row.scroll_into_view_if_needed()
        print("🪲 try row.click()")
        row.click(timeout=3000)
        clicked = True
    except Exception as e:
        print("🪲 row.click failed:", e)

    if not clicked:
        try:
            row = item.locator("xpath=..").first
            print("🪲 try row.click(force=True)")
            row.click(force=True, timeout=3000)
            clicked = True
        except Exception as e:
            print("🪲 row.click(force=True) failed:", e)

    if not clicked:
        try:
            print("🪲 try JS click on row")
            item.locator("xpath=..").first.evaluate("""
                (el) => {
                    el.dispatchEvent(new MouseEvent('mousedown', {bubbles:true}));
                    el.dispatchEvent(new MouseEvent('mouseup', {bubbles:true}));
                    el.dispatchEvent(new MouseEvent('click', {bubbles:true}));
                }
            """)
            clicked = True
        except Exception as e:
            print("🪲 JS click failed:", e)

    if not clicked:
        print(f"❌ Impossible de sélectionner : {student['name']}")
        export_debug_state(page, root, prefix="student_click_failed", student=student)
        return False

    set_current_student(student["name"], student["class"])

    # Ici on ne fait PAS confiance à aria-expanded
    for n in range(20):
        dialog_open = selector_dialog_is_open(root)

        label = ""
        try:
            label = root.locator('.ie-btnselecteur .bs-libelle').first.inner_text().strip()
        except Exception:
            pass

        print(f"🪲 poll {n}: label={label!r} dialog_open={dialog_open}")

        # Succès si la boîte se ferme
        if not dialog_open:
            page.wait_for_timeout(1200)
            export_debug_state(page, root, prefix="student_selected_dialog_closed", student=student)
            print(f"✅ Élève sélectionné : {student['name']} ({student['class']})")
            return True

        page.wait_for_timeout(250)

    export_debug_state(page, root, prefix="student_selection_not_confirmed", student=student)
    print(f"⚠️ Clic effectué mais sélection non confirmée : {student['name']}")
    return False

def click_tout_voir_for_current_student(page, timeout=20):
    start = time.time()
    selector = '#id_77id_44[aria-label="Tout voir"]'

    while time.time() - start <= timeout:
        root = find_pronote_root(page)

        try:
            btn = root.locator(selector).first

            if btn.count() > 0:
                btn.wait_for(state="visible", timeout=3000)

                try:
                    print("BTN HTML:", btn.evaluate("el => el.outerHTML"))
                except Exception:
                    pass

                export_debug_state(page, root, prefix="before_tout_voir", student=get_current_student())

                try:
                    btn.scroll_into_view_if_needed()
                except Exception:
                    pass

                page.wait_for_timeout(300)

                student = get_current_student()
                before = count_dernieres_notes_for_student(student)

                try:
                    btn.click(timeout=3000)
                except Exception:
                    try:
                        btn.click(force=True, timeout=3000)
                    except Exception:
                        try:
                            btn.focus()
                            page.keyboard.press("Enter")
                            page.wait_for_timeout(300)
                            page.keyboard.press("Space")
                        except Exception:
                            root.evaluate("""
                                () => {
                                    const el = document.querySelector('#id_77id_44[aria-label="Tout voir"]');
                                    if (el) {
                                        el.dispatchEvent(new MouseEvent('mousedown', {bubbles:true}));
                                        el.dispatchEvent(new MouseEvent('mouseup', {bubbles:true}));
                                        el.dispatchEvent(new MouseEvent('click', {bubbles:true}));
                                    }
                                }
                            """)

                export_debug_state(page, root, prefix="after_tout_voir_click", student=get_current_student())

                for _ in range(24):
                    now = count_dernieres_notes_for_student(student)
                    if now > before:
                        print(f"✅ bouton 'Tout voir' validé pour {student['name']}")
                        return True
                    page.wait_for_timeout(500)

                export_debug_state(page, root, prefix="tout_voir_no_notes", student=get_current_student())
                print(f"⚠️ clic effectué mais aucune requête notes pour {student['name']}")
                return False

        except Exception:
            pass

        page.wait_for_timeout(500)

    root = find_pronote_root(page)
    export_debug_state(page, root, prefix="tout_voir_not_found", student=get_current_student())
    print(f"❌ bouton #id_77id_44 introuvable pour {get_current_student()['name']}")
    return False

# =========================
# JSON EXPORTS
# =========================

def count_dernieres_notes_for_student(student):
    count = 0
    for item in raw_responses:
        data = item.get("data", {})
        stu = normalize_student(item.get("student"))

        if (
            data.get("id") == "DernieresNotes" and
            stu["name"] == student["name"] and
            stu["class"] == student["class"]
        ):
            count += 1
    return count


def wait_for_dernieres_notes(student, previous_count=0, timeout=12):
    start = time.time()

    while time.time() - start <= timeout:
        now = count_dernieres_notes_for_student(student)
        if now > previous_count:
            return True
        time.sleep(0.25)

    return False


def save_all_responses_to_json(filename="pronote_raw_responses.json"):
    grouped = {"students": {}}

    for item in raw_responses:
        student = normalize_student(item.get("student"))
        s_key = student_key(student)

        if s_key not in grouped["students"]:
            grouped["students"][s_key] = {
                "student": student,
                "responses": {}
            }

        data = item.get("data", {})
        response_id = data.get("id", "UNKNOWN")

        if response_id not in grouped["students"][s_key]["responses"]:
            grouped["students"][s_key]["responses"][response_id] = []

        grouped["students"][s_key]["responses"][response_id].append({
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


def iter_dernieres_notes_payloads(raw_responses_list):
    for item in raw_responses_list:
        data = item.get("data", {})
        if data.get("id") != "DernieresNotes":
            continue

        payload = data.get("dataSec", {}).get("data", {})
        if not payload:
            continue

        yield normalize_student(item.get("student")), payload


# =========================
# CSV EXPORTS
# =========================
def export_notes_csv(raw_responses_list, filename="notes.csv"):
    rows = []

    for student, payload in iter_dernieres_notes_payloads(raw_responses_list):
        devoirs = payload.get("listeDevoirs", {}).get("V", [])

        for devoir in devoirs:
            rows.append({
                "eleve": student["name"],
                "classe": student["class"],
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
            "eleve", "classe",
            "matiere", "note", "bareme", "date", "periode",
            "moyenne_matiere", "coefficient", "note_max", "note_min",
            "commentaire", "commentaire_sur_note",
            "est_bonus", "est_facultatif", "est_en_groupe",
            "couleur_matiere", "libelle_sujet", "libelle_corrige"
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ {filename} généré ({len(rows)} lignes)")

def export_services_csv(raw_responses_list, filename="services.csv"):
    rows = []

    for student, payload in iter_dernieres_notes_payloads(raw_responses_list):
        services = payload.get("listeServices", {}).get("V", [])

        for service in services:
            rows.append({
                "eleve": student["name"],
                "classe": student["class"],
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
            "eleve", "classe",
            "matiere", "ordre", "est_service_en_groupe",
            "moy_eleve", "bareme_moy_eleve", "moy_classe",
            "moy_min", "moy_max", "couleur"
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ {filename} généré ({len(rows)} lignes)")

def export_resume_csv(raw_responses_list, filename="resume.csv"):
    rows = []

    for student, payload in iter_dernieres_notes_payloads(raw_responses_list):
        rows.append({
            "eleve": student["name"],
            "classe": student["class"],
            "moy_generale": payload.get("moyGenerale", {}).get("V", ""),
            "moy_generale_classe": payload.get("moyGeneraleClasse", {}).get("V", ""),
            "bareme_moy_generale": payload.get("baremeMoyGenerale", {}).get("V", ""),
            "bareme_moy_generale_defaut": payload.get("baremeMoyGeneraleParDefaut", {}).get("V", ""),
            "avec_detail_devoir": payload.get("avecDetailDevoir", False),
            "avec_detail_service": payload.get("avecDetailService", False)
        })

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "eleve", "classe",
            "moy_generale", "moy_generale_classe",
            "bareme_moy_generale", "bareme_moy_generale_defaut",
            "avec_detail_devoir", "avec_detail_service"
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ {filename} généré ({len(rows)} lignes)")

# =========================
# MULTI-STUDENTS NOTES FLOW
# =========================
def go_to_notes_all_students(context, page, timeout_per_student=20):
    attach_response_hooks(page)
    raw_responses.clear()

    root = find_pronote_root(page)
    print("ROOT URL:", getattr(root, "url", "page"))
    print("combo count:", root.locator('.ie-btnselecteur[aria-label="Sélectionnez un élève"][role="combobox"]').count())
    print("tout voir count:", root.locator('#id_77id_44').count())

    students = get_students_in_order(page)

    if not students:
        print("❌ Aucun élève détecté")
        return False

    print("👨‍🎓 Élèves détectés dans l'ordre :")
    for s in students:
        print(f"   - {s['name']} ({s['class']})")

    for student in students:
        print(f"\n➡️ Traitement de {student['name']} ({student['class']})")

        ok = select_student_by_index(page, student)
        if not ok:
            print(f"❌ Impossible de sélectionner {student['name']}")
            return False

        previous_count = count_dernieres_notes_for_student(student)

        ok = click_tout_voir_for_current_student(page, timeout=timeout_per_student)
        if not ok:
            print(f"❌ Impossible d'ouvrir les notes pour {student['name']}")
            return False

        ok = wait_for_dernieres_notes(student, previous_count=previous_count, timeout=12)
        if not ok:
            print(f"❌ Aucune réponse DernieresNotes reçue pour {student['name']}")
            return False

    page.wait_for_timeout(1500)

    save_all_responses_to_json()
    save_raw_responses_flat()

    export_notes_csv(raw_responses)
    export_services_csv(raw_responses)
    export_resume_csv(raw_responses)

    print("✅ dump JSON + CSV multi-élèves terminés")
    return True


# =========================
# MAIN
# =========================
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

    notes_success = go_to_notes_all_students(context, page)

    if not notes_success:
        print("❌ échec accès notes")
        debug_hold(page, "Échec pendant l'accès aux notes")
        context.close()
        browser.close()
        sys.exit(1)

    print("✅ tout est OK")

    # Décommente si tu veux garder la fenêtre ouverte même quand tout marche
    # if DEBUG:
    #     debug_hold(page, "Fin normale du script")

    context.close()
    browser.close()