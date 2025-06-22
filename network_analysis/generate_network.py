import networkx as nx
from pyvis.network import Network
import webbrowser
import pandas as pd


def build_network(
        df:pd.DataFrame,
        kto_nr,
        kto_name,
        gkto_nr,
        gkto_name,
        soll,
        haben,
        saldo,
        kto_kategorie,        
        filename:str="graph.html",
        schwelle:int=15000
        ):
    """Takes a df with the """
    G = generate_network_graph(
        df,
        kto_nr,
        kto_name,
        gkto_nr,
        gkto_name,
        soll,
        haben,
        saldo,
        kto_kategorie,
        schwelle
        )
    visualize_graph(G, filename)


def _get_node_color(kategorie: str) -> str:
    farben = {
        "Umsatzerlöse": "#fbffa5",
        "Sonstige Erlöse": "#FBFF87FF",
        "Debitoren": "#000000",
        "Aufwand": "#5CA3FF",
        "Sonstige Forderungen": "#000000",
        "Kreditoren": "#000000",
        "Zahlungsmittel": "#c300d5",
        "Verrechnungskonten": "#c300d5", 
        "Umsatzsteuer": "#c300d5", 
        "Sonstige Aktiva": "#FFFFFF",
        "Sonstige Passiva": "#B7B7B7",
        "Eröffnungskonten": "#ffffff",
    }
    return farben.get(kategorie, "#cccccc")


def _get_edge_style(src_kat: str, dst_kat: str, summe_soll: float, summe_haben: float, schwelle: float, max_betrag: float) -> dict:
    betrag = max(abs(summe_soll), abs(summe_haben))
    style = {}

    # Bewertungslogik (symmetrisch plausible Kombinationen)
    plausible_combinations = [
        ("Umsatzerlöse", "Debitoren"),
        ("Umsatzerlöse", "Kreditoren"),
        ("Aufwand", "Kreditoren"),
        ("Debitoren", "Zahlungsmittel"),
        ("Sonstige Forderungen", "Zahlungsmittel"),
        ("Kreditoren", "Zahlungsmittel"),
        ("Sonstige Erlöse", "Debitoren"),
        ("Sonstige Erlöse", "Kreditoren"),
    ]
    plausible_combinations += [(b, a) for (a, b) in plausible_combinations]  # bidirektional

    critic_combinations = [
        ("Aufwand", "Zahlungsmittel"),
        ("Aufwand", "Verrechnungskonten"),
        ("Debitoren", "Verrechnungskonten"),
        ("Debitoren", "Sonstige Passiva"),
        ("Debitoren", "Sonstige Aktiva"),
        ("Kreditoren", "Verrechnungskonten"),
        ("Kreditoren", "Sonstige Aktiva"),
        ("Kreditoren", "Sonstige Passiva"),
    ]
    critic_combinations += [(b, a) for (a, b) in critic_combinations]  # bidirektional

    irrelevant_combinations = [
        ("Sonstige Passiva", "Sonstige Aktiva"),
        ("Sonstige Erlöse", "Sonstige Passiva"),
        ("Sonstige Erlöse", "Sonstige Aktiva"),
        ("Sonstige Erlöse", "Zahlungsmittel"),
        ("Sonstige Aktiva", "Zahlungsmittel"),
        ("Sonstige Passiva", "Zahlungsmittel"),
        ("Sonstige Forderungen", "Sonstige Passiva"),
        ("Sonstige Forderungen", "Sonstige Aktiva"),
        ("Aufwand", "Sonstige Passiva"),
        ("Aufwand", "Sonstige Aktiva"),
    ]
    irrelevant_combinations += [(b, a) for (a, b) in irrelevant_combinations]  # bidirektional

    if ("Eröffnungskonten") in (src_kat, dst_kat):
        style["color"] = "#B7D6FF"
        style["opacity"] = 0.25
    elif (src_kat, dst_kat) in plausible_combinations:
        style["color"] = "#00d515" 
        style["opacity"] = 1.0
    elif betrag < schwelle:
        style["color"] = "#999999"
        style["opacity"] = 0.5
    elif("Umsatzsteuer") in (src_kat, dst_kat):
        style["color"] = "#00d515",
        style["opacity"] = 1.0
    elif src_kat == dst_kat:
        style["color"] = "#999999"  # Selbstbuchung
        style["opacity"] = 0.5
    elif (src_kat, dst_kat) in irrelevant_combinations:
        style["color"] = "#999999" 
        style["opacity"] = 0.5
    elif (src_kat, dst_kat) in critic_combinations:
        style["color"] = "#ffbf00"
        style["opacity"] = 1.0
    else:
        style["color"] = "#ff0000" 
        style["opacity"] = 1.0

    # Dashes bei niedriger Bedeutung oder technischen Konten
    style["dashes"] = betrag < schwelle

    # Normalisierte Kantenbreite
    min_width, max_width = 1.0, 5.0
    norm_width = min_width + (betrag / max_betrag) * (max_width - min_width)
    style["width"] = round(norm_width, 2)

    return style




