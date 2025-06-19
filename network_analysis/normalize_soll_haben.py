import pandas as pd

def normalize_soll_haben(df: pd.DataFrame,
                         soll: str = "soll",
                         haben: str = "haben") -> pd.DataFrame:
    """
    Bereinigt negative Beträge in den Soll- und Haben-Spalten nach buchhalterischer Logik.
    Wenn Soll negativ ist, wird der Betrag dem Haben zugeschlagen und Soll auf 0 gesetzt.
    Wenn Haben negativ ist, wird der Betrag dem Soll zugeschlagen und Haben auf 0 gesetzt.
    Falls beide negativ sind, wird der Betrag mit dem kleineren Betrag vollständig aufgerechnet.
    """
    df = df.copy()

    mask_neg_soll = df[soll] < 0
    df.loc[mask_neg_soll, haben] += -df.loc[mask_neg_soll, soll]
    df.loc[mask_neg_soll, soll] = 0

    mask_neg_haben = df[haben] < 0
    df.loc[mask_neg_haben, soll] += -df.loc[mask_neg_haben, haben]
    df.loc[mask_neg_haben, haben] = 0

    return df