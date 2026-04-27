import random
import time


# =========================
# UI TIMING CONFIG
# =========================
TYPE_DELAY = 90  # délai entre chaque caractère tapé au clavier

PAUSES = {
    # Petites pauses techniques
    "poll": 300,
    "tiny": 250,

    # Actions utilisateur
    "before_action": 350,
    "after_click": 900,
    "after_input": 650,
    "after_checkbox": 1000,
    "after_select": 1200,

    # Navigation / changement de page
    "page_change": 2200,
    "after_home": 2200,
    "after_submit": 1800,

    # Pronote spécifique
    "after_student_change": 1800,
    "after_notes_open": 1800,
    "between_students": 1600,

    # Exports
    "after_json_export": 900,
    "after_csv_export": 900,

    # Fallback
    "default": 1000,

    # Retry
    "retry_refused": 15000,
}


def ui_pause(page=None, kind="default", ms=None, label=""):
    """
    Pause centralisée.
    - page fourni  -> pause Playwright : page.wait_for_timeout(ms)
    - page absent  -> pause Python : time.sleep(...)
    - kind permet de choisir un délai dans PAUSES
    - léger jitter pour éviter un rythme trop mécanique
    """

    base_ms = ms if ms is not None else PAUSES.get(kind, PAUSES["default"])

    jitter = int(base_ms * 0.20)
    jitter = min(jitter, 350)

    final_ms = base_ms + random.randint(-jitter, jitter)
    final_ms = max(100, final_ms)

    try:
        import debug
        show_pause_log = debug.DEBUG_PRINT
    except Exception:
        show_pause_log = False

    if label and show_pause_log:
        print(f"⏳ pause {label} : {final_ms} ms")

    if page is not None:
        page.wait_for_timeout(final_ms)
    else:
        time.sleep(final_ms / 1000)