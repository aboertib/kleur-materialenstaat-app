from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from io import StringIO
from typing import Iterable, List

import pandas as pd
import streamlit as st
from docx import Document

BOUWDELEN = [
    "gevel", "kozijnen", "kozijn", "ramen", "raam", "deuren", "deur", "voordeur",
    "achterdeur", "schuifpui", "dak", "dakrand", "boeiboord", "goot",
    "hemelwaterafvoer", "hwa", "metselwerk", "plint", "balustrade", "vloer",
    "wand", "plafond", "trap", "hekwerk", "latei", "dorpel", "vensterbank"
]

MATERIALEN = [
    "baksteen", "metselwerk", "hout", "kunststof", "aluminium", "staal",
    "zink", "beton", "glas", "composiet", "vezelcement", "bitumen",
    "epdm", "dakpan", "stucwerk", "keimwerk", "rockpanel"
]

AFWERKINGEN = [
    "gepoedercoat", "geschilderd", "gelakt", "gebeitst", "verzinkt",
    "gebakken", "geschaafd", "mat", "glans", "structuur",
    "geborsteld", "onbehandeld", "geïmpregneerd", "naturel"
]

KLEURPATRONEN = [
    r"\bRAL\s?-?\s?\d{4}\b",
    r"\bkleur\s+[a-zA-ZÀ-ÿ0-9\- ]+",
    r"\bwit\b|\bzwart\b|\bantraciet\b|\bgrijs\b|\bbruin\b|\bbeige\b|\bgroen\b|\bblauw\b"
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
    Kleur: str
    Afwerking: str
    Bronregel: str


def normaliseer_spaties(tekst: str) -> str:
    return re.sub(r"\s+", " ", tekst).strip()


def vind_eerste_match(tekst: str, woordenlijst: Iterable[str]) -> str:
    tekst_lower = tekst.lower()
    for woord in woordenlijst:
        patroon = r"\b" + re.escape(woord.lower()) + r"\b"
        if re.search(patroon, tekst_lower):
            return woord
    return ""


def vind_kleur(tekst: str) -> str:
    for patroon in KLEURPATRONEN:
        match = re.search(patroon, tekst, re.IGNORECASE)
        if match:
            return normaliseer_spaties(match.group(0))
    return ""


def splits_regels(omschrijving: str) -> List[str]:
    return [
        normaliseer_spaties(regel)
        for regel in re.split(r"[\n.;]", omschrijving)
        if normaliseer_spaties(regel)
    ]


def analyseer_omschrijving(omschrijving: str) -> List[MateriaalRegel]:
    resultaten = []

    for regel in splits_regels(omschrijving):
        bouwdeel = vind_eerste_match(regel, BOUWDELEN)
        materiaal = vind_eerste_match(regel, MATERIALEN)
        kleur = vind_kleur(regel)
        afwerking = vind_eerste_match(regel, AFWERKINGEN)

        if bouwdeel or materiaal or kleur or afwerking:
            resultaten.append(
                MateriaalRegel(
                    Bouwdeel=bouwdeel or "Onbekend",
                    Materiaal=materiaal or "Niet gevonden",
                    Kleur=kleur or "Niet gevonden",
                    Afwerking=afwerking or "Niet gevonden",
                    Bronregel=regel,
                )
            )

    return resultaten


def resultaten_naar_dataframe(resultaten):
    return pd.DataFrame([asdict(r) for r in resultaten])


def maak_csv(df):
    buffer = StringIO()
    df.to_csv(buffer, index=False, sep=";", encoding="utf-8-sig")
    return buffer.getvalue().encode("utf-8-sig")


def lees_bestand(uploaded_file) -> str:
    if uploaded_file is None:
        return ""

    bestandstype = uploaded_file.name.split(".")[-1].lower()

    if bestandstype == "docx":
        document = Document(uploaded_file)
        tekst = []
        for paragraaf in document.paragraphs:
            if paragraaf.text.strip():
                tekst.append(paragraaf.text)
        return "\n".join(tekst)

    inhoud = uploaded_file.read()

    try:
        return inhoud.decode("utf-8")
    except UnicodeDecodeError:
        return inhoud.decode("latin-1")


def main():
    st.set_page_config(
        page_title="Kleur- en materialenstaat",
        page_icon="🏗️",
        layout="wide",
    )

    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg,#050816 0%,#0b1020 50%,#070816 100%);
        color: white;
    }

    .block-container {
        padding-top: 2rem;
        max-width: 1400px;
    }

    .stButton > button {
        background: linear-gradient(90deg,#7c3aed,#2563eb);
        color: white;
        border-radius: 14px;
        border: none;
        font-weight: 700;
    }

    div[data-testid='stDataFrame'] {
        border-radius: 18px;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("🏗️ Kleur- en materialenstaat generator")
    st.caption("Analyseer TXT, CSV en Word-documenten automatisch met AI-ready documentanalyse.")

    uploaded_file = st.file_uploader(
        "Upload technische omschrijving",
        type=["txt", "csv", "docx"],
        help="Ondersteunt TXT, CSV en Word-documenten (.docx)",
    )

    upload_tekst = lees_bestand(uploaded_file)

    standaardtekst = upload_tekst if upload_tekst else VOORBEELDTEKST

    omschrijving = st.text_area(
        "Technische omschrijving",
        value=standaardtekst,
        height=260,
    )

    if st.button("✨ Analyseer document", use_container_width=True):
        resultaten = analyseer_omschrijving(omschrijving)
        df = resultaten_naar_dataframe(resultaten)

        st.subheader("Kleur- en materialenstaat")

        if df.empty:
            st.warning("Geen herkenbare materialen gevonden.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.download_button(
                label="⬇ Download CSV",
                data=maak_csv(df),
                file_name="kleur_materialenstaat.csv",
                mime="text/csv",
                use_container_width=True,
            )

            st.success(f"{len(df)} regels gevonden.")


if __name__ == "__main__":
    main()
