import re
import html
import json
import csv
import io
from urllib.request import urlopen
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st
import airportsdata
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Amadeus – potovalni načrt",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ Amadeus – potovalni načrt")
st.caption(
    "Prilepi letalske segmente iz Amadeusa in ustvari pregledno tabelo za stranko."
)

# ---------------------------------------------------------
# LETALIŠČA
# ---------------------------------------------------------

AIRPORTS = {
    "LJU": ("Ljubljana", "Europe/Ljubljana"),
    "ZAG": ("Zagreb", "Europe/Zagreb"),
    "VIE": ("Dunaj", "Europe/Vienna"),
    "TRS": ("Trst", "Europe/Rome"),
    "VCE": ("Benetke", "Europe/Rome"),
    "MXP": ("Milano Malpensa", "Europe/Rome"),
    "LIN": ("Milano Linate", "Europe/Rome"),
    "FCO": ("Rim Fiumicino", "Europe/Rome"),
    "CIA": ("Rim Ciampino", "Europe/Rome"),
    "NAP": ("Neapelj", "Europe/Rome"),
    "BLQ": ("Bologna", "Europe/Rome"),
    "CDG": ("Pariz Charles de Gaulle", "Europe/Paris"),
    "ORY": ("Pariz Orly", "Europe/Paris"),
    "AMS": ("Amsterdam", "Europe/Amsterdam"),
    "FRA": ("Frankfurt", "Europe/Berlin"),
    "MUC": ("München", "Europe/Berlin"),
    "ZRH": ("Zürich", "Europe/Zurich"),
    "BRU": ("Bruselj", "Europe/Brussels"),
    "LHR": ("London Heathrow", "Europe/London"),
    "LGW": ("London Gatwick", "Europe/London"),
    "IST": ("Istanbul", "Europe/Istanbul"),
    "SAW": ("Istanbul Sabiha Gökçen", "Europe/Istanbul"),
    "ATH": ("Atene", "Europe/Athens"),
    "MAD": ("Madrid", "Europe/Madrid"),
    "BCN": ("Barcelona", "Europe/Madrid"),
    "LIS": ("Lizbona", "Europe/Lisbon"),
    "JFK": ("New York JFK", "America/New_York"),
    "EWR": ("Newark", "America/New_York"),
    "ORD": ("Chicago", "America/Chicago"),
    "LAX": ("Los Angeles", "America/Los_Angeles"),
    "DXB": ("Dubaj", "Asia/Dubai"),
    "DOH": ("Doha", "Asia/Qatar"),
    "AUH": ("Abu Dabi", "Asia/Dubai"),
    "SIN": ("Singapur", "Asia/Singapore"),
    "HKG": ("Hongkong", "Asia/Hong_Kong"),
    "HND": ("Tokio Haneda", "Asia/Tokyo"),
    "NRT": ("Tokio Narita", "Asia/Tokyo"),
    "PEK": ("Peking", "Asia/Shanghai"),
    "PVG": ("Šanghaj Pudong", "Asia/Shanghai"),
    "BKK": ("Bangkok", "Asia/Bangkok"),
    "DEL": ("Delhi", "Asia/Kolkata"),
    "BOM": ("Mumbai", "Asia/Kolkata"),
    "SYD": ("Sydney", "Australia/Sydney"),
    "MEL": ("Melbourne", "Australia/Melbourne"),
    "YYZ": ("Toronto", "America/Toronto"),
    "YUL": ("Montreal", "America/Toronto"),
    "GRU": ("São Paulo", "America/Sao_Paulo"),
    "CPT": ("Cape Town", "Africa/Johannesburg"),
    "JNB": ("Johannesburg", "Africa/Johannesburg"),
    "MEX": ("Mexico City", "America/Mexico_City"),
    "GDL": ("Guadalajara", "America/Mexico_City"),
    "ATL": ("Atlanta", "America/New_York"),
    "DPS": ("Bali Denpasar", "Asia/Makassar"),
    "EZE": ("Buenos Aires Ezeiza", "America/Argentina/Buenos_Aires"),
    "GGZ": ("Železniška postaja Gradec", "Europe/Vienna"),
    "ZWS": ("Železniška postaja Stuttgart", "Europe/Vienna"),
    "FRATN": ("Železniška postaja Frankfurt letališče", "Europe/Vienna"),
}

