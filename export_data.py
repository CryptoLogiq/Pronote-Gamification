import json
import csv
import time
import pathlib
import re
from datetime import datetime


# =========================
# STUDENT HELPERS
# =========================
def normalize_student(student_dict=None):
    student_dict = student_dict or {}
    return {
        "name": (student_dict.get("name") or "").strip(),
        "class": (student_dict.get("class") or "").strip(),
    }


def student_key(student_dict=None):
    s = normalize_student(student_dict)
    return f"{s['name']}|{s['class']}"


# =========================
# JSON EXPORTS
# =========================
def count_dernieres_notes_for_student(raw_responses_list, student):
    count = 0
    target = normalize_student(student)

    for item in raw_responses_list:
        data = item.get("data", {})
        stu = normalize_student(item.get("student"))

        if (
            data.get("id") == "DernieresNotes"
            and stu["name"] == target["name"]
            and stu["class"] == target["class"]
        ):
            count += 1

    return count


def wait_for_dernieres_notes(raw_responses_list, student, previous_count=0, timeout=12):
    start = time.time()

    while time.time() - start <= timeout:
        now = count_dernieres_notes_for_student(raw_responses_list, student)
        if now > previous_count:
            return True
        time.sleep(0.25)

    return False


def save_all_responses_to_json(raw_responses_list, filename="pronote_raw_responses.json"):
    grouped = {"students": {}}

    for item in raw_responses_list:
        student = normalize_student(item.get("student"))
        s_key = student_key(student)

        if s_key not in grouped["students"]:
            grouped["students"][s_key] = {
                "student": student,
                "responses": {},
            }

        data = item.get("data", {})
        response_id = data.get("id", "UNKNOWN")

        if response_id not in grouped["students"][s_key]["responses"]:
            grouped["students"][s_key]["responses"][response_id] = []

        grouped["students"][s_key]["responses"][response_id].append({
            "url": item.get("url"),
            "data": data,
        })

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(grouped, f, indent=2, ensure_ascii=False)

    print(f"✅ JSON brut sauvegardé dans : {filename}")


