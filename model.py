# Questo file contiene la logica per generare la formazione.

import random

# Esempio di rosa (da sostituire con la tua)
ROSTER = {
"Por": ["Milinkovic-Savic", "Consigli"],
"Dif": [
("Bremer", 7.0), ("Danilo", 6.3), ("Theo Hernandez", 6.8),
("Bastoni", 6.6), ("Darmian", 6.5)
],
"Cen": [
("Calhanoglu", 7.2), ("Barella", 6.8), ("Zielinski", 6.4),
("Loftus-Cheek", 6.6)
],
"Att": [
("Lautaro", 7.8), ("Osimhen", 7.6), ("Leao", 7.0), ("Thuram", 7.4)
],
}


def get_best_lineup():
    portiere = ROSTER["Por"][0]

    dif = sorted(ROSTER["Dif"], key=lambda x: x[1], reverse=True)[:3]
    cen = sorted(ROSTER["Cen"], key=lambda x: x[1], reverse=True)[:3]
    att = sorted(ROSTER["Att"], key=lambda x: x[1], reverse=True)[:3]

    formazione = "\n".join([
        f"POR: {portiere}",
        ", ".join([f"DIF: {d[0]} ({d[1]})" for d in dif]),
        ", ".join([f"CEN: {c[0]} ({c[1]})" for c in cen]),
        ", ".join([f"ATT: {a[0]} ({a[1]})" for a in att]),
    ])


    return formazione