import time

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