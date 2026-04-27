import time
from ui_timing import ui_pause, TYPE_DELAY
import html
import pathlib
from datetime import datetime
from urllib.parse import urlparse

# =========================
# AUTH FLOW HELPERS
# =========================

def is_real_pronote_url(page):
    try:
        parsed = urlparse(page.url.lower())
    except Exception:
        return False

    return (
        "index-education.net" in parsed.netloc
        and "/pronote/" in parsed.path
        and "mobile.parent.html" in parsed.path
    )


def has_pronote_ui(page):
    selectors = [
        '.ie-btnselecteur[aria-label="Sélectionnez un élève"][role="combobox"]',
        'article.widget.notes:has(span:has-text("Dernières notes"))',
        'article:has(span:has-text("Dernières notes"))',
        'a.btn-menu.icon_home[aria-label="Accueil"]',
    ]

    candidates = [page] + list(page.frames)

    for root in candidates:
        for selector in selectors:
            try:
                el = root.locator(selector).first
                if el.count() > 0:
                    return True
            except Exception:
                pass

    return False


def is_pronote_ready(page):
    """
    Valide qu'on est vraiment sur PRONOTE,
    pas juste sur une URL CAS qui contient 'pronote' dans le paramètre service.
    """

    if not is_real_pronote_url(page):
        return False

    try:
        if "identifiant=" in page.url.lower():
            return True
    except Exception:
        pass

    return has_pronote_ui(page)


def wait_for_pronote_ready(page, timeout=20):
    start = time.time()

    while time.time() - start <= timeout:
        if is_pronote_ready(page):
            return True

        ui_pause(page, "poll")

    return False

def detect_auth_error(page):
    """
    Retourne :
    - None
    - bad_credentials
    - account_blocked
    - access_denied
    - temporary_refused
    """

    try:
        body_text = page.locator("body").inner_text().lower()
    except Exception:
        return None

    bad_credentials_markers = [
        "identifiant ou mot de passe incorrect",
        "identifiant incorrect",
        "mot de passe incorrect",
        "erreur d'authentification"
    ]

    account_blocked_markers = [
        "compte bloqué",
        "compte bloque",
        "compte désactivé",
        "compte desactivé",
        "trop de tentatives"
    ]

    access_denied_markers = [
        "vous ne pouvez pas accéder",
        "vous ne pouvez pas acceder",
        "accès non autorisé",
        "acces non autorisé",
        "accès refusé",
        "acces refusé"
    ]

    temporary_refused_markers = [
        "connexion refusée",
        "connexion refusee",
        "service indisponible",
        "erreur temporaire",
        "maintenance",
        "veuillez réessayer",
        "veuillez reessayer"
    ]

    if any(marker in body_text for marker in bad_credentials_markers):
        return "bad_credentials"

    if any(marker in body_text for marker in account_blocked_markers):
        return "account_blocked"

    if any(marker in body_text for marker in access_denied_markers):
        return "access_denied"

    if any(marker in body_text for marker in temporary_refused_markers):
        return "temporary_refused"

    return None

