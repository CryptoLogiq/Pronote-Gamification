import json
import sys
import os


# =========================
# SETTINGS / CREDENTIALS
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

    def write_file():
        if os.path.exists(filename):
            backup = filename + ".bak"

            try:
                os.replace(filename, backup)
                print(f"⚠️ Ancien credentials.json sauvegardé dans : {backup}")
            except Exception:
                print("⚠️ Impossible de sauvegarder l'ancien credentials.json")

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=4, ensure_ascii=False)

        print("✅ Fichier credentials.json créé")
        print("👉 Remplis-le puis relance le script")
        sys.exit(1)

    if not os.path.exists(filename):
        print("⚠️ credentials.json introuvable → création d'un fichier modèle")
        write_file()

    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        if set(data.keys()) != required_keys:
            print("❌ credentials.json mal formé")
            write_file()

        login = data.get("login", "").strip()
        password = data.get("password", "").strip()
        jj = data.get("jj", "").strip()
        mm = data.get("mm", "").strip()
        aa = data.get("aa", "").strip()
        url = data.get("url", "").strip()

        if (
            not login
            or not password
            or not jj
            or not mm
            or not aa
            or not url
            or login == template["login"]
            or password == template["password"]
            or jj == template["jj"]
            or mm == template["mm"]
            or aa == template["aa"]
            or url == template["url"]
        ):
            print("❌ credentials.json non configuré correctement")
            print("👉 Remplis les champs login / password / jj / mm / aa / url")
            write_file()

        return {
            "login": login,
            "password": password,
            "jj": jj,
            "mm": mm,
            "aa": aa,
            "url": url,
        }

    except json.JSONDecodeError:
        print("❌ credentials.json invalide (JSON corrompu)")
        sys.exit(1)
