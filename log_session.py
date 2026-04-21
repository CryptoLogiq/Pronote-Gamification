from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir="./profile",  # dossier local
        headless=False
    )

    page = context.new_page()
    page.goto("https://0383301g.index-education.net/pronote/mobile.parent.html")

    input("➡️ Connecte-toi manuellement puis appuie sur Entrée...")

    # à partir d'ici tu es connecté 🎯

    print("✅ Connecté, récupération des données...")

    # exemple interception
    def handle_response(response):
        if "DernieresNotes" in response.url:
            print(response.json())

    page.on("response", handle_response)

    page.reload()

    input("Appuie pour fermer...")
    context.close()