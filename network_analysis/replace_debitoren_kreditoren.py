import pandas as pd

def replace_debitoren_kreditoren(first_letter_debitor: str, 
                                  first_letter_kreditor: str, 
                                  df: pd.DataFrame,
                                  kto_nr: str = "KONTO_NR",
                                  kto_name: str = "KONTO_BEZ",
                                  gkto_nr: str = "GKTO_NR",
                                  gkto_name: str = "GKTO_BEZ"
                                  ) -> pd.DataFrame:
    df = df.copy()

    # Hilfsfunktion zur Ersetzung basierend auf erster Ziffer
    def _replace_kto(nr, name):
        if pd.isna(nr):
            return nr, name
        nr_str = str(nr)
        if nr_str.startswith(first_letter_debitor):
            return "DEBITOR", "DEBITOR"
        elif nr_str.startswith(first_letter_kreditor):
            return "KREDITOR", "KREDITOR"
        else:
            return nr, name  # Fallback: Originalwerte behalten

    # Anwendung auf Hauptkonto
    df[[kto_nr, kto_name]] = df[[kto_nr, kto_name]].apply(
        lambda row: _replace_kto(row[kto_nr], row[kto_name]),
        axis=1, result_type='expand'
    )

    # Anwendung auf Gegenkonto
    df[[gkto_nr, gkto_name]] = df[[gkto_nr, gkto_name]].apply(
        lambda row: _replace_kto(row[gkto_nr], row[gkto_name]),
        axis=1, result_type='expand'
    )

    return df