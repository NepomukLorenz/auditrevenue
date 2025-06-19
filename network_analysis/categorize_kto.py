from typing import Literal
from pydantic import BaseModel
from openai import OpenAI
import pandas as pd
from dotenv import load_dotenv
import os

__all__ = ["categorize_kto"]

load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Kategorien-Schema via Pydantic

type KategorieLiteral = Literal[
    "Aufwand",
    "Zahlungsmittel",
    "Umsatzerlöse",
    "Sonstige Erlöse",
    "Debitoren",
    "Sonstige Forderungen",
    "Kreditoren",
    "Verrechnungskonten",
    "Umsatzsteuer",
    "Sonstige Aktiva",
    "Sonstige Passiva",
    "Eröffnungskonten",
]


class KontoKategorie(BaseModel):
    kategorie: KategorieLiteral


def _extract_top_gegenkonten(
    bewegungen_df: pd.DataFrame, konto: str, kto, gkto_name, soll, n: int = 3
) -> str:
    gefiltert = bewegungen_df[bewegungen_df[kto] == konto]
    gruppiert = (
        gefiltert.groupby(gkto_name)[soll].sum().sort_values(ascending=False).head(n)
    )
    return "\n".join(f"{k}: {v:,.2f}" for k, v in gruppiert.items())


def _get_nachbarkonten(
    df_konten: pd.DataFrame,
    konto: str,
    df_konten_kto: str,
    df_konten_kto_name: str,
    n: int = 2,
) -> str:
    # Work on a copy, damit die Original-DF nicht verändert wird

    df = df_konten.copy()

    # Spalte für die numerische Sortierung anlegen

    try:
        df["src_int"] = df[df_konten_kto].astype(int)
        ziel = int(konto)
    except ValueError:
        return ""
    # nach src_int sortieren und Index resetten

    sortiert = df.sort_values("src_int").reset_index(drop=True)

    # Position des gesuchten Kontos finden

    mask = sortiert["src_int"] == ziel
    if not mask.any():
        return ""
    idx = mask.idxmax()

    # Start- und End-Index für n Nachbarn links und rechts

    start = max(idx - n, 0)
    end = min(idx + n + 1, len(sortiert))

    # Ausschnitt holen und aktuelles Konto herausfiltern

    nachbarn = sortiert.iloc[start:end]
    nachbarn = nachbarn[nachbarn[df_konten_kto] != konto]

    # Ergebnis-Zeilen zusammenbauen

    lines = [
        f"{int(row[df_konten_kto])}: {row[df_konten_kto_name]}"
        for _, row in nachbarn.iterrows()
    ]
    return "\n".join(lines)


def _call_ai_kategorie_bestimmen(
    kontonummer: str,
    kontobezeichnung: str,
    gegenkontoinfo: str = "",
    nachbarkonten: str = "",
) -> str:
    system_msg = {
        "role": "system",
        "content": (
            "Du bist ein professionelles Buchhaltungs-KI-System. "
            "Deine Aufgabe ist es, jedem Konto genau eine passende Kategorie aus einer vordefinierten Liste zuzuweisen."
        ),
    }

    user_msg = {
        "role": "user",
        "content": f"""
Ordne dem folgenden Konto eine der folgenden Kategorien zu:
[Aufwand, Zahlungsmittel, Umsatzerlöse, Sonstige Erlöse, Debitoren, Sonstige Forderungen, Kreditoren, Verrechnungskonten, Umsatzsteuer, Sonstige Aktiva, Sonstige Passiva, Eröffnungskonten]

Kontonummer: {kontonummer}
Kontobezeichnung: {kontobezeichnung}
{f"\n\nGegenkontoinformationen:\n{gegenkontoinfo}" if gegenkontoinfo else ""}
{f"\n\nÄhnliche Konten im Kontenplan:\n{nachbarkonten}" if nachbarkonten else ""}

Hinweis: 
- VAK steht für Aufwand

Du musst und darfst ausschließlich mit einer Kategorie der Liste antworten.
""",
    }

    response = client.responses.parse(
        model="gpt-4o-2024-08-06",
        input=[system_msg, user_msg],
        text_format=KontoKategorie,
    )

    return response.output_parsed.kategorie


def categorize_kto(
    df_konten: pd.DataFrame,
    df_konten_kto,
    df_konten_kto_name,
    df_bewegungen: pd.DataFrame | None = None,
    df_bewegungen_kto: str | None = None,
    df_bewegungen_kto_name: str | None = None,
    df_bewegungen_gkto: str | None = None,
    df_bewegungen_gkto_name: str | None = None,
    df_bewegungen_soll: str | None = None,
    df_bewegungen_haben: str | None = None,
    df_bewegugnen_saldo: str | None = None,
) -> pd.DataFrame:

    kategorien = []
    for _, row in df_konten.iterrows():
        konto = row[df_konten_kto]
        name = row[df_konten_kto_name]

        gegen_info = ""
        if df_bewegungen is not None:
            gegen_info = _extract_top_gegenkonten(
                df_bewegungen,
                konto,
                df_bewegungen_kto,
                df_bewegungen_gkto_name,
                df_bewegungen_soll,
            )
        nachbarkonten = _get_nachbarkonten(
            df_konten, konto, df_konten_kto, df_konten_kto_name, n=3
        )

        kategorie = _call_ai_kategorie_bestimmen(konto, name, gegen_info, nachbarkonten)
        kategorien.append(kategorie)
    df_result = df_konten.copy()
    df_result["kto_kategorie"] = kategorien

    agg_categorized = df_bewegungen.merge(
        df_result[[df_konten_kto, "kto_kategorie"]], on=df_konten_kto, how="left"
    )

    ### Ausgabe des Kategorisierten Kontenplans und aggregierten Journals zum Debugging bei Bedarf
    # df_result.to_excel("kto_kategorisiert.xlsx", index=False, engine="openpyxl")
    # agg_categorized.to_excel("kto_kategorisiert_agg.xlsx", index=False, engine="openpyxl")

    return agg_categorized
