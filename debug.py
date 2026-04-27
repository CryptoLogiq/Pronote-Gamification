from datetime import datetime
import pathlib
import json

# =========================
# DEBUG for DEV
# =========================
DEBUG = False

# =========================
# Debug output if needed
# =========================
DEBUG_PRINT = False


def _debug_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _get_current_student_safe():
    """Évite un import circulaire au chargement du module debug."""
    try:
        import pronote
        return pronote.get_current_student()
    except Exception:
        return {"name": "", "class": ""}


def export_state(page, root, prefix="debug", student=None):
    if not DEBUG_PRINT:
        return

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
        "current_student": _get_current_student_safe(),
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
        combo_selector = '.ie-btnselecteur[aria-label="Sélectionnez un élève"][role="combobox"]'
        combo = root.locator(combo_selector).first
        if combo.count() > 0:
            meta["combo_count"] = root.locator(combo_selector).count()
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

    with open(f"{base}_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    try:
        with open(f"{base}_page.html", "w", encoding="utf-8") as f:
            f.write(page.content())
    except Exception:
        pass

    try:
        with open(f"{base}_root.html", "w", encoding="utf-8") as f:
            f.write(root.content())
    except Exception:
        pass

    try:
        page.screenshot(path=f"{base}_page.png", full_page=True)
    except Exception:
        pass

    try:
        body = root.locator("body").first
        if body.count() > 0:
            body.screenshot(path=f"{base}_root.png")
    except Exception:
        pass

    try:
        combo = root.locator('.ie-btnselecteur[aria-label="Sélectionnez un élève"][role="combobox"]').first
        if combo.count() > 0:
            with open(f"{base}_combo.html", "w", encoding="utf-8") as f:
                f.write(combo.evaluate("el => el.outerHTML"))
    except Exception:
        pass

    try:
        tree = root.locator('div[role="tree"][aria-label="Liste"]').first
        if tree.count() > 0:
            with open(f"{base}_tree.html", "w", encoding="utf-8") as f:
                f.write(tree.evaluate("el => el.outerHTML"))
    except Exception:
        pass

    print(f"🪲 Debug export créé : {base}")


def dump_treeitems_debug(root):
    if not DEBUG_PRINT:
        return

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


def hold(page, reason=""):
    if not DEBUG:
        return

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