def generate_network_graph(
        df:pd.DataFrame,
        kto_nr:str,
        kto_name:str,
        gkto_nr:str,
        gkto_name:str,
        soll:str,
        haben:str,
        saldo:str,
        kto_kategorie:str,
        schwelle: float = 0,
    ):
    """
    Erstellt einen gerichteten Netzwerk-Graphen mit farbigen Knoten und Kanten.

    Alle Spaltennamen werden als Funktionsargumente übergeben, sodass
    dieselbe Logik auch bei anders benannten DataFrames funktioniert.
    """

    G = nx.DiGraph()

    # Maximalbetrag für die Kantenbreitenskalierung
    max_betrag = df[[soll, haben]].abs().max().max()

    # Knoten erstellen
    src_konten = (
        df
        .groupby(kto_nr)
        .agg({
            kto_name:      "first",
            kto_kategorie: "first",
            soll:          "sum",
            haben:         "sum",
            saldo:         "sum",
        })
        .reset_index()
    )

    ## Anzahl der Verbindungen pro Konto
    edge_counts = df[kto_nr].value_counts() + df[gkto_nr].value_counts()
    edge_counts = edge_counts.fillna(0)

    for _, row in src_konten.iterrows():
        farbe = _get_node_color(row[kto_kategorie])

        ### Gegenkonten-Listen für Tooltip
        title_df_soll = (
            df[df[kto_nr] == row[kto_nr]][[gkto_nr, gkto_name, soll]]
            .sort_values(by=soll, ascending=False)
        )
        title_df_haben = (
            df[df[kto_nr] == row[kto_nr]][[gkto_nr, gkto_name, haben]]
            .sort_values(by=haben, ascending=False)
        )

        gegen_text_soll = (
            "\n".join(
                f"{betrag:_>16,.2f} €  {dst:<10}  {name}"
                for dst, name, betrag in title_df_soll.values
            )
            if not title_df_soll.empty else "keine"
        )

        gegen_text_haben = (
            "\n".join(
                f"{betrag:_>16,.2f} €  {dst:<10}  {name}"
                for dst, name, betrag in title_df_haben.values
            )
            if not title_df_haben.empty else "keine"
        )

        title_text = (
            f"Konto: {row[kto_nr]}\n"
            f"Name: {row[kto_name]}\n"
            f"Kategorie: {row[kto_kategorie]}\n"
            f"Saldo: {row[saldo]:,.2f} €\n"
            f"=== Gegenkonten Soll: =============\n{gegen_text_soll}\n\n"
            f"=== Gegenkonten Haben: ============\n{gegen_text_haben}"
        )

        num_edges = edge_counts.get(row[kto_nr], 1)
        size = min(20, max(10, num_edges * 0.25))  # (min 10, max 20)

        G.add_node(
            row[kto_nr],
            label=str(row[kto_nr]),
            title=title_text,
            color=farbe,
            size=size,
        )

    # Kanten erzeugen
    ## Ziel-Kategorien ergänzen
    df = (
        df.merge(
            df[[kto_nr, kto_kategorie]].drop_duplicates(),
            how="left",
            left_on=gkto_nr,
            right_on=kto_nr,
            suffixes=("", "_dst"),
        )
        .rename(columns={f"{kto_kategorie}_dst": "dst_kategorie"})
        .drop(columns=[f"{kto_nr}_dst"])
    )

    for _, row in df.iterrows():
        if row[soll] > 0:  # nur Soll-Flüsse darstellen
            style = _get_edge_style(
                row[kto_kategorie],
                row["dst_kategorie"],
                row[soll],
                row[haben],
                schwelle=schwelle,
                max_betrag=max_betrag,
            )

            edge_title = (
                f"{row[kto_nr]}\n"
                f"{row[kto_name]}\n"
                f"{row[kto_kategorie]}\n"
                "→\n"
                f"{row[gkto_nr]}\n"
                f"{row[gkto_name]}\n"
                f"{row['dst_kategorie']}\n"
                "\nBetrag:\n"
                f"{row[soll]:,.2f} €"
            )

            G.add_edge(
                row[kto_nr],
                row[gkto_nr],
                value=row[soll],
                title=edge_title,
                color=style["color"],
                width=style["width"],
                dashes=style["dashes"],
            )

    return G


