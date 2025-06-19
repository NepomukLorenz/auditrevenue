import pandas as pd
import numpy as np
from datetime import datetime


def test_saldo_je_journalnummer(
    df: pd.DataFrame,
    journal_nr: str,          # Spaltenname für Journalnummern
    saldo: str,        # Spaltenname für Beträge
    tol: float = 1         # Toleranz für Rundungsdifferenzen
) -> None:
    """
    Kontrolliert, ob jeder Buchungssatz (pro JOURNAL_NR) wieder Summe Null ergibt.
    Schreibt alle fehlerhaften Journale in eine Excel-Datei.
    """
    # Summen je Journal ermitteln
    saldo_check = df.groupby(journal_nr, as_index=False)[saldo].sum()

    # Journale mit Restsaldo > Toleranz
    bad = saldo_check[saldo_check[saldo].abs() > tol]

    if not bad.empty:
        print("Fehler: Folgende JOURNAL_NR haben nach Aufbereitung keinen Nullsaldo:")
        print(bad)
        bad_journale = bad[journal_nr]
        output = df[df[journal_nr].isin(bad_journale)]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Journalnummern_nicht_null_{timestamp}.xlsx"
        output.to_excel(filename, index=False)

        raise RuntimeError("Saldenprüfung fehlgeschlagen, bitte Journalaufbereitung prüfen.")
    else:
        print("Saldenprüfung bestanden: alle Buchungssätze summieren auf Null.")


def test_ob_jede_buchung_umgedreht_doppelt(df: pd.DataFrame,
                                                     kto_nr,
                                                     gkto_nr,
                                                     saldo,
                                                     journal_nr) -> None:
    """Testet je JOURNAL_NR, ob jede Buchung eine spiegelbildliche Gegenbuchung hat.
    Fehlerhafte Buchungen werden in eine Excel-Datei exportiert.
    """
    problems = []
    for jid, grp in df.groupby(journal_nr):
        unmatched = grp.copy()
        unmatched["matched"] = False

        for idx, row in grp.iterrows():
            if unmatched.loc[idx, "matched"]:
                continue

            # Suchmaske für gespiegelte Buchung
            mask = (
                (unmatched[kto_nr] == row[gkto_nr]) &
                (unmatched[gkto_nr] == row[kto_nr]) &
                (unmatched[saldo].round(0) == round(-row[saldo], 0)) &
                (~unmatched["matched"])
            )

            match_idx = unmatched[mask].index
            if not match_idx.empty:
                unmatched.loc[idx, "matched"] = True
                unmatched.loc[match_idx[0], "matched"] = True
            else:
                problems.append({
                    "JOURNAL_NR": jid,
                    "KONTO_NR": row[kto_nr],
                    "GKTO_NR": row[gkto_nr],
                    "BETRAG": row[saldo]
                })
    if problems:
        df_problems = pd.DataFrame(problems)
        file_path = "fehlerhafte_buchungen.xlsx"
        df_problems.to_excel(file_path, index=False)
        print(f"Fehlerhafte Buchungen wurden nach '{file_path}' exportiert.")
        print(df_problems)
        # raise RuntimeError("Nicht alle Buchungen sind doppelt vorhanden.")
    else:
        print("Spiegelbuchungstest bestanden: Alle Buchungen sind symmetrisch doppelt vorhanden.")
 

def check_if_sum_soll_and_sum_haben_are_equal(df: pd.DataFrame, soll_col:str, haben_col:str) -> None:
    """Überprüft, ob die Summen der Soll- und Habenspalten übereinstimmen."""
    sum_soll = df[soll_col].sum()
    sum_haben = df[haben_col].sum()
    if not np.isclose(sum_soll, sum_haben, atol=0.50):
        raise ValueError(f"Die Summen von {soll_col} und {haben_col} stimmen nicht überein: "
                         f"{sum_soll} != {sum_haben}")
    else:
        print("Aggregierte Soll- und Habensummen stimmen überein")


def check_if_only_mirror_pairs(
        agg: pd.DataFrame,
        kto_nr,
        gkto_nr,
        soll,
        haben,
        saldo,
        ) -> None:
    """Überprüft, ob das aggregierte Journal ausschließlich aus gespiegelten (also entgegengesetzt "doppelt") Kontenkombinationen besteht,
    was die voraussetzung für eine akurate Gegenkontenanalyse ist"""
    mirrors = pd.merge(
        agg, agg,
        left_on=[kto_nr, gkto_nr],
        right_on=[gkto_nr, kto_nr],
        suffixes=("_fwd","_rev")
    )
    bad = mirrors.loc[
        (~np.isclose(mirrors[f"{saldo}_fwd"], -mirrors[f"{saldo}_rev"], atol=0.1)) |
        (~np.isclose(mirrors[f"{soll}_fwd"],  mirrors[f"{haben}_rev"], atol=0.1)) |
        (~np.isclose(mirrors[f"{haben}_fwd"], mirrors[f"{soll}_rev"], atol=0.1))
    ]
    if not bad.empty:
        print("Salden-Postulat verletzt für diese Spiegel-Paare:")
        print(bad[[f"{kto_nr}_fwd",f"{gkto_nr}_fwd"]].drop_duplicates())
        #raise ValueError("Salden-Postulat verletzt für diese Spiegel-Paare. Bitte Journalaufbereitung prüfen.")
    else:
        print("Salden-Postulat erfüllt für alle Spiegel-Paare")              