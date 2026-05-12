from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from io import StringIO
from typing import Iterable, List

import pandas as pd
import streamlit as st


BOUWDELEN = [
    "gevel", "kozijnen", "kozijn", "ramen", "raam", "deuren", "deur", "voordeur",
    "achterdeur", "schuifpui", "dak", "dakrand", "boeiboord", "goot",
    "hemelwaterafvoer", "hwa", "metselwerk", "plint", "balustrade", "vloer",
    "wand", "plafond", "trap", "hekwerk", "latei", "dorpel", "vensterbank",
    "luifel", "garagepoort", "berging", "erfafscheiding"
]

MATERIALEN = [
    "baksteen", "metselwerk", "hout", "hardhout", "vurenhout", "kunststof",
    "aluminium", "staal", "zink", "beton", "keramisch", "glas", "composiet",
    "vezelcement", "bitumen", "epdm", "dakpan", "dakpannen", "stucwerk",
    "keimwerk", "natuursteen", "multiplex", "hpl", "rockpanel"
]

AFWERKINGEN = [
    "gepoedercoat", "poedercoating", "geschilderd", "gelakt", "gebeitst",
    "verzinkt", "thermisch verzinkt", "gebakken", "geschaafd", "mat", "glans",
    "hoogglans", "zijdeglans", "structuur", "geborsteld", "onbehandeld",
    "geïmpregneerd", "geimpregneerd", "naturel", "gekeimd", "gespoten",
    "geanodiseerd", "gecoat"
]

KLEURPATRONEN = [
    r"\bRAL\s?-?\s?\d{4}\b",
    r"\bNCS\s?[A-Z0-9\- ]+\b",
    r"\bkleur\s+[a-zA-ZÀ-ÿ0-9\- ]+",
    r"\bwit\b|\bzwart\b|\bantraciet\b|\bgrijs\b|\bdonkergrijs\b|\blichtgrijs\b|\broodbruin\b|\brood\b|\bbruin\b|\bbeige\b|\bcrème\b|\bgroen\b|\bblauw\b|\bzandkleurig\b|\bnaturel\b|\btransparant\b"
]

VOORBEELDTEKST = """Gevelmetselwerk uitvoeren in roodbruine baksteen, gebakken uitvoering.
Kozijnen uitvoeren in kunststof, kleur RAL 9010.
Dakrand voorzien van aluminium zetwerk, gepoedercoat in RAL 7016.
Hemelwaterafvoer uitvoeren in zink naturel.
Voordeur uitvoeren in hout, geschilderd zwart.
Boeiboord uitvoeren in vezelcement, kleur antraciet.
"""


@dataclass
class MateriaalRegel:
    Bouwdeel: str
    Materiaal: str
    Kleur: str
    Afwerking: str
    Bronregel: str