def visualize_graph(G, filename="graph.html"):
    net = Network(
        height="2160px", # = 4k; "1080px" = FHD
        width="100%",
        directed=True,
        bgcolor="#FFFFFF",
        notebook=False,
        cdn_resources='in_line'
    )
    net.from_nx(G)
    net.set_options("""
const options = {
  "physics": {
    "forceAtlas2Based": {
      "theta": 0.8,
      "gravitationalConstant": -50,
      "centralGravity": 0.02,
      "springLength": 100,
      "springConstant": 0.15,
      "damping": 0.4,
      "avoidOverlap": 0.9
    },
    "maxVelocity": 50,
    "minVelocity": 0.5,
    "solver": "forceAtlas2Based",
    "timestep": 0.2,
    "wind": {
      "x": 0,
      "y": 0
    }
  },
  "interaction": {
    "tooltipDelay": 200,
    "hideEdgesOnDrag": false,
    "hideNodesOnDrag": false,
    "navigationButtons": true,
    "keyboard": true
  },
  "configure": {
    "enabled": true,
    "filter": ["nodes", "edges"],
    "showButton": true
  }
}
""")
    html = net.generate_html()
    html = add_legend_to_pyvis_html(html)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)


def add_legend_to_pyvis_html(html: str):
    node_legend = {
        "Umsatzerlöse": "#fbffa5",
        "Sonstige Erlöse": "#FBFF87FF",
        "Aufwand": "#5CA3FF",
        "Debitoren": "#000000",
        "Sonstige Forderungen": "#000000",
        "Kreditoren": "#000000",
        "Zahlungsmittel": "#c300d5",
        "Verrechnungskonten": "#c300d5", 
        "Umsatzsteuer": "#c300d5", 
        "Sonstige Aktiva": "#FFFFFF",
        "Sonstige Passiva": "#B7B7B7",
        "Eröffnungskonten": "#ffffff",
    }

    edge_legend = {
        "Plausible Kombinationen": "green",
        "Risikobehaftete Kombinationen": "yellow",
        "Kritische Kombinationen": "red",
        "Irrelevante Kombinationen": "gray",
        "Eröffnungsbuchungen": "lightblue"
    }

    # HTML für die Legende zusammenbauen
    legend_html = """
<style>
.legend-box {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: white;
    border: 1px solid #aaa;
    padding: 10px;
    font-family: Arial, sans-serif;
    font-size: 12px;
    box-shadow: 0 0 10px rgba(0,0,0,0.2);
    max-width: 200px;
    z-index: 999;
}
.legend-box table {
    width: 100%;
    border-collapse: collapse;
}
.legend-box td {
    padding: 2px 4px;
    vertical-align: middle;
}
.color-box {
    width: 12px;
    height: 12px;
    display: inline-block;
    border: 1px solid #444;
    margin-right: 5px;
}
.legend-section {
    margin-top: 6px;
    margin-bottom: 4px;
    font-weight: bold;
    border-bottom: 1px solid #ccc;
}
</style>

<div class="legend-box">
    <div class="legend-section">Knoten</div>
    <table>
"""

    for label, color in node_legend.items():
        legend_html += f"""
        <tr>
            <td><span class="color-box" style="background:{color};"></span></td>
            <td>{label}</td>
        </tr>
        """

    legend_html += """
    </table>
    <div class="legend-section">Kanten</div>
    <table>
"""

    for label, color in edge_legend.items():
        legend_html += f"""
        <tr>
            <td><span class="color-box" style="background:{color};"></span></td>
            <td>{label}</td>
        </tr>
        """

    legend_html += """
    </table>
</div>
"""

    html = html.replace("</body>", legend_html + "\n</body>")
    return html