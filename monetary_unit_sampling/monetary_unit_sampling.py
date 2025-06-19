import numpy as np
import pandas as pd
from typing import Union, Optional

def mus_sampling_with_given_sample_size(
    data: Union[pd.Series, pd.DataFrame],
    amount_col: Optional[str] = None,
    sample_size: int = 1,
    mode: str = "filter",
    seed: Optional[int] = None
) -> Union[pd.Series, pd.DataFrame]:
    """
    Systematisches Monetary Unit Sampling (PPS) mit korrektem Handling negativer Werte
    und beliebigem Index.

    Gibt bei leerem Input einfach den leeren Input zurück.

    Parameters
    ----------
    data : pd.Series or pd.DataFrame
        Eingabedaten. Bei DataFrame muss amount_col gesetzt sein.
    amount_col : str, optional
        Spaltenname der Beträge (bei DataFrame).
    sample_size : int
        Anzahl der zu ziehenden Einheiten.
    mode : {"filter", "mark"}
        - "filter": gibt nur die gezogenen Zeilen zurück
        - "mark":   gibt alle Zeilen zurück und markiert die gezogenen mit "x" in Spalte "MUS"
    seed : int, optional
        Zufallsseed für Reproduzierbarkeit.

    Returns
    -------
    pd.Series or pd.DataFrame
    """
    # --- Input-Validation ---------------------------------------------------
    if isinstance(data, pd.DataFrame):
        if amount_col is None:
            raise ValueError("Bei DataFrame muss 'amount_col' gesetzt sein.")
        if data.empty:
            return data  # leerer DataFrame
        series = data[amount_col]
    elif isinstance(data, pd.Series):
        if amount_col is not None:
            raise ValueError("Bei Series darf 'amount_col' nicht gesetzt sein.")
        if data.empty:
            return data  # leere Series
        series = data
    else:
        raise TypeError("`data` muss pd.Series oder pd.DataFrame sein.")

    if not np.issubdtype(series.dtype, np.number):
        raise TypeError("Die Betragsspalte muss numerisch sein.")
    if sample_size < 1:
        raise ValueError("`sample_size` muss mindestens 1 sein.")
    if mode not in {"filter", "mark"}:
        raise ValueError("`mode` muss 'filter' oder 'mark' sein.")

    # --- Reset Index und Betragsserie vorbereiten --------------------------
    # Klaren Integer-Index 0..n-1, sonst u.U. ValueError
    if isinstance(data, pd.DataFrame):
        df = data.reset_index(drop=True).copy()
    else:  # pd.Series
        df = data.reset_index(drop=True).to_frame(name=series.name)

    # Ermittlung der Intervalle
    amt = df[series.name].abs()
    total = amt.sum()
    interval = total / sample_size

    # Zufallsstart
    if seed is not None:
        np.random.seed(seed)
    start = np.random.uniform(0, interval)

    # Schwellenwerte
    thresholds = start + interval * np.arange(sample_size)

    # Sortieren nach absoluten Beträgen und kumulieren
    sorted_pos = np.argsort(amt.values)
    cum = amt.values[sorted_pos].cumsum()

    # Positionen ermitteln
    sel_positions = [ sorted_pos[np.searchsorted(cum, t)] for t in thresholds ]

    # --- Ausgabe ------------------------------------------------------------
    if mode == "filter":
        # nur die ausgewählten Zeilen
        result = df.iloc[sel_positions]
        # wenn Series ursprünglich, gib es als Series zurück
        return result[series.name] if isinstance(data, pd.Series) else result

    # mode == "mark"
    df["MUS"] = ""
    df.iloc[sel_positions, df.columns.get_loc("MUS")] = "x"
    # Series: zurück als DataFrame mit MUS-Spalte
    return df if isinstance(data, pd.DataFrame) else df
