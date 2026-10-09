
import re
import json
import html
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Amadeus Itinerary Generator",
    page_icon="✈️",
    layout="wide",
)

AIRPORTS = {
    "LJU": ("Ljubljana", "Europe/Ljubljana"),
    "TRS": ("Trst", "Europe/Rome"),
    "VCE": ("Benetke", "Europe/Rome"),
    "MXP": ("Milano Malpensa", "Europe/Rome"),
    "LIN": ("Milano Linate", "Europe/Rome"),
    "FCO": ("Rim Fiumicino", "Europe/Rome"),
    "CIA": ("Rim Ciampino", "Europe/Rome"),
    "NAP": ("Neapelj", "Europe/Rome"),
    "BRI": ("Bari", "Europe/Rome"),
    "BLQ": ("Bologna", "Europe/Rome"),
    "BGY": ("Bergamo", "Europe/Rome"),
    "VRN": ("Verona", "Europe/Rome"),
    "ZAG": ("Zagreb", "Europe/Zagreb"),
    "SPU": ("Split", "Europe/Zagreb"),
    "DBV": ("Dubrovnik", "Europe/Zagreb"),
    "BEG": ("Beograd", "Europe/Belgrade"),
    "SJJ": ("Sarajevo", "Europe/Sarajevo"),
    "SKP": ("Skopje", "Europe/Skopje"),
    "VIE": ("Dunaj", "Europe/Vienna"),
    "GRZ": ("Gradec", "Europe/Vienna"),
    "MUC": ("München", "Europe/Berlin"),
    "FRA": ("Frankfurt", "Europe/Berlin"),
    "BER": ("Berlin", "Europe/Berlin"),
    "HAM": ("Hamburg", "Europe/Berlin"),
    "DUS": ("Düsseldorf", "Europe/Berlin"),
    "ZRH": ("Zürich", "Europe/Zurich"),
    "GVA": ("Ženeva", "Europe/Zurich"),
    "CDG": ("Pariz Charles de Gaulle", "Europe/Paris"),
    "ORY": ("Pariz Orly", "Europe/Paris"),
    "AMS": ("Amsterdam", "Europe/Amsterdam"),
    "BRU": ("Bruselj", "Europe/Brussels"),
    "LHR": ("London Heathrow", "Europe/London"),
    "LGW": ("London Gatwick", "Europe/London"),
    "MAN": ("Manchester", "Europe/London"),
    "DUB": ("Dublin", "Europe/Dublin"),
    "MAD": ("Madrid", "Europe/Madrid"),
    "BCN": ("Barcelona", "Europe/Madrid"),
    "LIS": ("Lizbona", "Europe/Lisbon"),
    "ATH": ("Atene", "Europe/Athens"),
    "IST": ("Istanbul", "Europe/Istanbul"),
    "SAW": ("Istanbul Sabiha Gökçen", "Europe/Istanbul"),
    "DOH": ("Doha", "Asia/Qatar"),
    "DXB": ("Dubaj", "Asia/Dubai"),
    "AUH": ("Abu Dabi", "Asia/Dubai"),
    "JFK": ("New York JFK", "America/New_York"),
    "EWR": ("Newark", "America/New_York"),
    "LAX": ("Los Angeles", "America/Los_Angeles"),
    "SFO": ("San Francisco", "America/Los_Angeles"),
    "ORD": ("Chicago O’Hare", "America/Chicago"),
    "MIA": ("Miami", "America/New_York"),
    "YYZ": ("Toronto", "America/Toronto"),
    "YVR": ("Vancouver", "America/Vancouver"),
    "BKK": ("Bangkok", "Asia/Bangkok"),
    "SIN": ("Singapur", "Asia/Singapore"),
    "KUL": ("Kuala Lumpur", "Asia/Kuala_Lumpur"),
    "HKG": ("Hongkong", "Asia/Hong_Kong"),
    "PVG": ("Šanghaj Pudong", "Asia/Shanghai"),
    "PEK": ("Peking", "Asia/Shanghai"),
    "NRT": ("Tokio Narita", "Asia/Tokyo"),
    "HND": ("Tokio Haneda", "Asia/Tokyo"),
    "ICN": ("Seul Incheon", "Asia/Seoul"),
    "TPE": ("Taipei", "Asia/Taipei"),
    "SYD": ("Sydney", "Australia/Sydney"),
    "MEL": ("Melbourne", "Australia/Melbourne"),
    "CPT": ("Cape Town", "Africa/Johannesburg"),
    "JNB": ("Johannesburg", "Africa/Johannesburg"),
    "CAI": ("Kairo", "Africa/Cairo"),
    "NBO": ("Nairobi", "Africa/Nairobi"),
    "ADD": ("Adis Abeba", "Africa/Addis_Ababa"),
    "TBS": ("Tbilisi", "Asia/Tbilisi"),
    "EVN": ("Erevan", "Asia/Yerevan"),
    "ALA": ("Almaty", "Asia/Almaty"),
    "DEL": ("Delhi", "Asia/Kolkata"),
    "BOM": ("Mumbai", "Asia/Kolkata"),
    "CMB": ("Colombo", "Asia/Colombo"),
    "MLE": ("Malé", "Indian/Maldives"),
    "MRU": ("Mauritius", "Indian/Mauritius"),
    "TFS": ("Tenerife South", "Atlantic/Canary"),
    "LPA": ("Gran Canaria", "Atlantic/Canary"),
    "PMI": ("Palma de Mallorca", "Europe/Madrid"),
    "AGP": ("Málaga", "Europe/Madrid"),
    "ALC": ("Alicante", "Europe/Madrid"),
    "IBZ": ("Ibiza", "Europe/Madrid"),
    "HER": ("Heraklion", "Europe/Athens"),
    "RHO": ("Rodos", "Europe/Athens"),
    "AYT": ("Antalya", "Europe/Istanbul"),
    "DPS": ("Bali Denpasar", "Asia/Makassar"),
    "MNL": ("Manila", "Asia/Manila"),
    "SGN": ("Hošiminh", "Asia/Ho_Chi_Minh"),
    "HAN": ("Hanoj", "Asia/Ho_Chi_Minh"),
    "USM": ("Koh Samui", "Asia/Bangkok"),
    "HKT": ("Phuket", "Asia/Bangkok"),
    "KTM": ("Katmandu", "Asia/Kathmandu"),
}

