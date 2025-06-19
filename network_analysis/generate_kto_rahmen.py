import pandas as pd

def generate_kto_rahmen(df:pd.DataFrame, kto_nr:str, kto_name:str) -> pd.DataFrame:
    """Extracts unique accounts from given df, returns df with cols from params {kto_nr} and {kto_name}"""
    if not {kto_nr, kto_name}.issubset(df.columns):
        raise ValueError(f"Das DataFrame muss die Spalten {kto_nr} und {kto_name} enthalten.")
    return(
        df.groupby(kto_nr, as_index=False)
        .agg({kto_name: "first"})
    )