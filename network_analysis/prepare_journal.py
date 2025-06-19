import pandas as pd
from network_analysis.check_journal import test_ob_jede_buchung_umgedreht_doppelt, test_saldo_je_journalnummer
from network_analysis.normalize_soll_haben import normalize_soll_haben
from network_analysis.replicate_div_rows import replicate_div_rows
from network_analysis.replace_debitoren_kreditoren import replace_debitoren_kreditoren

def prepare_journal(
        df: pd.DataFrame,
        kto_nr,
        kto_name,
        gkto_nr,
        gkto_name,
        soll,
        haben,
        saldo,
        journal_nr
        )-> pd.DataFrame:   
    """Journalaubereitung zur Gegenkontoanalyse"""
    
    df_prep = replicate_div_rows(df, kto_nr, kto_name, gkto_nr, gkto_name, soll, haben, saldo, journal_nr)

    df_prep = normalize_soll_haben(df_prep, soll=soll, haben=haben)
    
    ### Bei Bedarf
    # df_prep = replace_debitoren_kreditoren(
    #     first_letter_debitor="1",
    #     first_letter_kreditor="2",
    #     df=df_prep,
    #     kto_nr=kto_nr,
    #     kto_name=kto_name,
    #     gkto_nr=gkto_nr,
    #     gkto_name=gkto_name
    #     )

    test_saldo_je_journalnummer(df_prep, saldo=saldo, journal_nr=journal_nr)
    test_ob_jede_buchung_umgedreht_doppelt(df_prep, kto_nr, gkto_nr, saldo, journal_nr)
    df_prep.to_excel("ertweitertes_journal.xlsx")
    
    return df_prep