MONTHS = {
    m.upper(): i
    for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        1,
    )
}

HEADERS = [
    "Datum",
    "Let",
    "Relacija",
    "Odhod",
    "Prihod",
    "Trajanje leta",
    "Čas prestopa",
]


def airport(code):
    return AIRPORTS.get(code, (code, "UTC"))[0]


def tz(code):
    return AIRPORTS.get(code, (code, "UTC"))[1]


def fmt_time(value):
    return value.strftime("%H:%M")


def fmt_duration(minutes):
    if minutes is None or minutes < 0:
        return "—"
    hours, mins = divmod(minutes, 60)
    return f"{hours} h {mins:02d} min"


def parse_date(token, year):
    match = re.fullmatch(r"(\d{1,2})([A-Z]{3})", token.upper())
    if not match or match.group(2) not in MONTHS:
        return None

    try:
        return date(
            year,
            MONTHS[match.group(2)],
            int(match.group(1)),
        )
    except ValueError:
        return None


def parse_segments(raw):
    segments = []

    start_re = re.compile(
        r"^\s*(?:\d+\s+)?"
        r"([A-Z0-9]{2,3}\s?\d{1,4}[A-Z]?)\s+"
        r"([A-Z])\s+"
        r"(\d{1,2}[A-Z]{3})\b(.*)$",
        re.I,
    )

    time_re = re.compile(
        r"(?<!\d)(\d{4})(?:\+(\d))?\s+"
        r"(\d{4})(?:\+(\d))?(?!\d)"
    )

    # Samodejno določanje letnice:
    # - uporabi tekoče leto za prihodnje datume;
    # - če je prvi datum že minil, predpostavi naslednje leto;
    # - če se datum med zaporednimi leti premakne nazaj,
    #   upošteva prehod v naslednje leto.
    current_year = datetime.now().year
    today = date.today()
    previous_date = None

    for line in raw.splitlines():
        match = start_re.match(line)
        if not match:
            continue

        flight, _booking_class, date_token, remainder = match.groups()
        times = time_re.search(remainder)

        if not times:
            continue

        dep_token, dep_plus, arr_token, arr_plus = times.groups()

        route_part = remainder[:times.start()].upper()
        route_part = re.sub(
            r"\b(?:HK|HN|HL|TK|KL|SS|NN|GK)\d*\b",
            " ",
            route_part,
        )
        route_part = re.sub(r"\b\d+\b", " ", route_part)

        route_tokens = re.findall(r"[A-Z]{3,6}", route_part)
        origin = destination = None

        joined = next(
            (
                token
                for token in route_tokens
                if len(token) == 6
                and token[:3] in AIRPORTS
                and token[3:] in AIRPORTS
            ),
            None,
        )

        if joined:
            origin, destination = joined[:3], joined[3:]
        else:
            three = [token for token in route_tokens if len(token) == 3]
            if len(three) >= 2:
                origin, destination = three[0], three[1]

        if not origin or not destination:
            continue

        dep_date = parse_date(date_token, current_year)
        if dep_date is None:
            continue

        if previous_date is None:
            if dep_date < today:
                dep_date = parse_date(date_token, current_year + 1)
        elif dep_date < previous_date:
            dep_date = parse_date(date_token, previous_date.year + 1)

        if dep_date is None:
            continue

        current_year = dep_date.year
        previous_date = dep_date

        dep_time = datetime.strptime(dep_token, "%H%M").time()
        arr_time = datetime.strptime(arr_token, "%H%M").time()

        dep_local = datetime.combine(dep_date, dep_time).replace(
            tzinfo=ZoneInfo(tz(origin))
        )

        arr_date = dep_date + timedelta(days=int(arr_plus or 0))
        arr_local = datetime.combine(arr_date, arr_time).replace(
            tzinfo=ZoneInfo(tz(destination))
        )

        # Če prihod po pretvorbi časovnih pasov pomeni naslednji dan,
        # upoštevaj dodatni dan tudi, kadar ga izpis ne navede.
        if (
            arr_local.astimezone(ZoneInfo("UTC"))
            < dep_local.astimezone(ZoneInfo("UTC"))
        ):
            arr_local += timedelta(days=1)

        duration = int(
            (
                arr_local.astimezone(ZoneInfo("UTC"))
                - dep_local.astimezone(ZoneInfo("UTC"))
            ).total_seconds()
            // 60
        )

        segments.append(
            {
                "flight": re.sub(r"\s+", "", flight.upper()),
                "date": dep_date,
                "origin": origin,
                "destination": destination,
                "dep": dep_local,
                "arr": arr_local,
                "duration": duration,
            }
        )

    # Čas prestopa izračunamo med zaporednimi leti.
    for i, seg in enumerate(segments):
        seg["layover"] = None

        if (
            i + 1 < len(segments)
            and seg["destination"] == segments[i + 1]["origin"]
        ):
            minutes = int(
                (
                    segments[i + 1]["dep"].astimezone(ZoneInfo("UTC"))
                    - seg["arr"].astimezone(ZoneInfo("UTC"))
                ).total_seconds()
                // 60
            )

            if 0 <= minutes <= 18 * 60:
                seg["layover"] = minutes

    return segments