def save_raw_responses_flat(raw_responses_list, filename="pronote_raw_responses_flat.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(raw_responses_list, f, indent=2, ensure_ascii=False)

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
def _export_date():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _csv_value(value):
    if value is None:
        return ""

    return str(value).strip()


def _row_key(row, fieldnames):
    return tuple(
        _csv_value(row.get(fieldname, ""))
        for fieldname in fieldnames
    )


def _deduplicate_rows(rows, key_fieldnames, existing_keys=None):
    existing_keys = existing_keys or set()
    seen_keys = set()
    unique_rows = []

    for row in rows:
        key = _row_key(row, key_fieldnames)

        if key in existing_keys or key in seen_keys:
            continue

        seen_keys.add(key)
        unique_rows.append(row)

    return unique_rows


def _dedupe_fieldnames(fieldnames, dedupe_fieldnames=None):
    if dedupe_fieldnames:
        return [fieldname for fieldname in dedupe_fieldnames if fieldname in fieldnames]

    return [fieldname for fieldname in fieldnames if fieldname != "date_export"]


def _append_csv_rows(
    filename,
    fieldnames,
    rows,
    delimiter=",",
    encoding="utf-8",
    dedupe_fieldnames=None,
):
    path = pathlib.Path(filename)
    write_header = not path.exists() or path.stat().st_size == 0
    existing_rows = []

    if not write_header:
        with open(path, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            existing_fieldnames = reader.fieldnames or []
            existing_rows = list(reader)

        if existing_fieldnames != fieldnames:
            merged_fieldnames = list(fieldnames)

            for existing_fieldname in existing_fieldnames:
                if existing_fieldname not in merged_fieldnames:
                    merged_fieldnames.append(existing_fieldname)

            with open(path, "w", newline="", encoding=encoding) as f:
                writer = csv.DictWriter(f, fieldnames=merged_fieldnames, delimiter=delimiter)
                writer.writeheader()
                writer.writerows(existing_rows)

            fieldnames = merged_fieldnames

        key_fieldnames = _dedupe_fieldnames(fieldnames, dedupe_fieldnames)
        deduplicated_existing_rows = _deduplicate_rows(existing_rows, key_fieldnames)

        if len(deduplicated_existing_rows) != len(existing_rows):
            with open(path, "w", newline="", encoding=encoding) as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
                writer.writeheader()
                writer.writerows(deduplicated_existing_rows)

            existing_rows = deduplicated_existing_rows

    key_fieldnames = _dedupe_fieldnames(fieldnames, dedupe_fieldnames)
    existing_keys = {
        _row_key(existing_row, key_fieldnames)
        for existing_row in existing_rows
    }
    rows_to_write = _deduplicate_rows(
        rows,
        key_fieldnames,
        existing_keys=existing_keys,
    )

    file_encoding = encoding if write_header else "utf-8"

    with open(path, "a", newline="", encoding=file_encoding) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)

        if write_header:
            writer.writeheader()

        writer.writerows(rows_to_write)

    return len(rows_to_write), len(rows) - len(rows_to_write)


def export_notes_csv(raw_responses_list, filename="notes.csv"):
    rows = []
    date_export = _export_date()

    for student, payload in iter_dernieres_notes_payloads(raw_responses_list):
        devoirs = payload.get("listeDevoirs", {}).get("V", [])

        for devoir in devoirs:
            rows.append({
                "date_export": date_export,
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
                "libelle_corrige": devoir.get("libelleCorrige", ""),
            })

    fieldnames = [
        "date_export",
        "eleve", "classe",
        "matiere", "note", "bareme", "date", "periode",
        "moyenne_matiere", "coefficient", "note_max", "note_min",
        "commentaire", "commentaire_sur_note",
        "est_bonus", "est_facultatif", "est_en_groupe",
        "couleur_matiere", "libelle_sujet", "libelle_corrige",
    ]

    added_count, duplicate_count = _append_csv_rows(
        filename,
        fieldnames,
        rows,
        dedupe_fieldnames=[
            "eleve",
            "classe",
            "matiere",
            "date",
            "note",
            "bareme",
            "libelle_sujet",
        ],
    )

    print(f"✅ {filename} alimenté ({added_count} lignes ajoutées, {duplicate_count} doublons ignorés)")

def _text(value):
    if value is None:
        return ""
    return str(value).strip()


def _clean_matiere(label):
    label = _text(label)

    if ">" in label:
        label = label.split(">")[-1].strip()

    return label


def _clean_note(value):
    return _text(value).lstrip("|").strip()


def _format_note_for_table(devoir):
    note = _clean_note(devoir.get("note", {}).get("V", ""))
    bareme = _clean_note(devoir.get("bareme", {}).get("V", ""))
    date = _text(devoir.get("date", {}).get("V", ""))
    coef = _text(devoir.get("coefficient", ""))
    commentaire = _text(devoir.get("commentaire", ""))

    if note and bareme:
        result = f"{note}/{bareme}"
    elif note:
        result = note
    else:
        return ""

    details = []

    if date:
        details.append(date)

    if coef:
        details.append(f"coef {coef}")

    if commentaire:
        details.append(commentaire)

    if details:
        result += " (" + ", ".join(details) + ")"

    return result


def export_tableau_notes_eleves_csv(raw_responses_list, filename="tableau_notes_eleves.csv"):
    date_export = _export_date()
    students = []
    matieres = []
    data = {}
    moyennes_generales = {}

    for student, payload in iter_dernieres_notes_payloads(raw_responses_list):
        student_label = f"{student['name']} ({student['class']})"

        if student_label not in students:
            students.append(student_label)

        moy_generale = _text(payload.get("moyGenerale", {}).get("V", ""))
        if moy_generale:
            moyennes_generales[student_label] = moy_generale

        services = payload.get("listeServices", {}).get("V", [])

        for service in services:
            matiere = _clean_matiere(service.get("L", ""))

            if not matiere:
                continue

            if matiere not in matieres:
                matieres.append(matiere)

            if matiere not in data:
                data[matiere] = {}

            if student_label not in data[matiere]:
                data[matiere][student_label] = {
                    "moyenne": "",
                    "notes": [],
                }

            data[matiere][student_label]["moyenne"] = _text(
                service.get("moyEleve", {}).get("V", "")
            )

        devoirs = payload.get("listeDevoirs", {}).get("V", [])

        for devoir in devoirs:
            matiere = _clean_matiere(
                devoir.get("service", {}).get("V", {}).get("L", "")
            )

            if not matiere:
                continue

            if matiere not in matieres:
                matieres.append(matiere)

            if matiere not in data:
                data[matiere] = {}

            if student_label not in data[matiere]:
                data[matiere][student_label] = {
                    "moyenne": "",
                    "notes": [],
                }

            note_txt = _format_note_for_table(devoir)

            if note_txt:
                data[matiere][student_label]["notes"].append(note_txt)

    fieldnames = ["date_export", "matiere"] + students
    rows = []

    row = {"date_export": date_export, "matiere": "MOYENNE GENERALE"}

    for student_label in students:
        moyenne = moyennes_generales.get(student_label, "")
        row[student_label] = f"{moyenne}/20" if moyenne else ""

    rows.append(row)

    for matiere in matieres:
        row = {"date_export": date_export, "matiere": matiere}

        for student_label in students:
            info = data.get(matiere, {}).get(student_label, {})

            cell = ""

            moyenne = info.get("moyenne", "")
            notes = info.get("notes", [])

            if moyenne:
                cell = f"Moyenne : {moyenne}/20"

            if notes:
                if cell:
                    cell += " — "
                cell += " | ".join(notes)

            row[student_label] = cell

        rows.append(row)

    added_count, duplicate_count = _append_csv_rows(
        filename,
        fieldnames,
        rows,
        delimiter=";",
        encoding="utf-8-sig",
    )

    print(f"✅ {filename} alimenté ({added_count} lignes ajoutées, {duplicate_count} doublons ignorés)")


def export_services_csv(raw_responses_list, filename="services.csv"):
    rows = []
    date_export = _export_date()

    for student, payload in iter_dernieres_notes_payloads(raw_responses_list):
        services = payload.get("listeServices", {}).get("V", [])

        for service in services:
            rows.append({
                "date_export": date_export,
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
                "couleur": service.get("couleur", ""),
            })

    fieldnames = [
        "date_export",
        "eleve", "classe",
        "matiere", "ordre", "est_service_en_groupe",
        "moy_eleve", "bareme_moy_eleve", "moy_classe",
        "moy_min", "moy_max", "couleur",
    ]

    added_count, duplicate_count = _append_csv_rows(filename, fieldnames, rows)

    print(f"✅ {filename} alimenté ({added_count} lignes ajoutées, {duplicate_count} doublons ignorés)")


def export_resume_csv(raw_responses_list, filename="resume.csv"):
    rows = []
    date_export = _export_date()

    for student, payload in iter_dernieres_notes_payloads(raw_responses_list):
        rows.append({
            "date_export": date_export,
            "eleve": student["name"],
            "classe": student["class"],
            "moy_generale": payload.get("moyGenerale", {}).get("V", ""),
            "moy_generale_classe": payload.get("moyGeneraleClasse", {}).get("V", ""),
            "bareme_moy_generale": payload.get("baremeMoyGenerale", {}).get("V", ""),
            "bareme_moy_generale_defaut": payload.get("baremeMoyGeneraleParDefaut", {}).get("V", ""),
            "avec_detail_devoir": payload.get("avecDetailDevoir", False),
            "avec_detail_service": payload.get("avecDetailService", False),
        })

    fieldnames = [
        "date_export",
        "eleve", "classe",
        "moy_generale", "moy_generale_classe",
        "bareme_moy_generale", "bareme_moy_generale_defaut",
        "avec_detail_devoir", "avec_detail_service",
    ]

    added_count, duplicate_count = _append_csv_rows(filename, fieldnames, rows)

    print(f"✅ {filename} alimenté ({added_count} lignes ajoutées, {duplicate_count} doublons ignorés)")

def _text(value):
    if value is None:
        return ""
    return str(value).strip()


def _clean_note(value):
    return _text(value).lstrip("|").strip()


def _clean_matiere(label):
    label = _text(label)

    if ">" in label:
        label = label.split(">")[-1].strip()

    return label


def _to_float_fr(value):
    """
    Convertit '9,38' ou '9.38' en float Python.
    Retourne None si impossible.
    """
    value = _clean_note(value)

    if not value:
        return None

    value = value.replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return None


def _format_float_fr(value, decimals=2):
    if value is None:
        return ""

    txt = f"{value:.{decimals}f}"
    txt = txt.rstrip("0").rstrip(".")
    return txt.replace(".", ",")


def _get_devoir_sujet(devoir):
    candidates = [
        devoir.get("libelleSujet", ""),
        devoir.get("commentaire", ""),
        devoir.get("commentaireSurNote", ""),
        devoir.get("libelleCorrige", ""),
    ]

    for value in candidates:
        txt = _text(value)
        if txt:
            return txt

    return ""


def _get_note_sur_20(note, bareme):
    note_float = _to_float_fr(note)
    bareme_float = _to_float_fr(bareme)

    if note_float is None or bareme_float in (None, 0):
        return ""

    return _format_float_fr((note_float / bareme_float) * 20)


def export_notes_brutes_csv(raw_responses_list, filename="notes_brutes.csv"):
    """
    Export exploitable :
    - 1 ligne = 1 note
    - 1 cellule = 1 donnée
    - trié par élève puis matière puis date
    - moyenne générale répétée sur chaque ligne
    - moyenne matière répétée sur chaque ligne
    """

    rows = []
    date_export = _export_date()

    for student, payload in iter_dernieres_notes_payloads(raw_responses_list):
        eleve = student["name"]
        classe = student["class"]

        moyenne_generale = _text(payload.get("moyGenerale", {}).get("V", ""))
        bareme_moyenne_generale = _text(payload.get("baremeMoyGenerale", {}).get("V", "20"))

        services = payload.get("listeServices", {}).get("V", [])
        devoirs = payload.get("listeDevoirs", {}).get("V", [])

        moyennes_par_matiere = {}

        for service in services:
            matiere = _clean_matiere(service.get("L", ""))

            if not matiere:
                continue

            moyennes_par_matiere[matiere] = {
                "moyenne_matiere": _text(service.get("moyEleve", {}).get("V", "")),
                "bareme_moyenne_matiere": _text(service.get("baremeMoyEleve", {}).get("V", "20")),
                "moyenne_classe": _text(service.get("moyClasse", {}).get("V", "")),
                "moyenne_min": _text(service.get("moyMin", {}).get("V", "")),
                "moyenne_max": _text(service.get("moyMax", {}).get("V", "")),
            }

        for devoir in devoirs:
            matiere = _clean_matiere(
                devoir.get("service", {}).get("V", {}).get("L", "")
            )

            if not matiere:
                continue

            infos_matiere = moyennes_par_matiere.get(matiere, {})

            note = _clean_note(devoir.get("note", {}).get("V", ""))
            bareme = _clean_note(devoir.get("bareme", {}).get("V", ""))

            rows.append({
                "date_export": date_export,
                "eleve": eleve,
                "classe": classe,

                "moyenne_generale": moyenne_generale,
                "bareme_moyenne_generale": bareme_moyenne_generale,

                "matiere": matiere,
                "moyenne_matiere": infos_matiere.get("moyenne_matiere", ""),
                "bareme_moyenne_matiere": infos_matiere.get("bareme_moyenne_matiere", ""),
                "moyenne_classe": infos_matiere.get("moyenne_classe", ""),
                "moyenne_min": infos_matiere.get("moyenne_min", ""),
                "moyenne_max": infos_matiere.get("moyenne_max", ""),

                "sujet": _get_devoir_sujet(devoir),
                "note": note,
                "bareme": bareme,
                "note_sur_20": _get_note_sur_20(note, bareme),
                "coefficient": _text(devoir.get("coefficient", "")),
                "date": _text(devoir.get("date", {}).get("V", "")),

                "periode": devoir.get("periode", {}).get("V", {}).get("L", ""),
                "note_min": _clean_note(devoir.get("noteMin", {}).get("V", "")),
                "note_max": _clean_note(devoir.get("noteMax", {}).get("V", "")),
                "commentaire": _text(devoir.get("commentaire", "")),
                "commentaire_sur_note": _text(devoir.get("commentaireSurNote", "")),
                "bonus": devoir.get("estBonus", False),
                "facultatif": devoir.get("estFacultatif", False),
                "en_groupe": devoir.get("estEnGroupe", False),
            })

    rows.sort(key=lambda r: (
        r["eleve"],
        r["classe"],
        r["matiere"],
        r["date"],
        r["sujet"],
    ))

    fieldnames = [
        "date_export",
        "eleve",
        "classe",

        "moyenne_generale",
        "bareme_moyenne_generale",

        "matiere",
        "moyenne_matiere",
        "bareme_moyenne_matiere",
        "moyenne_classe",
        "moyenne_min",
        "moyenne_max",

        "sujet",
        "note",
        "bareme",
        "note_sur_20",
        "coefficient",
        "date",

        "periode",
        "note_min",
        "note_max",
        "commentaire",
        "commentaire_sur_note",
        "bonus",
        "facultatif",
        "en_groupe",
    ]

    added_count, duplicate_count = _append_csv_rows(
        filename,
        fieldnames,
        rows,
        delimiter=";",
        encoding="utf-8-sig",
        dedupe_fieldnames=[
            "eleve",
            "classe",
            "matiere",
            "date",
            "note",
            "bareme",
            "sujet",
        ],
    )

    print(f"✅ {filename} alimenté ({added_count} notes ajoutées, {duplicate_count} doublons ignorés)")


def _safe_filename(value):
    value = (value or "").strip()

    # Remplace les caractères interdits sous Windows : \ / : * ? " < > |
    value = re.sub(r'[\\/:*?"<>|]', "_", value)

    # Remplace les espaces multiples
    value = re.sub(r"\s+", "_", value)

    return value


def export_notes_brutes_par_eleve_csv(raw_responses_list, output_dir="exports_eleves"):
    """
    Génère 1 fichier CSV par élève.
    Chaque fichier garde le même format que notes_brutes.csv :
    - 1 ligne = 1 note
    - 1 cellule = 1 donnée
    - trié par matière/date/sujet
    """

    output_path = pathlib.Path(output_dir)
    output_path.mkdir(exist_ok=True)

    students = {}

    # Regroupe les réponses par élève
    for item in raw_responses_list:
        student = normalize_student(item.get("student"))
        key = student_key(student)

        if not student["name"]:
            continue

        if key not in students:
            students[key] = {
                "student": student,
                "responses": [],
            }

        students[key]["responses"].append(item)

    # Exporte 1 fichier par élève
    for data in students.values():
        student = data["student"]
        responses = data["responses"]

        filename = _safe_filename(
            f"notes_brutes_{student['name']}_{student['class']}.csv"
        )

        filepath = output_path / filename

        export_notes_brutes_csv(
            responses,
            filename=str(filepath)
        )

    print(f"✅ exports par élève générés dans le dossier : {output_dir}")
