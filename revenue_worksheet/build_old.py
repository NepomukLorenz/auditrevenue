import pandas as pd
from typing import Union
from pathlib import Path
from revenue_worksheet.umsatzanalyse_with_template import create_arbeitspapier_from_template_with_sections
from typing import Optional
from monetary_unit_sampling.monetary_unit_sampling import mus_sampling_with_given_sample_size


def build_working_paper(
        df1: pd.DataFrame,
        df2: pd.DataFrame,
        col_konto: str,
        col_saldo: str,
        col_datum: str,
        template_path: Union[str, Path],
        mapping_path: Union[str, Path],
        output_path: Union[str, Path] = "arbeitspapier.xlsx",
        mus_sample_size:int= 10,
    ) -> None:

    mapping = _get_mapping(mapping_path)
    lst_sparten = _get_list_of_sections(mapping)

    # 1) Mapping + Filter auf Umsatz-/Materialkennzeichen für beide DataFrames
    df1_mapped = _initially_map_and_filter_df(df1, col_konto, mapping)
    df2_mapped = _initially_map_and_filter_df(df2, col_konto, mapping)


    df_list_of_touples = _get_all_dfs(
        lst_sparten,
        df1_mapped,
        df2_mapped,
        col_kategorie="kategorie",
        col_sparte="sparte",
        col_saldo=col_saldo,
        col_datum=col_datum,
    )
    
    df2_mapped_only_ue = _filter_for_mus_sample(df2_mapped)
    mus_sample = mus_sampling_with_given_sample_size(df2_mapped_only_ue, col_saldo, mus_sample_size, "filter")
    

    create_arbeitspapier_from_template_with_sections(
        df_list_of_touples,
        template_path,
        output_path,
        mus_sample
    )


def _get_mapping(path)->pd.DataFrame:
    """returns df with cols: kto_nr, kto_name, kto_categorie (ue, ma) and kto_section (sparte, o.ae.)"""
    df = pd.read_excel(path, dtype="string")
    return df


def _get_list_of_sections(mapping:pd.DataFrame)-> list:
    return mapping.iloc[:, 3].unique().tolist()


def _initially_map_and_filter_df(df:pd.DataFrame, col_kto:str, mapping:pd.DataFrame, umsatzkennzeichen:str="u", materialkennzeichen:str="m"):
    """In der Mappingtabelle steht kto, kto_name, kennzeichen und sparte (Namen verschieden nur mit Spaltenindex arbeiten).
    der df (Buchungsjournal) soll um die Kategorie und sparte, die man aus der mapping datei lesen kann, erweitert werden. joinen kann man df[col_kto] und mapping[0]

    Am ende soll der df wieder ausgegeben werden, nur dass jetzt rechts auch noch die kategorie und sparte je konto zu finden ist. 
    
    zuletzt wird der df auf nur kennzeichen == Umsatzkennzeichen oder Materaialkennzeichen gefiltert."""

    # 1) Bestimme mittels Spaltenindex die vier Mapping-Spaltennamen
    kto_map_col      = mapping.columns[0]
    name_map_col     = mapping.columns[1]
    kennz_map_col    = mapping.columns[2]
    sparte_map_col   = mapping.columns[3]

    # 2) Left-Join: Journal mit Mapping verbinden
    df_merged = df.merge(
        mapping,
        how="left",
        left_on=col_kto,
        right_on=kto_map_col,
        validate="many_to_one"
    )

    # 3) Filter auf Umsatz- oder Materialkennzeichen
    mask = df_merged[kennz_map_col].isin([umsatzkennzeichen, materialkennzeichen])
    df_filt = df_merged.loc[mask].copy()

    # 4) Erzeuge die neuen, aussagekräftigen Spalten
    df_filt = df_filt.assign(
        kategorie   = df_filt[kennz_map_col], #die Spalten heißen jetzt "kategorie"
        sparte      = df_filt[sparte_map_col] # und "sparte".
    )

    # 5) Alte Mapping-Spalten entfernen
    df_result = df_filt.drop(
        columns=[kto_map_col, name_map_col, kennz_map_col, sparte_map_col]
    )
    return df_result

