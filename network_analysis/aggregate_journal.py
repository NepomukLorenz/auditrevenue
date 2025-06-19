import pandas as pd

from network_analysis.check_journal import check_if_sum_soll_and_sum_haben_are_equal, check_if_only_mirror_pairs

def _get_journal_grouped_by_kto_and_gkto(df, kto_nr, kto_name, gkto_nr, gkto_name, soll, haben, saldo)-> pd.DataFrame:
    """Gruppiert das Journal nach Konto und Gegenkonto und summiert die Beträge."""
    df = (
        df
        .groupby([kto_nr, gkto_nr], as_index=False)
        .agg({
            kto_name: "first",
            gkto_name: "first", 
            soll: "sum",
            haben: "sum",
            saldo: "sum"
        }))
    df[soll]  = df[soll].round(2)
    df[haben] = df[haben].round(2)
    df[saldo] = df[saldo].round(2)

    df.to_excel("gegenkonten_aggregiert.xlsx", index=False, engine="openpyxl")
    return df

def get_nodes_and_edges_by_aggregating_journal(
    df: pd.DataFrame,
    kto_nr: str = "KONTO_NR",
    kto_name: str = "KONTO_BEZ",
    gkto_name: str = "GKTO_BEZ",
    gkto_nr: str = "GKTO_NR",
    soll: str = "BETRAG_SOLL",
    haben: str = "BETRAG_HABEN",
    saldo: str = "BETRAG_SALDO"
    ) -> pd.DataFrame:
    """Benötigt ein normales Journal (mit 100% Gegenkontenquote) und ermittelt die gerichteten Kanten für die Gegenkontoanalyse."""
    agg = _get_journal_grouped_by_kto_and_gkto(df, kto_nr, kto_name, gkto_nr, gkto_name, soll, haben, saldo)
    check_if_only_mirror_pairs(agg, kto_nr, gkto_nr, soll, haben, saldo)
    check_if_sum_soll_and_sum_haben_are_equal(agg, soll, haben)
    return agg