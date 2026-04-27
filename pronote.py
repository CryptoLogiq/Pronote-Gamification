import time

import debug
import export_data
from debug import DEBUG, DEBUG_PRINT

# Variables of module :
RESPONSE_HOOKS_ATTACHED = False

# =========================
# GLOBAL DATA STORAGE
# =========================
raw_responses = []

CURRENT_STUDENT = {
    "name": "",
    "class": ""
}

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

#def selector_dialog_is_open(root):
#    try:
#        dlg = root.locator('[id="IE.Identite.collection.g13_Fenetre"]').first
#        tree = root.locator('div[role="tree"][aria-label="Liste"]').first
#        return dlg.count() > 0 and dlg.is_visible() and tree.count() > 0 and tree.is_visible()
#    except Exception:
#        return False

def selector_dialog_is_open(root):
    try:
        trees = root.locator('div[role="tree"][aria-label="Liste"]')

        for i in range(trees.count()):
            tree = trees.nth(i)
            try:
                if tree.is_visible():
                    return True
            except Exception:
                pass

        return False

    except Exception:
        return False

def ensure_home_page(page, root_url, timeout=15):
    deadline = time.time() + timeout

    home_button_selectors = [
        'a.btn-menu.icon_home[aria-label="Accueil"]',
        'a[role="button"][aria-label="Accueil"]',
        '.btn-menu.icon_home',
        '.icon_home',
    ]

    home_markers = [
        'article.widget.notes:has(span:has-text("Dernières notes"))',
        'article:has(span:has-text("Dernières notes"))',
        'span:has-text("Dernières notes")',
    ]

    while time.time() < deadline:
        root = find_pronote_root(page)

        # 1) Vérifie si on est vraiment sur l'accueil
        # On évite "Espace Parents", car "Détail des notes - Espace Parents"
        # contient aussi ce texte.
        try:
            title = page.title()
            if "Page d'accueil" in title:
                return True
        except Exception:
            pass

        try:
            for marker in home_markers:
                el = root.locator(marker).first
                if el.count() > 0 and el.is_visible():
                    return True
        except Exception:
            pass

        # 2) Si pas sur l'accueil, on clique le bouton Accueil PRONOTE
        clicked = False

        for sel in home_button_selectors:
            try:
                btn = root.locator(sel).first
                if btn.count() > 0 and btn.is_visible():
                    print("🏠 clic bouton Accueil")
                    btn.click(timeout=2000)
                    clicked = True
                    break
            except Exception:
                pass

            try:
                btn = page.locator(sel).first
                if btn.count() > 0 and btn.is_visible():
                    print("🏠 clic bouton Accueil via page")
                    btn.click(timeout=2000)
                    clicked = True
                    break
            except Exception:
                pass

        if clicked:
            page.wait_for_timeout(1800)
            continue

        # 3) Fallback si le bouton Accueil n'est pas trouvé
        try:
            print("⚠️ bouton Accueil introuvable → fallback URL accueil")
            page.goto(root_url, wait_until="domcontentloaded", timeout=10000)
            page.wait_for_timeout(2000)
        except Exception:
            pass

        page.wait_for_timeout(500)

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

    debug.export_state(page, root, prefix="before_select_student", student=student)

    ok = open_selector_if_needed(root, page)
    if not ok:
        debug.export_state(page, root, prefix="selector_not_open", student=student)
        return False

    tree = root.locator('div[role="tree"][aria-label="Liste"]').first
    tree.wait_for(state="visible", timeout=5000)

    items = tree.locator('div[role="treeitem"]')
    count = items.count()
    print(f"🪲 treeitem count = {count}")

    if count <= student["index"]:
        print(f"❌ Index élève invalide : {student}")
        debug.export_state(page, root, prefix="invalid_student_index", student=student)
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
        debug.export_state(page, root, prefix="student_click_failed", student=student)
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
            debug.export_state(page, root, prefix="student_selected_dialog_closed", student=student)
            print(f"✅ Élève sélectionné : {student['name']} ({student['class']})")
            return True

        page.wait_for_timeout(250)

    debug.export_state(page, root, prefix="student_selection_not_confirmed", student=student)
    print(f"⚠️ Clic effectué mais sélection non confirmée : {student['name']}")
    return False