def show_auth_error_page(page, error_type, details="", retry_count=None, max_retries=None):
    """
    Affiche une page HTML locale dans le navigateur Playwright
    pour expliquer clairement l'erreur d'authentification.
    """

    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    try:
        current_url = page.url
    except Exception:
        current_url = ""

    messages = {
        "bad_credentials": {
            "title": "Identifiant ou mot de passe incorrect",
            "level": "danger",
            "message": (
                "Le portail indique que l'identifiant ou le mot de passe est incorrect. "
                "Le script s'arrête immédiatement pour éviter de multiplier les tentatives "
                "et risquer de bloquer le compte."
            ),
            "action": (
                "Vérifie le fichier credentials.json, puis relance le script. "
                "Attention aux majuscules, espaces copiés/collés, et caractères spéciaux."
            ),
        },
        "account_blocked": {
            "title": "Compte bloqué ou désactivé",
            "level": "danger",
            "message": (
                "Le portail indique que le compte semble bloqué ou désactivé."
            ),
            "action": (
                "Ne relance pas en boucle. Il faut vérifier l'accès manuellement "
                "ou contacter le support / l'établissement si nécessaire."
            ),
        },
        "access_denied": {
            "title": "Accès refusé",
            "level": "danger",
            "message": (
                "Le portail indique que l'accès n'est pas autorisé pour ce compte."
            ),
            "action": (
                "Vérifie que le bon profil est sélectionné, par exemple Parent Responsable, "
                "et que le compte a bien accès à PRONOTE."
            ),
        },
        "temporary_refused": {
            "title": "Connexion temporairement refusée",
            "level": "warning",
            "message": (
                "La connexion semble refusée temporairement. "
                "Le script va attendre un peu puis refaire une tentative depuis le début."
            ),
            "action": (
                "Patiente. Si l'erreur revient plusieurs fois, le service est peut-être saturé "
                "ou temporairement indisponible."
            ),
        },
        "temporary_refused_max": {
            "title": "Trop de refus temporaires",
            "level": "danger",
            "message": (
                "La connexion a été refusée plusieurs fois malgré les nouvelles tentatives."
            ),
            "action": (
                "Le script s'arrête pour éviter d'insister. Réessaie plus tard."
            ),
        },
        "timeout": {
            "title": "Timeout pendant l'authentification",
            "level": "warning",
            "message": (
                "Le script a dépassé le temps maximum prévu pendant l'authentification."
            ),
            "action": (
                "La page a peut-être changé, ou le portail a mis trop longtemps à répondre."
            ),
        },
        "pronote_not_ready": {
            "title": "PRONOTE non atteint",
            "level": "danger",
            "message": (
                "L'authentification n'a pas abouti jusqu'à la vraie page PRONOTE. "
                "Le script était encore sur le portail CAS / EduConnect ou sur une page intermédiaire."
            ),
            "action": (
                "Vérifie manuellement si EduConnect demande une validation supplémentaire, "
                "si la page met plus longtemps à rediriger, ou si le service PRONOTE est temporairement indisponible."
            ),
        },
    }

    info = messages.get(error_type, {
        "title": "Erreur inconnue",
        "level": "danger",
        "message": "Une erreur non identifiée est survenue.",
        "action": "Regarde la console et les exports debug si disponibles.",
    })

    retry_html = ""

    if retry_count is not None and max_retries is not None:
        retry_html = f"""
        <div class="retry">
            Tentative : <strong>{retry_count}</strong> / <strong>{max_retries}</strong>
        </div>
        """

    safe_title = html.escape(info["title"])
    safe_message = html.escape(info["message"])
    safe_action = html.escape(info["action"])
    safe_details = html.escape(details or "")
    safe_url = html.escape(current_url or "")

    html_content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Erreur Pronote - {safe_title}</title>
    <style>
        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f4f6f8;
            color: #1f2933;
        }}

        .page {{
            max-width: 900px;
            margin: 60px auto;
            padding: 30px;
        }}

        .card {{
            background: white;
            border-radius: 16px;
            padding: 32px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.12);
            border-left: 8px solid #d97706;
        }}

        .card.danger {{
            border-left-color: #dc2626;
        }}

        .card.warning {{
            border-left-color: #d97706;
        }}

        h1 {{
            margin-top: 0;
            font-size: 28px;
        }}

        .badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            background: #fee2e2;
            color: #991b1b;
            font-weight: bold;
            font-size: 13px;
            margin-bottom: 18px;
        }}

        .warning .badge {{
            background: #fef3c7;
            color: #92400e;
        }}

        .section {{
            margin-top: 24px;
        }}

        .label {{
            font-weight: bold;
            color: #4b5563;
            margin-bottom: 6px;
        }}

        .box {{
            background: #f9fafb;
            border-radius: 10px;
            padding: 14px;
            border: 1px solid #e5e7eb;
            word-break: break-word;
        }}

        .retry {{
            margin-top: 18px;
            padding: 12px;
            background: #fff7ed;
            border: 1px solid #fed7aa;
            border-radius: 10px;
        }}

        .footer {{
            margin-top: 26px;
            font-size: 13px;
            color: #6b7280;
        }}
    </style>