def _filter_for_mus_sample(df:pd.DataFrame, filter_col:str = "kategorie", umsatzkennzeichen:str="u"):
    """Filtert das journal auf nur Umsatzerlöse anhnad des Kennzeichens in der Spalte "kategorie" """
    mask = df[filter_col].isin([umsatzkennzeichen])
    df_filt = df.loc[mask].copy()
    return df_filt

def _get_all_dfs(
        lst_sparten:list, 
        df1:pd.DataFrame, 
        df2:pd.DataFrame,
        col_kategorie: str,
        col_sparte: str,
        col_saldo: str,
        col_datum: str, 
        umsatzkennzeichen:str="u",
        materialkennzeichen:str="m")-> list:
    """Generates a list of toupels each containig df1 and df2 calculatet by section"""
    list = []

    year1 =_calculate_one_df(
        df = df1,
        col_sparte = col_sparte,
        col_kategorie = col_kategorie,
        col_saldo = col_saldo,
        col_datum = col_datum,
        sparte_value=None
        )
    year2 =_calculate_one_df(
        df = df2,
        col_sparte = col_sparte,
        col_kategorie = col_kategorie,
        col_saldo = col_saldo,
        col_datum = col_datum,
        sparte_value = None
        )
    list.append((year2, year1))

    if len(lst_sparten) > 0: 
        for section in lst_sparten:
            result1 = _calculate_one_df(
                df = df1,
                col_sparte = col_sparte,
                col_kategorie = col_kategorie,
                col_saldo = col_saldo,
                col_datum = col_datum,
                sparte_value = str(section)
                ) 
            result2 = _calculate_one_df(
                df = df2,
                col_sparte = col_sparte,
                col_kategorie = col_kategorie,
                col_saldo = col_saldo,
                col_datum = col_datum,
                sparte_value = str(section)
                )
            toupel = (result2, result1)
            list.append(toupel)

    return list


def _calculate_one_df(
        df: pd.DataFrame,
        col_sparte: str,
        col_kategorie: str,
        col_saldo: str,
        col_datum: str,
        sparte_value: Optional[str] = None,
        umsatzkennzeichen: str = "u",
        materialkennzeichen: str = "m",
    ) -> pd.DataFrame:
    """
    12-Zeilen-Übersicht der Monatssummen für Umsatzerlöse (u) und Materialaufwand (m).
    """

    # 0) Kopie um SettingWithCopyWarnings zu vermeiden
    df = df.copy()

    # --- fix für FutureWarning: StringDtype mit datetime64 tauschen ---
    tmp = pd.to_datetime(df[col_datum], errors="coerce")
    df = df.drop(columns=[col_datum])
    df[col_datum] = tmp

    # 1) Monat extrahieren
    df.loc[:, "Monat"] = df[col_datum].dt.month

    # 3) Nach Sparte filtern (wenn gewünscht)
    if sparte_value is not None:
        df = df.loc[df[col_sparte] == sparte_value]

    # 4) Umsatzerlöse je Monat
    series_u = (
        df.loc[df[col_kategorie] == umsatzkennzeichen]
          .groupby("Monat")[col_saldo]
          .sum()
          .reindex(range(1, 13), fill_value=0)
          .mul(-1)
    )

    # 5) Materialaufwand je Monat
    series_m = (
        df.loc[df[col_kategorie] == materialkennzeichen]
          .groupby("Monat")[col_saldo]
          .sum()
          .reindex(range(1, 13), fill_value=0)
    )

    # 6) Ergebnis-DataFrame
    result = pd.DataFrame({
        "Umsatz":     series_u,
        "Materialaufwand":  series_m
    })
    result.index.name = None

    return result