# Imena letalskih družb po IATA kodah.
AIRLINES = {
    "A3": "Aegean Airlines",
    "AA": "American Airlines",
    "AC": "Air Canada",
    "AF": "Air France",
    "AI": "Air India",
    "AY": "Finnair",
    "AZ": "ITA Airways",
    "BA": "British Airways",
    "BR": "EVA Air",
    "CA": "Air China",
    "CI": "China Airlines",
    "CX": "Cathay Pacific",
    "CZ": "China Southern Airlines",
    "DL": "Delta Air Lines",
    "EK": "Emirates",
    "ET": "Ethiopian Airlines",
    "EY": "Etihad Airways",
    "FI": "Icelandair",
    "FR": "Ryanair",
    "IB": "Iberia",
    "JL": "Japan Airlines",
    "JU": "Air Serbia",
    "KE": "Korean Air",
    "KL": "KLM",
    "KQ": "Kenya Airways",
    "LA": "LATAM Airlines",
    "LH": "Lufthansa",
    "LO": "LOT Polish Airlines",
    "LX": "SWISS",
    "LY": "EL AL",
    "ME": "Middle East Airlines",
    "MH": "Malaysia Airlines",
    "MS": "EgyptAir",
    "NH": "ANA",
    "NZ": "Air New Zealand",
    "OS": "Austrian Airlines",
    "OU": "Croatia Airlines",
    "OZ": "Asiana Airlines",
    "PC": "Pegasus Airlines",
    "QF": "Qantas",
    "QR": "Qatar Airways",
    "RJ": "Royal Jordanian",
    "RO": "TAROM",
    "SA": "South African Airways",
    "SK": "SAS",
    "SN": "Brussels Airlines",
    "SQ": "Singapore Airlines",
    "SU": "Aeroflot",
    "TG": "Thai Airways",
    "TK": "Turkish Airlines",
    "TP": "TAP Air Portugal",
    "UA": "United Airlines",
    "U2": "easyJet",
    "UX": "Air Europa",
    "VN": "Vietnam Airlines",
    "VS": "Virgin Atlantic",
    "VY": "Vueling",
    "W6": "Wizz Air",
    "WY": "Oman Air",
    "ZH": "Shenzhen Airlines",
    "ZL": "Regional Express",
}

@st.cache_data(ttl=86400, show_spinner=False)
def load_airline_database():
    """Naloži brezplačen seznam letalskih družb; ob napaki uporabi lokalni seznam."""
    airlines = dict(AIRLINES)
    url = "https://raw.githubusercontent.com/gh2137/iata-codes/main/clean/airlines.csv"
    try:
        with urlopen(url, timeout=4) as response:
            content = response.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content), delimiter=";")
        for row in reader:
            code = (row.get("iata_code") or "").strip().upper()
            name = (row.get("airline_name") or "").strip()
            if code and name:
                airlines[code] = name
    except Exception:
        pass
    return airlines

AIRLINE_DATABASE = load_airline_database()

try:
    AIRPORT_DATABASE = airportsdata.load("IATA")
except Exception:
    AIRPORT_DATABASE = {}


def airport_info(code):
    code = (code or "").strip().upper()
    airport = AIRPORT_DATABASE.get(code, {})
    local_name, fallback_timezone = AIRPORTS.get(code, ("", "UTC"))

    city = local_name or airport.get("city") or airport.get("name") or code
    timezone_name = airport.get("tz") or fallback_timezone or "UTC"

    try:
        ZoneInfo(timezone_name)
    except Exception:
        timezone_name = "UTC"

    return city, timezone_name


def airline_name(flight):
    """Vrne polno ime prevoznika na podlagi kode na začetku številke leta."""
    code = flight[:2].upper()
    return AIRLINE_DATABASE.get(code, AIRLINES.get(code, code))