def css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(124, 58, 237, 0.28), transparent 32%),
                radial-gradient(circle at top right, rgba(14, 165, 233, 0.15), transparent 25%),
                linear-gradient(135deg, #050711 0%, #0b1020 55%, #070816 100%);
            color: #f8fafc;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #070a13 0%, #0b1020 100%);
            border-right: 1px solid rgba(148, 163, 184, 0.18);
        }

        section[data-testid="stSidebar"] * { color: #e5e7eb !important; }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }

        .hero {
            padding: 28px 30px;
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 28px;
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.90), rgba(17, 24, 39, 0.72));
            box-shadow: 0 24px 70px rgba(0,0,0,.35);
            margin-bottom: 22px;
        }

        .eyebrow {
            display: inline-flex;
            gap: 8px;
            align-items: center;
            padding: 7px 12px;
            border-radius: 999px;
            background: rgba(124, 58, 237, .16);
            color: #c4b5fd;
            border: 1px solid rgba(167, 139, 250, .25);
            font-size: 13px;
            font-weight: 700;
            letter-spacing: .03em;
            text-transform: uppercase;
        }

        .hero h1 {
            margin: 16px 0 8px 0;
            font-size: clamp(2rem, 4vw, 4.2rem);
            line-height: 1.02;
            font-weight: 850;
            letter-spacing: -0.055em;
        }

        .gradient-text {
            background: linear-gradient(90deg, #ffffff 0%, #c4b5fd 42%, #60a5fa 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .hero p { color: #aeb7c6; font-size: 1.05rem; max-width: 850px; }

        .glass-card {
            padding: 22px;
            border-radius: 24px;
            background: linear-gradient(180deg, rgba(15, 23, 42, .86), rgba(15, 23, 42, .58));
            border: 1px solid rgba(148, 163, 184, .18);
            box-shadow: 0 20px 55px rgba(0,0,0,.30);
            min-height: 145px;
        }

        .metric-card {
            padding: 20px;
            border-radius: 22px;
            background: linear-gradient(135deg, rgba(124, 58, 237, .18), rgba(15, 23, 42, .72));
            border: 1px solid rgba(167, 139, 250, .18);
        }

        .metric-label { color: #9ca3af; font-size: .9rem; }
        .metric-value { color: #fff; font-size: 2rem; font-weight: 800; margin-top: 4px; }

        .status-step {
            padding: 10px 0;
            color: #cbd5e1;
            border-bottom: 1px solid rgba(148, 163, 184, .12);
        }

        .status-dot {
            display: inline-flex;
            width: 24px;
            height: 24px;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            background: linear-gradient(135deg, #8b5cf6, #22c55e);
            color: white;
            margin-right: 10px;
            font-weight: 800;
        }

        div[data-testid="stTextArea"] textarea {
            background: rgba(2, 6, 23, .82);
            color: #e5e7eb;
            border: 1px solid rgba(148, 163, 184, .24);
            border-radius: 18px;
        }

        div[data-testid="stFileUploader"] section {
            background: rgba(2, 6, 23, .54);
            border: 1px dashed rgba(167, 139, 250, .70);
            border-radius: 22px;
        }

        .stButton > button, .stDownloadButton > button {
            border-radius: 16px;
            border: 1px solid rgba(167, 139, 250, .35);
            background: linear-gradient(90deg, #7c3aed, #9333ea, #2563eb);
            color: white;
            font-weight: 800;
            padding: .75rem 1.1rem;
            box-shadow: 0 12px 30px rgba(124, 58, 237, .28);
        }

        .stDataFrame {
            border: 1px solid rgba(148, 163, 184, .18);
            border-radius: 22px;
            overflow: hidden;
        }

        hr { border-color: rgba(148, 163, 184, .15); }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
    return [normaliseer_spaties(r) for r in re.split(r"[\n.;]", omschrijving) if normaliseer_spaties(r)]


def analyseer_omschrijving(omschrijving: str) -> List[MateriaalRegel]:
    resultaten: List[MateriaalRegel] = []
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


def dataframe_van_resultaten(resultaten: List[MateriaalRegel]) -> pd.DataFrame:
    if not resultaten:
        return pd.DataFrame(columns=["Bouwdeel", "Materiaal", "Kleur", "Afwerking", "Bronregel"])
    return pd.DataFrame([asdict(r) for r in resultaten])


def maak_csv(df: pd.DataFrame) -> bytes:
    buffer = StringIO()
    df.to_csv(buffer, index=False, sep=";", encoding="utf-8-sig")
    return buffer.getvalue().encode("utf-8-sig")


def lees_upload(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    inhoud = uploaded_file.read()
    try:
        return inhoud.decode("utf-8")
    except UnicodeDecodeError:
        return inhoud.decode("latin-1")


def render_sidebar() -> tuple[bool, bool]:
    with st.sidebar:
        st.markdown("""
        <div style='padding:18px 8px 26px 8px'>
            <div style='font-size:34px;font-weight:900;letter-spacing:-.05em;color:#fff;'>K&M</div>
            <div style='color:#a78bfa;font-weight:800;margin-top:4px;'>Kleur & Materialenstaat</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### Dashboard")
        gebruik_voorbeeld = st.toggle("Gebruik voorbeeldtekst", value=True)
        toon_bronregels = st.toggle("Toon bronregels", value=True)

        st.markdown("---")
        st.markdown("""
        <div class='glass-card'>
            <div class='eyebrow'>AI-powered demo</div>
            <h3 style='margin-top:16px;color:white;'>Slimmer bouwen met AI</h3>
            <p style='color:#aeb7c6;font-size:.92rem;'>Analyseer technische omschrijvingen en zet informatie direct om naar een bruikbare materialenstaat.</p>
        </div>
        """, unsafe_allow_html=True)
    return gebruik_voorbeeld, toon_bronregels


def main() -> None:
    st.set_page_config(page_title="Kleur- en materialenstaat", page_icon="🏗️", layout="wide")
    css()
    gebruik_voorbeeld, toon_bronregels = render_sidebar()

    st.markdown(
        """
        <div class='hero'>
            <div class='eyebrow'>ThuisinBouwen · Procesautomatisering</div>
            <h1><span class='gradient-text'>Kleur- en materialenstaat</span><br/>in enkele seconden</h1>
            <p>Upload of plak een technische omschrijving. De applicatie herkent bouwdelen, materialen, kleuren en afwerkingen en zet deze om naar een overzichtelijke export.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Upload technische omschrijving",
        type=["txt", "csv"],
        help="Voor deze demo worden tekstbestanden ondersteund. PDF-analyse kan later toegevoegd worden.",
    )
    upload_tekst = lees_upload(uploaded_file)
    standaardtekst = VOORBEELDTEKST if gebruik_voorbeeld and not upload_tekst else upload_tekst

    left, right = st.columns([1.65, 1], gap="large")
    with left:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Nieuwe analyse")
        omschrijving = st.text_area("Technische omschrijving", value=standaardtekst, height=270)
        analyse_knop = st.button("✨ Analyseer document", type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    resultaten = analyseer_omschrijving(omschrijving) if (analyse_knop or omschrijving.strip()) else []
    df = dataframe_van_resultaten(resultaten)
    export_df = df if toon_bronregels else df.drop(columns=["Bronregel"], errors="ignore")

    with right:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Analyse status")
        pct = 100 if not df.empty else 0
        st.progress(pct)
        st.markdown(
            f"""
            <div class='status-step'><span class='status-dot'>✓</span>Document ingelezen</div>
            <div class='status-step'><span class='status-dot'>✓</span>Tekst geanalyseerd</div>
            <div class='status-step'><span class='status-dot'>✓</span>{len(df)} regels gevonden</div>
            <div class='status-step'><span class='status-dot'>✓</span>Export voorbereid</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    metrics = [
        (m1, len(export_df), "Regels gevonden"),
        (m2, export_df["Bouwdeel"].nunique() if not export_df.empty and "Bouwdeel" in export_df else 0, "Bouwdelen"),
        (m3, export_df["Materiaal"].nunique() if not export_df.empty and "Materiaal" in export_df else 0, "Materialen"),
        (m4, "CSV", "Export formaat"),
    ]
    for col, value, label in metrics:
        with col:
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{value}</div><div class='metric-label'>{label}</div></div>", unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    topbar1, topbar2 = st.columns([3, 1])
    with topbar1:
        st.subheader("Kleur- en materialenstaat")
    with topbar2:
        st.download_button("⬇ Exporteren", data=maak_csv(export_df), file_name="kleur_materialenstaat.csv", mime="text/csv", use_container_width=True)

    if export_df.empty:
        st.warning("Geen herkenbare materialen, kleuren of afwerkingen gevonden.")
    else:
        st.dataframe(export_df, use_container_width=True, hide_index=True, height=360)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Volgende uitbreidingen"):
        st.markdown("""
        - PDF-upload met tekstextractie.
        - AI-analyse via OpenAI of Azure OpenAI.
        - Export naar Excel.
        - Projectdatabase en login.
        - Koppeling met SharePoint, Teams of Revit-data.
        """)


if __name__ == "__main__":
    main()
