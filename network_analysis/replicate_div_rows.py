import pandas as pd

def replicate_div_rows(
        df: pd.DataFrame,
        kto_nr,
        kto_name,
        gkto_nr,
        gkto_name,
        soll,
        haben,
        saldo,
        journal_nr
        ) -> pd.DataFrame:
    df = _mark_rows_with_div_or_no_gkto(df, gkto_nr=gkto_nr)
    _test_number_of_div_rows_per_journalnumber(df, journal_nr)
    df_copies = _find_references_and_replicate_div_rows(df, 
                                                        kto_nr=kto_nr, 
                                                        kto_name=kto_name, 
                                                        gkto_nr=gkto_nr, 
                                                        gkto_name=gkto_name, 
                                                        soll=soll, 
                                                        haben=haben, 
                                                        saldo=saldo, 
                                                        journal_nr=journal_nr)
    df_prep = _create_new_journal_inclouding_div_replicas_exclouding_original_div_rows(df, df_copies, journal_nr=journal_nr)
    return df_prep

def _mark_rows_with_div_or_no_gkto(df: pd.DataFrame, gkto_nr: str) -> pd.DataFrame:
    """Markiert Zeilen mit Div-Konto oder ohne Gegenkonto für die Gegenkontoanalyse."""
    is_div_konto = df[gkto_nr].str.strip().str.fullmatch(r"(?i)div\.?")
    is_missing_gkto = df[gkto_nr].isna() | (df[gkto_nr].str.strip() == "")
    df["is_div"] = is_div_konto | is_missing_gkto
    return df

def _test_number_of_div_rows_per_journalnumber(df: pd.DataFrame, journal_nr) -> None:
    """Testet, ob es für jede JOURNAL_NR maximal eine Div-Zeile gibt."""
    div_counts = df.groupby(journal_nr)["is_div"].sum()
    if (div_counts > 1).any():
        raise ValueError("Nicht für jede JOURNAL_NR gibt es genau eine Div-Zeile. "
                        "Bitte Journalaufbereitung prüfen.")
        
def _find_references_and_replicate_div_rows(df: pd.DataFrame, kto_nr, kto_name, gkto_nr, gkto_name, soll, haben, journal_nr, saldo=None, ) -> pd.DataFrame:
    """Findet für jede Journalnummer mit Div-Flag, die korrespondierdenen Gegenbuchungen (Referenzen) der Div-Buchung und kopiert letztere mit den Referenzwerten"""
    copies = []
    for jid, grp in df.groupby(journal_nr, sort=False):
        # finde die eine Div-Zeile
        div = grp.loc[grp["is_div"]]
        if len(div)!=1:
            continue  # überspringen, falls 0 oder >1 Div-Zeilen
        div = div.iloc[0]  # Series mit den Div-Feldern

        # finde alle Zeilen, deren GKTO_NR auf genau dieses Div-Konto zeigt
        refs = grp[(~grp["is_div"]) & (grp[gkto_nr] == div[kto_nr])]
        if refs.empty:
            continue

        # für jede Referenz eine Kopie der Div-Zeile, befüllt mit ref-Daten
        for _, r in refs.iterrows():
            copies.append({
                **div.drop("is_div").to_dict(),  # alle Original-Spalten der Div-Zeile
                gkto_nr:    r[kto_nr],     # Gegenkonto = das referenzierende Konto
                gkto_name:   r[kto_name],    # optional: leer oder aus r übernehmen
                soll:       r[haben],         # Betrag aus der Referenz-Zeile
                haben:      r[soll],
                saldo:  -r[saldo],
                "is_div":     False              
            })
    df_copies = pd.DataFrame(copies)
    return df_copies

def _create_new_journal_inclouding_div_replicas_exclouding_original_div_rows(df: pd.DataFrame, df_copies: pd.DataFrame, journal_nr) -> pd.DataFrame:
    """Erstellt ein neues Journal, das die Original-Div-Zeilen und deren Repliken enthält.
        df_prep enthält am Ende:
        • alle ursprünglichen Zeilen (inkl. Div-Zeilen)
        • plus für jede Referenz-Zeile eine *aufgesplittete* Div-Kopie"""

    df_prep = pd.concat([df, df_copies], ignore_index=True, sort=False)

    # (optional) sortieren nach JOURNAL_NR, damit alles zusammenbleibt
    df_prep = df_prep.sort_values([journal_nr,"is_div"], ascending=[True, True])

    # Aus df_prep alle ORIGINAL-Div-Zeilen (is_div==True) rauswerfen
    df_prep = df_prep.loc[~df_prep["is_div"]].copy()

    # Optional: is_div-Spalte kannst du jetzt entfernen, wenn du sie nicht mehr brauchst
    df_prep = df_prep.drop(columns="is_div")
    
    return df_prep