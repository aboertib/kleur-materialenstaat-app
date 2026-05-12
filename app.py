from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from io import StringIO
from typing import Iterable, List

import pandas as pd
import streamlit as st

BOUWDELEN = [
    "gevel", "kozijnen", "dak", "dakrand", "hemelwaterafvoer", "voordeur"
]

MATERIALEN = [
    "baksteen", "kunststof", "aluminium", "zink", "hout"
]

AFWERKINGEN = [
    "gepoedercoat", "geschilderd", "gebakken", "naturel"
]

VOORBEELDTEKST = """Gevelmetselwerk uitvoeren in roodbruine baksteen, gebakken uitvoering.
Kozijnen uitvoeren in kunststof, kleur RAL 9010.
Dakrand voorzien van aluminium zetwerk, gepoedercoat in RAL 7016.
Hemelwaterafvoer uitvoeren in zink naturel.
Voordeur uitvoeren in hout, geschilderd zwart.
"""

@dataclass
class MateriaalRegel:
    Bouwdeel: str
    Materiaal: str
    Afwerking: str
    Bronregel: str


def vind_eerste_match(tekst: str, woordenlijst: Iterable[str]) -> str:
    tekst = tekst.lower()
    for woord in woordenlijst:
        if woord.lower() in tekst:
            return woord
    return "Niet gevonden"


def analyseer_omschrijving(omschrijving: str) -> List[MateriaalRegel]:
    resultaten = []

    regels = [r.strip() for r in re.split(r"[\n.;]", omschrijving) if r.strip()]

    for regel in regels:
        resultaten.append(
            MateriaalRegel(
                Bouwdeel=vind_eerste_match(regel, BOUWDELEN),
                Materiaal=vind_eerste_match(regel, MATERIALEN),
                Afwerking=vind_eerste_match(regel, AFWERKINGEN),
                Bronregel=regel,
            )
        )

    return resultaten


def dataframe_van_resultaten(resultaten):
    return pd.DataFrame([asdict(r) for r in resultaten])


def maak_csv(df):
    buffer = StringIO()
    df.to_csv(buffer, index=False, sep=';')
    return buffer.getvalue().encode('utf-8')


def main():
    st.set_page_config(page_title="Kleur- en materialenstaat", layout="wide")

    st.title("🏗️ Kleur- en materialenstaat generator")

    omschrijving = st.text_area(
        "Technische omschrijving",
        value=VOORBEELDTEKST,
        height=250,
    )

    if st.button("Genereer materialenstaat"):
        resultaten = analyseer_omschrijving(omschrijving)
        df = dataframe_van_resultaten(resultaten)

        st.dataframe(df, use_container_width=True)

        st.download_button(
            label="Download CSV",
            data=maak_csv(df),
            file_name="materialenstaat.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
