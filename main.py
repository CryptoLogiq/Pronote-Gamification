from playwright.sync_api import sync_playwright
import sys

import debug
import login
import pronote
import settings


def ui_pause(page, ms=1200):
    page.wait_for_timeout(ms)


def main():
    creds = settings.load_credentials()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not debug.DEBUG)
        context = browser.new_context()
        page = context.new_page()

        try:
            print("🌐 ouverture URL")
            page.goto(creds["url"])

            success = login.run_auth_flow(page, creds)

            if not success:
                print("❌ login échoué")
                debug.hold(page, "Échec pendant l'authentification")
                sys.exit(1)

            print("🎯 PRONOTE prêt !")

            notes_success = pronote.go_to_notes_all_students(page, home_url=creds["url"])

            if not notes_success:
                print("❌ échec accès notes")
                debug.hold(page, "Échec pendant l'accès aux notes")
                sys.exit(1)

            print("✅ tout est OK")

            # Décommente si tu veux garder la fenêtre ouverte même quand tout marche
            # if debug.DEBUG:
            #     debug.hold(page, "Fin normale du script")

        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    main()