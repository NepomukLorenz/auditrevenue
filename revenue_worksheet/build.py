import pandas as pd
from typing import Union
from pathlib import Path
from revenue_worksheet.umsatzanalyse_with_template import (
    create_arbeitspapier_from_template_with_sections,
)
from typing import Optional
from monetary_unit_sampling.monetary_unit_sampling import (
    mus_sampling_with_given_sample_size,
)


def build_working_paper(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    col_konto: str,
    col_saldo: str,
    col_datum: str,
    template_path: Union[str, Path],
    mapping_path: Union[str, Path],
    df3: pd.DataFrame = None,
    output_path: Union[str, Path] = "arbeitspapier.xlsx",
    mus_sample_size: int = 10,
    cut_off_sample_size: int = 10,
    materiality: int = 0,
) -> None:

    mapping = _get_mapping(mapping_path)
    lst_sparten = _get_list_of_sections(mapping)

    df1_mapped = _initially_map_and_filter_df(df1, col_konto, mapping)
    df2_mapped = _initially_map_and_filter_df(df2, col_konto, mapping)
    if df3 is not None:
        df3_mapped = _initially_map_and_filter_df(df3, col_konto, mapping)

    df_list_of_touples = _get_all_dfs(
        lst_sparten,
        df1_mapped,
        df2_mapped,
        col_kategorie="kategorie",
        col_sparte="sparte",
        col_saldo=col_saldo,
        col_datum=col_datum,
    )

    df2_mapped_only_ue = _filter_for_mus_sample(
        df=df2_mapped, 
        saldo_col=col_saldo, 
        materiality=materiality
    )
    mus_sample = mus_sampling_with_given_sample_size(
        data=df2_mapped_only_ue,
        amount_col=col_saldo,
        sample_size=mus_sample_size,
        mode="filter",
    )

    df2_mapped_only_ue_only_dec = _filter_for_mus_cut_off_sample_dec(
        df=df2_mapped_only_ue,
        date_col=col_datum,
        saldo_col=col_saldo,
        materiality=materiality,
    )
    df2_mapped_only_ue_only_dec.to_excel("df2_mapped_only_ue_only_dec.xlsx")
    cut_off_sample_df2 = mus_sampling_with_given_sample_size(
        data=df2_mapped_only_ue_only_dec,
        amount_col=col_saldo,
        sample_size=cut_off_sample_size,
        mode="filter",
    )

    if df3 is not None:
        df3_mapped_only_ue_only_jan = _filter_for_mus_cut_off_sample_jan(
            df=df3_mapped, 
            date_col=col_datum, 
            saldo_col=col_saldo, 
            materiality=materiality
        )
        cut_off_sample_df3 = mus_sampling_with_given_sample_size(
            data=df3_mapped_only_ue_only_jan,
            amount_col=col_saldo,
            sample_size=cut_off_sample_size,
            mode="filter",
        )
        cut_off_sample = pd.concat(
            [cut_off_sample_df2, cut_off_sample_df3], ignore_index=True
        )
    else:
        cut_off_sample = cut_off_sample_df2

    create_arbeitspapier_from_template_with_sections(
        df_list_of_touples,
        template_path,
        output_path,
        mus_sample,
        cut_off_sample,
    )


def _get_mapping(path) -> pd.DataFrame:
    """returns df with cols: kto_nr, kto_name, kto_categorie (ue, ma) and kto_section (sparte, o.ae.)"""
    df = pd.read_excel(path, dtype="string")
    return df


def _get_list_of_sections(mapping: pd.DataFrame) -> list:
    return mapping.iloc[:, 3].unique().tolist()


def _initially_map_and_filter_df(
    df: pd.DataFrame,
    col_kto: str,
    mapping: pd.DataFrame,
    umsatzkennzeichen: str = "u",
    materialkennzeichen: str = "m",
):
    """In der Mappingtabelle steht kto, kto_name, kennzeichen und sparte (Namen verschieden nur mit Spaltenindex arbeiten).
    der df (Buchungsjournal) soll um die Kategorie und sparte, die man aus der mapping datei lesen kann, erweitert werden. joinen kann man df[col_kto] und mapping[0]

    Am ende soll der df wieder ausgegeben werden, nur dass jetzt rechts auch noch die kategorie und sparte je konto zu finden ist.

    zuletzt wird der df auf nur kennzeichen == Umsatzkennzeichen oder Materaialkennzeichen gefiltert.
    """
    kto_map_col = mapping.columns[0]
    name_map_col = mapping.columns[1]
    kennz_map_col = mapping.columns[2]
    sparte_map_col = mapping.columns[3]

    df_merged = df.merge(
        mapping,
        how="left",
        left_on=col_kto,
        right_on=kto_map_col,
        validate="many_to_one",
    )
    mask = df_merged[kennz_map_col].isin([umsatzkennzeichen, materialkennzeichen])
    df_filt = df_merged.loc[mask].copy()

    df_filt = df_filt.assign(
        kategorie=df_filt[kennz_map_col],  # die Spalten heißen jetzt "kategorie"
        sparte=df_filt[sparte_map_col],  # und "sparte".
    )
    df_result = df_filt.drop(
        columns=[kto_map_col, name_map_col, kennz_map_col, sparte_map_col]
    )
    return df_result