def format_text(segments):
    lines = []

    for seg in segments:
        route = (
            f"{airport(seg['origin'])} ({seg['origin']}) – "
            f"{airport(seg['destination'])} ({seg['destination']})"
        )
        date_text = seg["date"].strftime("%d.%m.%Y")
        arr_plus = " +1" if seg["arr"].date() > seg["date"] else ""

        line = (
            f"{date_text}  {seg['flight']}  {route}  "
            f"{fmt_time(seg['dep'])}–{fmt_time(seg['arr'])}{arr_plus}"
        )

        if seg["layover"] is not None:
            line += f"    * Čas prestopa: {fmt_duration(seg['layover'])}"

        lines.append(line)

    return "\n".join(lines)


def display_table(segments):
    rows = []

    for seg in segments:
        rows.append(
            {
                "Datum": seg["date"].strftime("%d.%m.%Y"),
                "Let": seg["flight"],
                "Relacija": (
                    f"{airport(seg['origin'])} ({seg['origin']}) – "
                    f"{airport(seg['destination'])} ({seg['destination']})"
                ),
                "Odhod": fmt_time(seg["dep"]),
                "Prihod": fmt_time(seg["arr"])
                + (" +1" if seg["arr"].date() > seg["date"] else ""),
                "Trajanje leta": fmt_duration(seg["duration"]),
                "Čas prestopa": (
                    fmt_duration(seg["layover"])
                    if seg["layover"] is not None
                    else "—"
                ),
            }
        )

    return rows