def parse_date(token, year):
    match = re.fullmatch(
        r"(\d{1,2})([A-Z]{3})",
        (token or "").upper().strip(),
    )

    if not match:
        return None

    months = {
        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4,
        "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8,
        "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    }

    month = months.get(match.group(2))

    if not month:
        return None

    try:
        return date(year, month, int(match.group(1)))
    except ValueError:
        return None


def format_duration(minutes):
    if minutes is None or minutes < 0:
        return "—"

    hours, mins = divmod(minutes, 60)

    if hours and mins:
        return f"{hours} h {mins} min"
    if hours:
        return f"{hours} h"

    return f"{mins} min"


def time_difference_minutes(
    start_date,
    start_time,
    start_tz,
    end_date,
    end_time,
    end_tz,
):
    try:
        start_dt = datetime.strptime(
            f"{start_date.isoformat()} {start_time}",
            "%Y-%m-%d %H%M",
        ).replace(tzinfo=ZoneInfo(start_tz))

        end_dt = datetime.strptime(
            f"{end_date.isoformat()} {end_time}",
            "%Y-%m-%d %H%M",
        ).replace(tzinfo=ZoneInfo(end_tz))

        return int((end_dt - start_dt).total_seconds() // 60)
    except Exception:
        return None


# ---------------------------------------------------------
# PARSANJE AMADEUSOVIH ZAPISOV
# ---------------------------------------------------------

def parse_amadeus_line(line):
    """
    Podpira klasične zapise in zapise z ločenimi kodami letališč,
    terminali in oznakami operativnega prevoznika.

    Primeri:
    1  OS3580 S 08NOV 7 GGZVIE HK1 0600 0857 TRN E 1
    1  *OS3580 S 08NOV GGZ VIE 3 0600 0857 E1/TRN
    1   IB 684 M 04DEC VCE MAD 4 0620 0900 E0/320
    2VY IB5380 Z 09DEC BCN 1 VCE 0720 0910 E0/321
    """
    line = line.strip()

    if not line:
        return None

    # Oznaka TRN je lahko na koncu vrstice (npr. E1/TRN).
    is_train = bool(re.search(r"\bTRN\b", line, re.IGNORECASE))

    # Odstranimo začetno številko segmenta, ne pa kode leta.
    line = re.sub(r"^\d+\s*", "", line)

    # Odstranimo začetno zvezdico, ki se pojavlja v nekaterih izpisih.
    line = re.sub(r"^\*\s*", "", line)

    # Pri obliki "VY IB5380 ..." je IB5380 dejanska številka leta.
    # Začetna koda operativnega prevoznika ni del številke leta.
    line = re.sub(
        r"^[A-Z0-9]{2}\s+(?=[A-Z]{2}\s*\d)",
        "",
        line,
        flags=re.IGNORECASE,
    )

    date_match = re.search(
        r"\b(?P<date>\d{1,2}[A-Z]{3})\b",
        line,
        re.IGNORECASE,
    )

    if not date_match:
        return None

    date_token = date_match.group("date").upper()
    prefix = line[:date_match.start()].strip()
    remainder = line[date_match.end():].strip()

    # Letalska številka in razred rezervacije pred datumom.
    flight_matches = list(
        re.finditer(
            r"(?P<flight>[A-Z0-9]{2}\s*[A-Z0-9]{1,4})\s+"
            r"(?P<class>[A-Z])(?=\s|$)",
            prefix,
            re.IGNORECASE,
        )
    )

    if not flight_matches:
        return None

    flight = re.sub(
        r"\s+",
        "",
        flight_matches[-1].group("flight"),
    ).upper()

    # Čase iščemo za datumom, da številk terminalov ne zamenjamo za čase.
    times = list(
        re.finditer(r"(?<!\d)(\d{4})(?!\d)", remainder)
    )

    if len(times) < 2:
        return None

    route_text = remainder[:times[0].start()].strip()

    # Najprej poiščemo samostojne kode letališč.
    airport_codes = re.findall(
        r"(?<![A-Z])([A-Z]{3})(?![A-Z])",
        route_text,
        re.IGNORECASE,
    )

    if len(airport_codes) >= 2:
        origin = airport_codes[0].upper()
        destination = airport_codes[1].upper()
    else:
        # Klasični zapis brez presledkov, npr. LJUAMS.
        joined_route = re.search(
            r"\b([A-Z]{6})\b",
            route_text,
            re.IGNORECASE,
        )

        if not joined_route:
            return None

        route = joined_route.group(1).upper()
        origin, destination = route[:3], route[3:]

    return {
        "flight": flight,
        "date_token": date_token,
        "origin": origin,
        "destination": destination,
        "departure_time": times[0].group(1),
        "arrival_time": times[1].group(1),
        "is_train": is_train,
    }


def parse_segments(raw):
    raw_lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip()
    ]

    matched_lines = []

    for line in raw_lines:
        item = parse_amadeus_line(line)
        if item:
            matched_lines.append(item)

    if not matched_lines:
        return []

    today = date.today()
    current_year = today.year

    first_date = parse_date(
        matched_lines[0]["date_token"],
        current_year,
    )

    base_year = (
        current_year + 1
        if first_date and first_date < today
        else current_year
    )

    previous_date = None
    parsed = []

    for item in matched_lines:
        flight_date = parse_date(
            item["date_token"],
            base_year,
        )

        if not flight_date:
            continue

        if previous_date and flight_date < previous_date:
            base_year += 1
            flight_date = parse_date(
                item["date_token"],
                base_year,
            )

        if not flight_date:
            continue

        previous_date = flight_date

        origin = item["origin"]
        destination = item["destination"]

        origin_city, origin_tz = airport_info(origin)
        destination_city, destination_tz = airport_info(destination)

        departure_time = item["departure_time"]
        arrival_time = item["arrival_time"]

        arrival_date = flight_date

        duration = time_difference_minutes(
            flight_date,
            departure_time,
            origin_tz,
            arrival_date,
            arrival_time,
            destination_tz,
        )

        # Če prihod po izračunu nastopi pred odhodom, preverimo naslednji dan.
        if duration is not None and duration < 0:
            next_day = flight_date + timedelta(days=1)

            next_duration = time_difference_minutes(
                flight_date,
                departure_time,
                origin_tz,
                next_day,
                arrival_time,
                destination_tz,
            )

            if next_duration is not None and next_duration >= 0:
                arrival_date = next_day
                duration = next_duration

        parsed.append({
            "date": flight_date,
            "flight": item["flight"],
            "airline_name": airline_name(item["flight"]),
            "is_train": item.get("is_train", False),
            "origin": origin,
            "destination": destination,
            "origin_city": origin_city,
            "destination_city": destination_city,
            "departure": departure_time[:2] + ":" + departure_time[2:],
            "arrival": arrival_time[:2] + ":" + arrival_time[2:],
            "duration_minutes": duration,
            "arrival_date": arrival_date,
        })

    # Izračun prestopov med zaporednimi leti.
    for i, segment in enumerate(parsed):
        segment["layover_minutes"] = None

        if i >= len(parsed) - 1:
            continue

        next_segment = parsed[i + 1]

        if segment["destination"] != next_segment["origin"]:
            continue

        _, timezone_name = airport_info(segment["destination"])

        try:
            arrival_dt = datetime.strptime(
                f"{segment['arrival_date'].isoformat()} "
                f"{segment['arrival']}",
                "%Y-%m-%d %H:%M",
            ).replace(tzinfo=ZoneInfo(timezone_name))

            next_departure_dt = datetime.strptime(
                f"{next_segment['date'].isoformat()} "
                f"{next_segment['departure']}",
                "%Y-%m-%d %H:%M",
            ).replace(tzinfo=ZoneInfo(timezone_name))

            layover = int(
                (next_departure_dt - arrival_dt).total_seconds() // 60
            )

            if 0 <= layover <= 18 * 60:
                segment["layover_minutes"] = layover

        except Exception:
            segment["layover_minutes"] = None

    # Odebeljena ločilna črta je samo med sklopi, ne pod zadnjo vrstico.
    # Sklop se nadaljuje samo, če naslednji let odleti z istega letališča
    # in ima veljaven prestop (0–18 ur). Sama enaka koda letališča ni dovolj:
    # večdnevni presledek, kot TLV 15. decembra -> TLV 18. decembra,
    # pomeni nov sklop.
    for i, segment in enumerate(parsed):
        segment["end_of_connection"] = (
            i < len(parsed) - 1
            and segment["layover_minutes"] is None
        )

    return parsed


# ---------------------------------------------------------
# PRIKAZ BESEDILA IN TABELE
# ---------------------------------------------------------

def format_text(segments):
    lines = []

    for segment in segments:
        date_text = segment["date"].strftime("%d.%m.%Y")

        route = (
            f"{segment['origin_city']} ({segment['origin']}) – "
            f"{segment['destination_city']} ({segment['destination']})"
        )

        duration = format_duration(segment["duration_minutes"])

        train_label = " (vlak)" if segment.get("is_train") else ""

        lines.append(
            f"{date_text} | {segment['airline_name']} "
            f"{segment['flight']}{train_label} | {route} | "
            f"{segment['departure']}–{segment['arrival']} | {duration}"
        )

    return "\n".join(lines)


def display_table(segments):
    rows = []

    for segment in segments:
        rows.append({
            "Datum": segment["date"].strftime("%d.%m.%Y"),
            "Let": (
                f"{segment['airline_name']} {segment['flight']}"
                + (" (vlak)" if segment.get("is_train") else "")
            ),
            "Relacija": (
                f"{segment['origin_city']} ({segment['origin']}) – "
                f"{segment['destination_city']} ({segment['destination']})"
            ),
            "Odhod": segment["departure"],
            "Prihod": segment["arrival"],
            "Trajanje leta": format_duration(segment["duration_minutes"]),
            "Čas prestopa": format_duration(segment["layover_minutes"]),
            "_konec_povezave": segment["end_of_connection"],
        })

    return rows


# ---------------------------------------------------------
# HTML TABELA – MODRO-ZLATA RAZLIČICA + ROBOTO
# ---------------------------------------------------------

def render_copyable_table(rows):
    if not rows:
        return

    headers = [
        key for key in rows[0]
        if not key.startswith("_")
    ]

    table_style = (
        "border-collapse:collapse;"
        "width:auto;"
        "max-width:100%;"
        "font-family:Roboto,Arial,Helvetica,sans-serif;"
        "font-size:13px;"
        "font-weight:400;"
        "color:#263445;"
    )

    th_style = (
        "background-color:#004899;"
        "color:#FFFFFF;"
        "font-family:Roboto,Arial,Helvetica,sans-serif;"
        "font-size:13px;"
        "font-weight:700;"
        "text-align:left;"
        "padding:9px 10px;"
        "border:1px solid #FBB900;"
        "border-bottom:4px solid #FBB900;"
        "white-space:nowrap;"
    )

    td_base = (
        "padding:8px 10px;"
        "border:1px solid #FBB900;"
        "vertical-align:top;"
        "font-family:Roboto,Arial,Helvetica,sans-serif;"
        "font-size:13px;"
        "font-weight:400;"
    )

    nowrap_columns = {
        "Datum",
        "Let",
        "Odhod",
        "Prihod",
        "Trajanje leta",
        "Čas prestopa",
    }

    html_rows = [
        f'<table style="{table_style}"><thead><tr>'
    ]

    for header in headers:
        html_rows.append(
            f'<th style="{th_style}">{html.escape(header)}</th>'
        )

    html_rows.append("</tr></thead><tbody>")

    for row_index, row in enumerate(rows):
        background = (
            "#FFF9E8"
            if row_index % 2
            else "#FFFFFF"
        )

        html_rows.append("<tr>")

        for header in headers:
            value = html.escape(str(row.get(header, "")))

            cell_style = (
                td_base
                + f"background-color:{background};"
            )

            if header in nowrap_columns:
                cell_style += "white-space:nowrap;"
            else:
                cell_style += (
                    "white-space:normal;"
                    "overflow-wrap:anywhere;"
                    "max-width:280px;"
                )

            # Na koncu nepovezanega sklopa je spodnja črta le malenkost debelejša.
            if row.get("_konec_povezave", False):
                cell_style += "border-bottom:2px solid #FBB900;"

            html_rows.append(
                f'<td style="{cell_style}">{value}</td>'
            )

        html_rows.append("</tr>")

    html_rows.append("</tbody></table>")
    table_html = "".join(html_rows)

    # Kopiranje v HTML ali navadno besedilo.
    tsv_lines = ["\t".join(headers)]

    for row in rows:
        tsv_lines.append(
            "\t".join(str(row.get(header, "")) for header in headers)
        )

    tsv_text = "\n".join(tsv_lines)

    safe_html = json.dumps(table_html, ensure_ascii=False)
    safe_tsv = json.dumps(tsv_text, ensure_ascii=False)

    components.html(
        f"""
        <div style="font-family:Roboto,Arial,Helvetica,sans-serif;">
          <style>
            @import url(
              'https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap'
            );
          </style>

          <button id="copyTable" style="
            background:#004899;
            color:#FBB900;
            border:2px solid #FBB900;
            border-radius:5px;
            padding:8px 13px;
            font-family:Roboto,Arial,Helvetica,sans-serif;
            font-size:13px;
            font-weight:700;
            cursor:pointer;
            margin:0 0 10px 0;
          ">📋 Kopiraj tabelo</button>

          <span id="copyStatus" style="
            font-family:Roboto,Arial,Helvetica,sans-serif;
            font-size:12px;
            color:#526579;
            margin-left:8px;
          "></span>

          <div style="overflow-x:auto;">
            {table_html}
          </div>
        </div>

        <script>
          const htmlTable = {safe_html};
          const plainText = {safe_tsv};

          document.getElementById("copyTable").addEventListener(
            "click",
            async () => {{
              const status = document.getElementById("copyStatus");

              try {{
                if (navigator.clipboard && window.ClipboardItem) {{
                  const item = new ClipboardItem({{
                    "text/html": new Blob(
                      [htmlTable],
                      {{type: "text/html"}}
                    ),
                    "text/plain": new Blob(
                      [plainText],
                      {{type: "text/plain"}}
                    )
                  }});

                  await navigator.clipboard.write([item]);
                  status.textContent = "Tabela je kopirana.";

                }} else if (
                  navigator.clipboard &&
                  navigator.clipboard.writeText
                ) {{
                  await navigator.clipboard.writeText(plainText);
                  status.textContent = "Kopirano kot besedilo.";

                }} else {{
                  status.textContent =
                    "Kopiranje ni podprto. Označi tabelo in jo kopiraj.";
                }}

              }} catch (err) {{
                status.textContent =
                  "Kopiranje ni uspelo. Poskusi ponovno ali kopiraj tabelo ročno.";
              }}
            }}
          );
        </script>
        """,
        height=max(190, 65 + 39 * len(rows)),
        scrolling=True,
    )


# ---------------------------------------------------------
# UPORABNIŠKI VMESNIK
# ---------------------------------------------------------

raw_input = st.text_area(
    "Prilepi Amadeus segmente",
    height=220,
    placeholder=(
        "Primer:\n"
        "2 KL1988 L 24SEP 4 LJUAMS HK1 0600 0755 *1A/E*\n"
        "3 KL 611 N 24SEP 4 AMSORD HK1 5 1245 1415 *1A/E*"
    ),
)

if st.button("Ustvari potovalni načrt", type="primary"):
    segments = parse_segments(raw_input)

    if segments:
        st.session_state["segments"] = segments
        st.session_state["raw_input"] = raw_input
        st.session_state.pop("parse_error", None)
    else:
        st.session_state.pop("segments", None)
        st.session_state["parse_error"] = (
            "Segmentov nisem prepoznala. Preveri, ali si prilepila "
            "vrstice z datumi, letalskimi številkami, relacijami in časi."
        )

if st.session_state.get("parse_error"):
    st.error(st.session_state["parse_error"])

if st.session_state.get("segments"):
    segments = st.session_state["segments"]
    rows = display_table(segments)

    st.subheader("Besedilni pregled")

    text_output = format_text(segments)

    st.code(text_output, language=None)

    st.download_button(
        label="⬇️ Prenesi besedilo (.txt)",
        data=text_output,
        file_name="potovalni_nacrt.txt",
        mime="text/plain",
    )

    st.subheader("Tabela za Loop ali e-pošto")

    st.caption(
        "Klikni »Kopiraj tabelo« in jo prilepi v Loop. "
        "Spodnja črta glave je debelejša; malenkost debelejša rumena črta "
        "med vrsticami označuje začetek novega sklopa letov. "
        "Če se oblikovanje ne prenese, je to lahko omejitev "
        "brskalnika ali ciljnega programa."
    )

    render_copyable_table(rows)
