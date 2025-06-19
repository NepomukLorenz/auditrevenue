import pandas as pd

from network_analysis.prepare_journal import prepare_journal
from network_analysis.aggregate_journal import get_nodes_and_edges_by_aggregating_journal
from network_analysis.generate_kto_rahmen import generate_kto_rahmen
from network_analysis.categorize_kto import categorize_kto
from network_analysis.generate_network import build_network

def build_network_analysis(
        destination_path:str, 
        dataframe: pd.DataFrame,
        kto_nr,
        kto_name,
        gkto_nr,
        gkto_name,
        soll,
        haben,
        saldo,
        journal_nr,
        materiality:int = 0) -> None:

    df_clean = prepare_journal(
        dataframe,
        kto_nr,
        kto_name,
        gkto_nr,
        gkto_name,
        soll,
        haben,
        saldo,
        journal_nr)
    
    agg = get_nodes_and_edges_by_aggregating_journal(
        df_clean,
        kto_nr,
        kto_name,
        gkto_nr,
        gkto_name,
        soll,
        haben,
        saldo)

    kto_rahmen = generate_kto_rahmen(agg, kto_nr, kto_name)
    agg_categorized = categorize_kto(
        kto_rahmen, 
        kto_nr,
        kto_name,
      
        agg,
        kto_nr,
        kto_name,
        gkto_nr,
        gkto_name,
        soll,
        haben,
        saldo)

    kto_kategorie = "kto_kategorie"  #Wird in categorize_kto so gesetzt

    build_network(
        agg_categorized,
        kto_nr,
        kto_name,
        gkto_nr,
        gkto_name,
        soll,
        haben,
        saldo,
        kto_kategorie,
        destination_path,
        materiality
        )