def _filter_for_mus_sample(
    df: pd.DataFrame,
    saldo_col: str = "SALDO_S_H",
    filter_col: str = "kategorie",
    umsatzkennzeichen: str = "u",
    materiality: int = 0,
):
    """Filtert das Journal auf:
    - nur Umsatzerlöse anhand des Kennzeichens in der Spalte "kategorie"
    - nur Buchungen mit absolutem Betrag größer als materiality
    """
    mask_kategorie = df[filter_col].isin([umsatzkennzeichen])
    df[saldo_col] = pd.to_numeric(df[saldo_col], errors="coerce")
    mask_betrag = df[saldo_col].abs() > materiality
    df_filt = df.loc[mask_kategorie & mask_betrag].copy()
    return df_filt


def _filter_for_mus_cut_off_sample_dec(
    df: pd.DataFrame,
    saldo_col: str = "SALDO_S_H",
    date_col: str = "BELEG_DAT",
    filter_col: str = "kategorie",
    umsatzkennzeichen: str = "u",
    materiality: int = 0,
):
    """Filtert das Journal auf:
    - nur Umsatzerlöse anhand des Kennzeichens in der Spalte "kategorie"
    - nur Buchungen ab dem 15. Dezember (unabhängig vom Jahr)
    - nur Buchungen mit absolutem Betrag größer als materiality
    """
    tmp = pd.to_datetime(df[date_col], errors="coerce")
    df = df.drop(columns=[date_col])
    df[date_col] = tmp
    mask_datum = df[date_col].dt.month.eq(12) & df[date_col].dt.day.ge(15)
    mask_kategorie = df[filter_col].isin([umsatzkennzeichen])
    df[saldo_col] = pd.to_numeric(df[saldo_col], errors="coerce")
    mask_betrag = df[saldo_col].abs() > materiality
    df_filt = df.loc[mask_kategorie & mask_datum & mask_betrag].copy()
    return df_filt


def _filter_for_mus_cut_off_sample_jan(
    df: pd.DataFrame,
    saldo_col: str = "SALDO_S_H",
    date_col: str = "BELEG_DAT",
    filter_col: str = "kategorie",
    umsatzkennzeichen: str = "u",
    materiality: int = 0,
):
    """Filtert das Journal auf:
    - nur Umsatzerlöse anhand des Kennzeichens in der Spalte "kategorie"
    - nur Buchungen bis einschließlich 15. Januar (unabhängig vom Jahr)
    - nur Buchungen mit absolutem Betrag größer als materiality
    """
    tmp = pd.to_datetime(df[date_col], errors="coerce")
    df = df.drop(columns=[date_col])
    df[date_col] = tmp
    mask_datum = df[date_col].dt.month.eq(1) & df[date_col].dt.day.le(15)
    mask_kategorie = df[filter_col].isin([umsatzkennzeichen])
    df[saldo_col] = pd.to_numeric(df[saldo_col], errors="coerce")
    mask_betrag = df[saldo_col].abs() > materiality
    df_filt = df.loc[mask_kategorie & mask_datum & mask_betrag].copy()
    return df_filt


def _get_all_dfs(
    lst_sparten: list,
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    col_kategorie: str,
    col_sparte: str,
    col_saldo: str,
    col_datum: str,
    umsatzkennzeichen: str = "u",
    materialkennzeichen: str = "m",
) -> list:
    """Generates a list of toupels each containig df1 and df2 calculatet by section"""
    list = []

    year1 = _calculate_one_df(
        df=df1,
        col_sparte=col_sparte,
        col_kategorie=col_kategorie,
        col_saldo=col_saldo,
        col_datum=col_datum,
        sparte_value=None,
    )
    year2 = _calculate_one_df(
        df=df2,
        col_sparte=col_sparte,
        col_kategorie=col_kategorie,
        col_saldo=col_saldo,
        col_datum=col_datum,
        sparte_value=None,
    )
    list.append((year2, year1))

    if len(lst_sparten) > 0:
        for section in lst_sparten:
            result1 = _calculate_one_df(
                df=df1,
                col_sparte=col_sparte,
                col_kategorie=col_kategorie,
                col_saldo=col_saldo,
                col_datum=col_datum,
                sparte_value=str(section),
            )
            result2 = _calculate_one_df(
                df=df2,
                col_sparte=col_sparte,
                col_kategorie=col_kategorie,
                col_saldo=col_saldo,
                col_datum=col_datum,
                sparte_value=str(section),
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

    result = pd.DataFrame({"Umsatz": series_u, "Materialaufwand": series_m})
    result.index.name = None

    return result