</head>
<body>
    <div class="page">
        <div class="card {html.escape(info["level"])}">
            <div class="badge">PRONOTE / EDUCONNECT</div>

            <h1>{safe_title}</h1>

            <div class="section">
                <div class="label">Explication</div>
                <div class="box">{safe_message}</div>
            </div>

            <div class="section">
                <div class="label">Action conseillée</div>
                <div class="box">{safe_action}</div>
            </div>

            {retry_html}

            <div class="section">
                <div class="label">URL au moment de l'erreur</div>
                <div class="box">{safe_url}</div>
            </div>

            <div class="section">
                <div class="label">Détails techniques</div>
                <div class="box">{safe_details if safe_details else "Aucun détail supplémentaire."}</div>
            </div>

            <div class="footer">
                Généré automatiquement le {html.escape(now)}.
            </div>
        </div>
    </div>
</body>
</html>
"""

    try:
        debug_dir = pathlib.Path("debug_exports")
        debug_dir.mkdir(exist_ok=True)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = debug_dir / f"auth_error_{error_type}_{stamp}.html"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"🧾 Page d'erreur sauvegardée : {filename}")

    except Exception as e:
        print("⚠️ impossible de sauvegarder la page d'erreur :", e)

    try:
        page.set_content(html_content, wait_until="domcontentloaded")
        print("🧾 Page d'erreur affichée dans le navigateur")
    except Exception as e:
        print("⚠️ impossible d'afficher la page d'erreur :", e)

def fill_field_slow(page, field, value):
    field.click()
    ui_pause(page, "after_click")

    field.press("Control+A")
    ui_pause(page, "tiny")

    field.press("Backspace")
    ui_pause(page, "tiny")

    page.keyboard.type(value, delay=TYPE_DELAY)
    ui_pause(page, "after_input")

    page.keyboard.press("Tab")
    ui_pause(page, "tiny")


def fill_identity_and_validate(page, creds):
    day = page.locator('input[name="jour"]')
    month = page.locator('input[name="mois"]')
    year = page.locator('input[name="annee"]')

    fill_field_slow(page, day, creds["jj"])
    fill_field_slow(page, month, creds["mm"])
    fill_field_slow(page, year, creds["aa"])

    ui_pause(page, "after_input", label="après date naissance")

    btn = page.locator('button:has-text("Confirmer")')

    try:
        btn.wait_for(state="visible", timeout=5000)
        btn.hover()
        ui_pause(page, "before_action")

        btn.click(timeout=3000)
        ui_pause(page, "after_submit", label="confirmation identité")

    except Exception:
        page.mouse.move(50, 50)
        ui_pause(page, "tiny")

        page.mouse.click(50, 50)
        ui_pause(page, "after_click")

        btn.click(force=True)
        ui_pause(page, "after_submit", label="confirmation identité force")


def run_auth_flow(page, creds, timeout=180, max_refused_retries=2):
    start = time.time()
    step = 0
    loop = 0
    refused_retries = 0

    while True:
        if time.time() - start > timeout:
            print("❌ TIMEOUT GLOBAL")
            show_auth_error_page(
                page,
                "timeout",
                details=f"Timeout global dépassé pendant l'étape {step}."
            )
            return False

        ui_pause(page, "poll")
        print(f"🔎 STEP {step} | URL → {page.url}")

        auth_error = detect_auth_error(page)

        if auth_error == "bad_credentials":
            print("❌ Identifiant ou mot de passe incorrect")
            print("🛑 Arrêt immédiat pour éviter de bloquer le compte")
            show_auth_error_page(
                page,
                "bad_credentials",
                details="Erreur détectée dans le texte de la page après tentative de connexion."
            )
            return False

        if auth_error == "account_blocked":
            print("❌ Compte bloqué ou désactivé")
            print("🛑 Arrêt immédiat")
            show_auth_error_page(
                page,
                "account_blocked",
                details="Erreur détectée dans le texte de la page."
            )
            return False

        if auth_error == "access_denied":
            print("❌ Accès refusé / accès non autorisé")
            print("🛑 Arrêt immédiat")
            show_auth_error_page(
                page,
                "access_denied",
                details="Erreur détectée dans le texte de la page."
            )
            return False

        if auth_error == "temporary_refused":
            refused_retries += 1

            print(f"⚠️ Connexion refusée temporairement ({refused_retries}/{max_refused_retries})")

            if refused_retries > max_refused_retries:
                print("❌ Trop de refus temporaires, arrêt du script")
                show_auth_error_page(
                    page,
                    "temporary_refused_max",
                    details="Nombre maximum de nouvelles tentatives atteint.",
                    retry_count=refused_retries - 1,
                    max_retries=max_refused_retries
                )
                return False

            show_auth_error_page(
                page,
                "temporary_refused",
                details="Le script va attendre puis relancer l'authentification depuis le début.",
                retry_count=refused_retries,
                max_retries=max_refused_retries
            )

            ui_pause(page, "retry_refused", label="connexion refusée, attente avant nouvelle tentative")

            try:
                print("🔁 Nouvelle tentative depuis le début")
                page.goto(creds["url"], wait_until="domcontentloaded", timeout=15000)
                ui_pause(page, "page_change", label="rechargement URL de départ")
            except Exception as e:
                print("⚠️ échec reload URL après connexion refusée :", e)

            step = 0
            loop = 0
            continue

        # 0️⃣ WAYF
        if step == 0:
            if page.locator('#idp-EDU').count() > 0:
                print("➡️ WAYF eleves ou Parent [case à cocher]")

                page.locator('label[for="idp-EDU"]').click()
                ui_pause(page, "after_checkbox", label="case EDU")

                page.locator('#button-submit').click()
                ui_pause(page, "page_change", label="validation WAYF")

                step += 1
                continue

        # 1️⃣ PROFILE
        elif step == 1:
            btn = page.locator('#bouton_responsable')

            if btn.count() > 0:
                print("➡️ PROFILE [Parent Responsable]")
                try:
                    btn.click(timeout=2000)
                    ui_pause(page, "after_click", label="profil responsable")
                except Exception:
                    page.evaluate("document.querySelector('#bouton_responsable').click()")
                    ui_pause(page, "after_click", label="profil responsable JS")

                step += 1
                ui_pause(page, "poll")
                continue

        # 2️⃣ LOGIN
        elif step == 2:
            if page.locator('input[name="j_username"]').count() > 0:
                print("➡️ LOGIN + MDP")

                user = page.locator('input[name="j_username"]')
                pwd = page.locator('input[name="j_password"]')

                fill_field_slow(page, user, creds["login"])
                fill_field_slow(page, pwd, creds["password"])

                btn = page.locator('#bouton_valider')

                if btn.count() > 0:
                    print("➡️ LOGIN submit")
                    try:
                        btn.wait_for(state="visible", timeout=5000)
                        btn.scroll_into_view_if_needed()
                        btn.click(timeout=3000)
                        ui_pause(page, "after_submit", label="login submit")
                    except Exception:
                        print("⚠️ click normal échoué → force")
                        try:
                            btn.click(force=True)
                            page.keyboard.press("Enter")
                        except Exception:
                            print("⚠️ force échoué → JS click")
                            page.evaluate("document.querySelector('#bouton_valider').click()")

                step += 1
                ui_pause(page, "page_change")
                continue

        # 3️⃣ VERIFY (optionnel)
        elif step == 3:
            if page.locator('input[name="jour"]').count() > 0:
                print("➡️ VERIF identité (date naissance d'un de vos enfants)")
                fill_identity_and_validate(page, creds)
                step += 1
                ui_pause(page, "page_change")
                continue
            else:
                step += 1
                ui_pause(page, "page_change")
                continue

        # 4️⃣ PRONOTE
        elif step == 4:
            print("➡️ Attente arrivée réelle sur PRONOTE")

            if wait_for_pronote_ready(page, timeout=20):
                print("✅ PRONOTE OK")
                return True

            print("⚠️ PRONOTE non atteint après attente")

            if loop == 0:
                loop += 1

                try:
                    print("🔁 Nouvelle tentative depuis le début du parcours")
                    page.goto(creds["url"], wait_until="domcontentloaded", timeout=15000)
                    ui_pause(page, "page_change", label="retour URL de départ")
                except Exception as e:
                    print("⚠️ échec retour URL de départ :", e)

                step = 0
                continue

            show_auth_error_page(
                page,
                "pronote_not_ready",
                details=f"Après authentification, PRONOTE n'a pas été atteint. URL actuelle : {page.url}"
            )
            return False

        ui_pause(page, "poll")