def render_copyable_table(rows):
    # Besedilna različica: uporabna za Excel in kot rezervni način kopiranja.
    tsv = "\t".join(HEADERS) + "\n"
    tsv += "\n".join(
        "\t".join(str(row[header]) for header in HEADERS)
        for row in rows
    )

    # HTML različica omogoča kopiranje oblikovane tabele v e-pošto.
    thead = "".join(
        f"<th>{html.escape(header)}</th>" for header in HEADERS
    )

    tbody = ""
    for row in rows:
        cells = "".join(
            f"<td>{html.escape(str(row[header]))}</td>"
            for header in HEADERS
        )
        tbody += f"<tr>{cells}</tr>"

    table_html = f"""
    <table style="
        border-collapse:collapse;
        width:100%;
        font-family:Arial,sans-serif;
        font-size:13px;
    ">
      <thead>
        <tr>{thead}</tr>
      </thead>
      <tbody>{tbody}</tbody>
    </table>
    """

    # JSON varno prenese vsebino v JavaScript.
    safe_tsv = json.dumps(tsv, ensure_ascii=False)
    safe_table_html = json.dumps(table_html, ensure_ascii=False)

    page = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{
          margin: 0;
          padding: 4px 0 8px;
          font-family: Arial, sans-serif;
          color: #222;
        }}
        .toolbar {{
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 12px;
        }}
        button {{
          border: 0;
          border-radius: 7px;
          padding: 10px 16px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          background: #176b57;
          color: white;
        }}
        button:hover {{ background: #105441; }}
        #status {{ font-size: 13px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{
          border: 1px solid #d9d9d9;
          padding: 9px 10px;
          text-align: left;
          vertical-align: top;
        }}
        th {{
          font-weight: 700;
          background: #f3f5f4;
          white-space: nowrap;
        }}
        tr:nth-child(even) {{ background: #fafafa; }}
        .table-wrap {{ overflow-x: auto; }}
      </style>
    </head>
    <body>
      <div class="toolbar">
        <button id="copyButton" type="button">📋 Kopiraj tabelo</button>
        <span id="status" role="status"></span>
      </div>
      <div class="table-wrap" id="tableWrap">{table_html}</div>
      <script>
        const plainText = {safe_tsv};
        const richHtml = {safe_table_html};

        document.getElementById("copyButton").addEventListener("click", async () => {{
          const status = document.getElementById("status");

          try {{
            if (navigator.clipboard && window.ClipboardItem) {{
              const item = new ClipboardItem({{
                "text/html": new Blob([richHtml], {{type: "text/html"}}),
                "text/plain": new Blob([plainText], {{type: "text/plain"}})
              }});
              await navigator.clipboard.write([item]);
              status.textContent = "Tabela je kopirana! Prilepi jo v e-pošto ali Excel.";
              return;
            }}

            if (navigator.clipboard && navigator.clipboard.writeText) {{
              await navigator.clipboard.writeText(plainText);
              status.textContent = "Tabela je kopirana kot besedilo.";
              return;
            }}

            throw new Error("Clipboard API unavailable");
          }} catch (error) {{
            // Rezervna možnost: uporabnik lahko besedilo ročno kopira.
            const area = document.createElement("textarea");
            area.value = plainText;
            area.style.position = "fixed";
            area.style.left = "0";
            area.style.top = "0";
            area.style.width = "100%";
            area.style.height = "120px";
            area.style.zIndex = "9999";
            document.body.appendChild(area);
            area.focus();
            area.select();

            const copied = document.execCommand("copy");
            area.remove();

            status.textContent = copied
              ? "Tabela je kopirana kot besedilo."
              : "Kopiranje ni uspelo. Poskusi še enkrat ali označi tabelo.";
          }}
        }});
      </script>
    </body>
    </html>
    """

    height = min(850, 165 + len(rows) * 43)
    components.html(page, height=height, scrolling=True)


st.title("✈️ Amadeus Itinerary Generator")
st.write(
    "Prilepi Amadeus izpis letov in pripravi itinerar za kopiranje v e-pošto."
)

raw = st.text_area(
    "Amadeus zapis",
    height=250,
    placeholder="Prilepi vrstice z leti iz Amadeusa …",
)

if st.button("Ustvari itinerar", type="primary", use_container_width=True):
    if not raw.strip():
        st.warning("Najprej prilepi Amadeus zapis letov.")
    else:
        segments = parse_segments(raw)

        if not segments:
            st.error(
                "Nisem prepoznala nobenega leta. Prilepi vrstice z leti "
                "(številka leta, datum, relacija in časi) in poskusi znova."
            )
        else:
            st.session_state["segments"] = segments
            st.success(f"Prepoznanih letov: {len(segments)}")

if st.session_state.get("segments"):
    segments = st.session_state["segments"]

    st.subheader("Besedilo za e-pošto")
    output = format_text(segments)
    st.code(output, language=None)

    st.download_button(
        "Prenesi besedilo (.txt)",
        data=output,
        file_name="itinerar.txt",
        mime="text/plain; charset=utf-8",
    )

    st.subheader("Preglednica")
    rows = display_table(segments)
    render_copyable_table(rows)

    st.caption(
        "Opomba: pri neznanih letališčih je za izračun uporabljena "
        "privzeta časovna cona UTC. Letnica se določa samodejno; "
        "pred pošiljanjem preveri datume, čase in prestope."
    )

st.divider()
st.caption(
    "V orodje ne vnašaj imen potnikov, številk kart ali drugih osebnih "
    "podatkov — zadostujejo vrstice z leti."
)