def click_tout_voir_for_current_student(page, timeout=20):
    start = time.time()

    while time.time() - start <= timeout:
        root = find_pronote_root(page)

        try:
            # 1) on ancre sur le widget "Dernières notes", pas sur l'id
            widget = root.locator(
                'article.widget.notes:has(span:has-text("Dernières notes"))'
            ).first

            if widget.count() == 0:
                widget = root.locator(
                    'article:has(span:has-text("Dernières notes"))'
                ).first

            if widget.count() == 0:
                page.wait_for_timeout(500)
                continue

            widget.wait_for(state="visible", timeout=3000)

            student = get_current_student()
            before = export_data.count_dernieres_notes_for_student(raw_responses, student)

            clicked = False

            # 2) bouton "Tout voir" dans ce widget
            targets = [
                widget.locator('button[aria-label="Tout voir"]').first,
                widget.locator('button:has-text("Tout voir")').first,
                widget.locator('header h2.clickable').first,
                widget.locator('span:has-text("Dernières notes")').first,
                widget.locator('.card-container').first,
            ]

            for target in targets:
                try:
                    if target.count() == 0:
                        continue
                except Exception:
                    continue

                try:
                    target.scroll_into_view_if_needed()
                except Exception:
                    pass

                try:
                    target.click(timeout=2500)
                    clicked = True
                    break
                except Exception:
                    pass

                try:
                    target.click(force=True, timeout=2500)
                    clicked = True
                    break
                except Exception:
                    pass

                try:
                    target.focus()
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(250)
                    page.keyboard.press("Space")
                    clicked = True
                    break
                except Exception:
                    pass

                try:
                    target.dispatch_event("click")
                    clicked = True
                    break
                except Exception:
                    pass

            if not clicked:
                page.wait_for_timeout(500)
                continue

            # 3) validation réelle : attendre la requête DernieresNotes
            for _ in range(24):
                now = export_data.count_dernieres_notes_for_student(raw_responses, student)
                if now > before:
                    print(f"✅ bouton 'Tout voir' validé pour {student['name']}")
                    return True
                page.wait_for_timeout(500)

            print(f"⚠️ clic sur le bloc notes effectué mais aucune requête notes pour {student['name']}")
            return False

        except Exception:
            pass

        page.wait_for_timeout(500)

    print(f"❌ Bloc 'Dernières notes' introuvable pour {get_current_student()['name']}")
    return False

def debug_notes_widget(page):
    root = find_pronote_root(page)
    try:
        widget = root.locator('article:has(span:has-text("Dernières notes"))').first
        print("notes widget count:", widget.count())
        if widget.count() > 0:
            print(widget.evaluate("el => el.outerHTML"))
    except Exception as e:
        print("debug_notes_widget error:", e)

# =========================
# MULTI-STUDENTS NOTES FLOW
# =========================
def go_to_notes_all_students(page, home_url=None, timeout_per_student=20):
    attach_response_hooks(page)
    raw_responses.clear()
    root_url = home_url or page.url
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

        # Toujours repartir de la page d'accueil avant une sélection
        if not ensure_home_page(page, root_url, timeout=15):
            print("❌ Impossible de revenir à la page d'accueil")
            return False

        ok = select_student_by_index(page, student)
        if not ok:
            print(f"❌ Impossible de sélectionner {student['name']}")
            return False

        previous_count = export_data.count_dernieres_notes_for_student(raw_responses, student)

        ok = click_tout_voir_for_current_student(page, timeout=timeout_per_student)
        if not ok:
            print(f"❌ Impossible d'ouvrir les notes pour {student['name']}")
            return False

        ok = export_data.wait_for_dernieres_notes(raw_responses, student, previous_count=previous_count, timeout=12)
        if not ok:
            print(f"❌ Aucune réponse DernieresNotes reçue pour {student['name']}")
            return False

        # Très important : revenir à l'accueil avant le prochain élève
        if not ensure_home_page(page, root_url, timeout=15):
            print(f"❌ Impossible de revenir à l'accueil après les notes de {student['name']}")
            return False

    page.wait_for_timeout(1500)

    export_data.save_all_responses_to_json(raw_responses)
    export_data.save_raw_responses_flat(raw_responses)

    export_data.export_notes_csv(raw_responses)
    export_data.export_services_csv(raw_responses)
    export_data.export_resume_csv(raw_responses)
    export_data.export_tableau_notes_eleves_csv(raw_responses)

    print("✅ dump JSON + CSV multi-élèves terminés")
    return True
