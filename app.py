
import re
import html
import json
import csv
from io import StringIO
from urllib.request import urlopen
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st
import airportsdata
import streamlit.components.v1 as components


# =========================================================
# NASTAVITVE APLIKACIJE
# =========================================================

st.set_page_config(
    page_title="Amadeus – potovalni načrt",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ Amadeus – potovalni načrt")
st.caption(
    "Prilepi letalske ali železniške segmente iz Amadeusa "
    "in ustvari pregleden potovalni načrt za stranko."
)


# =========================================================
# BARVE
# =========================================================

BLUE = "#004899"
GOLD = "#FBB900"
PALE_YELLOW = "#FFF9E8"
WHITE = "#FFFFFF"
TEXT_COLOR = "#263445"
BORDER_COLOR = "#D5DEE7"


# =========================================================
# LASTNI PREVODI LETALIŠČ IN ČASOVNI PASOVI
# Ti prevodi imajo prednost pred podatki iz baze.
# =========================================================

AIRPORTS = {
    "LJU": ("Ljubljana", "Europe/Ljubljana"),
    "ZAG": ("Zagreb", "Europe/Zagreb"),
    "VIE": ("Dunaj", "Europe/Vienna"),
    "GGZ": ("Gradec železniška postaja", "Europe/Vienna"),
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
}


# =========================================================
# BAZA LETALIŠČ
# =========================================================

@st.cache_data(show_spinner=False)
def load_airport_database():
    try:
        return airportsdata.load("IATA")
    except Exception:
        return {}


AIRPORT_DATABASE = load_airport_database()


def airport_info(code):
    code = (code or "").strip().upper()

    airport = AIRPORT_DATABASE.get(code, {})
    local_name, fallback_timezone = AIRPORTS.get(
        code, ("", "UTC")
    )

    city = (
        local_name
        or airport.get("city")
        or airport.get("name")
        or code
    )

    timezone_name = (
        fallback_timezone
        or airport.get("tz")
        or "UTC"
    )

    try:
        ZoneInfo(timezone_name)
    except Exception:
        timezone_name = "UTC"

    return city, timezone_name


# =========================================================
# BREZPLAČNA BAZA LETALSKIH DRUŽB
# Vir: github.com/gh2137/iata-codes
# Baza se predpomni za 24 ur.
# =========================================================

@st.cache_data(ttl=86400, show_spinner=False)
def load_airline_database():
    url = (
        "https://raw.githubusercontent.com/"
        "gh2137/iata-codes/main/clean/airlines.csv"
    )

    try:
        with urlopen(url, timeout=8) as response:
            content = response.read().decode("utf-8-sig")

        reader = csv.DictReader(
            StringIO(content),
            delimiter=";",
        )

        airlines = {}

        for row in reader:
            code = (row.get("iata_code") or "").strip().upper()
            name = (row.get("airline_name") or "").strip()

            if code and name:
                airlines[code] = name

        return airlines

    except Exception:
        return {}


AIRLINE_DATABASE = load_airline_database()


def airline_name(code):
    code = (code or "").strip().upper()
    return AIRLINE_DATABASE.get(code, "")


# =========================================================
# DATUMI, ČASI IN TRAJANJE
# =========================================================

def parse_date(token, year):
    match = re.fullmatch(
        r"(\d{1,2})([A-Z]{3})",
        (token or "").upper().strip(),
    )

    if not match:
        return None

    day = int(match.group(1))
    month_text = match.group(2)

    months = {
        "JAN": 1,
        "FEB": 2,
        "MAR": 3,
        "APR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "AUG": 8,
        "SEP": 9,
        "OCT": 10,
        "NOV": 11,
        "DEC": 12,
    }

    month = months.get(month_text)

    if not month:
        return None

    try:
        return date(year, month, day)
    except ValueError:
        return None


def format_duration(minutes):
    if minutes is None or minutes < 0:
        return "—"

    hours, mins = divmod(int(minutes), 60)

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

        return int(
            (end_dt - start_dt).total_seconds() // 60
        )

    except Exception:
        return None


# =========================================================
# RAZČLENJEVANJE AMADEUSOVIH SEGMENTOV
#
# Podprti primeri:
#
# 1  OS3580 S 08NOV 7 GGZVIE HK1 0600 0857 TRN E 1
# 2  KL1988 L 24SEP 4 LJUAMS HK1 0600 0755 *1A/E*
# 3  KL 611 N 24SEP 4 AMSORD HK1 5 1245 1415 *1A/E*
# 1  IB 684 M 04DEC VCE MAD 4 0620 0900 E0/320
# 2VY IB5380 Z 09DEC BCN 1 VCE 0720 0910 E0/321
# EN*OS 353 S 08NOV VIE 3 LYS 1 1015 1205 E0/E95
# =========================================================

def normalize_amadeus_line(line):
    line = re.sub(r"\s+", " ", line.strip())

    # Odstrani začetno številko segmenta.
    # Primer: "1 OS3580 ..." -> "OS3580 ..."
    # Primer: "2VY IB5380 ..." -> "VY IB5380 ..."
    line = re.sub(r"^\d+\s*", "", line)

    # Odstrani predpone, kot je EN*.
    line = re.sub(r"^[A-Z]{1,3}\*", "", line)

    # Odstrani operativnega prevoznika, če je zapisan
    # pred dejanskim prevoznikom in številko leta.
    # Primer: "VY IB5380 Z 09DEC ..." -> "IB5380 Z 09DEC ..."
    line = re.sub(
        r"^[A-Z0-9]{2}\s+(?=[A-Z0-9]{2}\d+\s+[A-Z]\s+\d{1,2}[A-Z]{3})",
        "",
        line,
    )

    return line


def extract_route(text):
    """
    Iz besedila po datumu prepozna odhodno in prihodno kodo.
    Podpira GGZVIE, LJU AMS in VIE 3 LYS 1.
    """

    # Poiščemo kompaktno zapisani kodi, npr. GGZVIE.
    compact = re.search(
        r"(?<![A-Z])([A-Z]{3})([A-Z]{3})(?![A-Z])",
        text,
    )

    if compact:
        return compact.group(1), compact.group(2)

    # Pri ločenih kodah upoštevamo samo del pred statusom
    # rezervacije ali pred prvim časom.
    before_status = re.split(
        r"\b(?:HK|HL|HN|KK|TK|UC|UN|NO|RQ|SS|NN)\d?\b",
        text,
        maxsplit=1,
    )[0]

    before_time = re.split(
        r"(?<!\d)\d{4}(?!\d)",
        before_status,
        maxsplit=1,
    )[0]

    codes = re.findall(
        r"(?<![A-Z])([A-Z]{3})(?![A-Z])",
        before_time,
    )

    if len(codes) >= 2:
        return codes[0], codes[1]

    return None, None


def parse_amadeus_line(original_line):
    line = normalize_amadeus_line(original_line)

    # Prevoznik in številka sta lahko zapisana skupaj ali ločeno:
    # OS3580 oziroma OS 3580.
    flight_match = re.search(
        r"(?P<airline>[A-Z0-9]{2})\s*"
        r"(?P<number>\d{1,4}[A-Z]?)\s+"
        r"(?P<class>[A-Z])\s+"
        r"(?P<date>\d{1,2}[A-Z]{3})\b",
        line,
        re.IGNORECASE,
    )

    if not flight_match:
        return None

    date_token = flight_match.group("date").upper()
    after_date = line[flight_match.end():]

    origin, destination = extract_route(after_date)

    if not origin or not destination:
        return None

    # Čase iščemo za datumom. Tako številke terminalov
    # ali številka leta ne morejo postati čas odhoda.
    times = re.findall(
        r"(?<!\d)(\d{4})(?!\d)",
        after_date,
    )

    if len(times) < 2:
        return None

    departure_time = times[0]
    arrival_time = times[1]

    if not (
        0 <= int(departure_time[:2]) <= 23
        and 0 <= int(departure_time[2:]) <= 59
        and 0 <= int(arrival_time[:2]) <= 23
        and 0 <= int(arrival_time[2:]) <= 59
    ):
        return None

    is_train = bool(
        re.search(r"\bTRN\b", line, re.IGNORECASE)
    )

    airline_code = flight_match.group("airline").upper()
    flight_number = (
        airline_code + flight_match.group("number").upper()
    )

    return {
        "airline_code": airline_code,
        "flight": flight_number,
        "date_token": date_token,
        "origin": origin.upper(),
        "destination": destination.upper(),
        "departure_time": departure_time,
        "arrival_time": arrival_time,
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

    if first_date and first_date < today:
        base_year = current_year + 1
    else:
        base_year = current_year

    parsed = []
    previous_date = None

    for item in matched_lines:
        flight_date = parse_date(
            item["date_token"],
            base_year,
        )

        if not flight_date:
            continue

        # Prehod čez novo leto.
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
        destination_city, destination_tz = airport_info(
            destination
        )

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

        # Če je prihod po lokalnem času naslednji dan,
        # preverimo še naslednji datum.
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
            "airline_code": item["airline_code"],
            "airline_name": airline_name(item["airline_code"]),
            "origin": origin,
            "destination": destination,
            "origin_city": origin_city,
            "destination_city": destination_city,
            "departure": (
                departure_time[:2] + ":" + departure_time[2:]
            ),
            "arrival": (
                arrival_time[:2] + ":" + arrival_time[2:]
            ),
            "duration_minutes": duration,
            "arrival_date": arrival_date,
            "is_train": item["is_train"],
            "layover_minutes": None,
            "connected_to_next": False,
        })

    # Izračun prestopov med zaporednimi segmenti.
    for index, segment in enumerate(parsed[:-1]):
        next_segment = parsed[index + 1]

        if segment["destination"] != next_segment["origin"]:
            continue

        _, timezone_name = airport_info(
            segment["destination"]
        )

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

            layover_minutes = int(
                (
                    next_departure_dt - arrival_dt
                ).total_seconds() // 60
            )

            # Prikazujemo običajne prestope do 18 ur.
            if 0 <= layover_minutes <= 18 * 60:
                segment["layover_minutes"] = layover_minutes
                segment["connected_to_next"] = True

        except Exception:
            segment["layover_minutes"] = None
            segment["connected_to_next"] = False

    return parsed

# =========================================================
# PODATKI ZA TABEL
# =========================================================

def display_table(segments):
    rows = []

    for segment in segments:
        flight_label = segment["flight"]

        if segment["airline_name"]:
            flight_label += "\n" + segment["airline_name"]

        if segment["is_train"]:
            flight_label += "\nvlak"

        rows.append({
            "Datum": segment["date"].strftime("%d.%m.%Y"),
            "Let": flight_label,
            "Relacija": (
                f"{segment['origin_city']} ({segment['origin']}) – "
                f"{segment['destination_city']} "
                f"({segment['destination']})"
            ),
            "Odhod": segment["departure"],
            "Prihod": segment["arrival"],
            "Trajanje leta": format_duration(
                segment["duration_minutes"]
            ),
            "Čas prestopa": format_duration(
                segment["layover_minutes"]
            ),
            "_connected_to_next": segment["connected_to_next"],
            "_flight": segment["flight"],
            "_airline_name": segment["airline_name"],
            "_is_train": segment["is_train"],
        })

    return rows


# =========================================================
# HTML TABELA ZA KOPIRANJE
# =========================================================

def render_copyable_table(rows):
    if not rows:
        return

    headers = [
        "Datum",
        "Let",
        "Relacija",
        "Odhod",
        "Prihod",
        "Trajanje leta",
        "Čas prestopa",
    ]

    table_style = (
        "border-collapse:collapse;"
        "width:auto;"
        "max-width:100%;"
        "font-family:Roboto,Arial,Helvetica,sans-serif;"
        "font-size:13px;"
        f"color:{TEXT_COLOR};"
    )

    th_style = (
        f"background-color:{BLUE};"
        "color:#FFFFFF;"
        "font-weight:700;"
        "text-align:left;"
        "padding:8px 9px;"
        f"border:1px solid {BORDER_COLOR};"
        f"border-bottom:4px solid {GOLD};"
        "white-space:nowrap;"
    )

    td_base = (
        "padding:7px 9px;"
        f"border:1px solid {BORDER_COLOR};"
        "vertical-align:top;"
        "font-family:Roboto,Arial,Helvetica,sans-serif;"
    )

    nowrap_columns = {
        "Datum",
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
            PALE_YELLOW if row_index % 2 else WHITE
        )

        # Rumena črta samo ob koncu sklopa povezanih letov,
        # če naslednji let ni povezava na trenutno destinacijo.
        connected_border = (
            f""
            if row.get("_connected_to_next")
            else "border-bottom:1.5 px solid {GOLD};"
        )

        html_rows.append("<tr>")

        for header in headers:
            cell_style = (
                td_base
                + f"background-color:{background};"
                + connected_border
            )

            if header in nowrap_columns:
                cell_style += "white-space:nowrap;"
            else:
                cell_style += (
                    "white-space:normal;"
                    "overflow-wrap:anywhere;"
                    "max-width:280px;"
                )

            if header == "Let":
                flight = html.escape(row["_flight"])
                airline = html.escape(row["_airline_name"])

                flight_html = (
                    f'<div style="font-weight:700;">{flight}</div>'
                )

                if airline:
                    flight_html += (
                        '<div style="font-size:11px;'
                        'color:#526579;margin-top:2px;">'
                        f'{airline}</div>'
                    )

                if row["_is_train"]:
                    flight_html += (
                        '<div style="font-size:11px;'
                        'color:#526579;margin-top:2px;">'
                        'vlak</div>'
                    )

                cell_value = flight_html

            else:
                cell_value = html.escape(str(row.get(header, "")))

            html_rows.append(
                f'<td style="{cell_style}">{cell_value}</td>'
            )

        html_rows.append("</tr>")

    html_rows.append("</tbody></table>")

    table_html = "".join(html_rows)

    # Besedilna različica kot rezervna možnost kopiranja.
    tsv_lines = ["\t".join(headers)]

    for row in rows:
        tsv_row = []

        for header in headers:
            if header == "Let":
                value = row["_flight"]

                if row["_airline_name"]:
                    value += " – " + row["_airline_name"]

                if row["_is_train"]:
                    value += " (vlak)"

            else:
                value = str(row.get(header, ""))

            tsv_row.append(value)

        tsv_lines.append("\t".join(tsv_row))

    tsv_text = "\n".join(tsv_lines)

    safe_html = json.dumps(table_html, ensure_ascii=False)
    safe_tsv = json.dumps(tsv_text, ensure_ascii=False)

    components.html(
        f"""
        <div style="font-family:Roboto,Arial,Helvetica,sans-serif;">
          <button id="copyTable"
            style="
              background:{BLUE};
              color:{GOLD};
              border:1px solid {GOLD};
              border-radius:5px;
              padding:8px 13px;
              font-size:13px;
              font-weight:600;
              cursor:pointer;
              margin:0 0 10px 0;
            ">
            📋 Kopiraj tabelo
          </button>

          <span id="copyStatus"
            style="font-size:12px;color:#526579;margin-left:8px;">
          </span>

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
        height=max(220, 75 + 58 * len(rows)),
        scrolling=True,
    )


# =========================================================
# UPORABNIŠKI VMESNIK
# =========================================================

raw_input = st.text_area(
    "Prilepi Amadeus segmente",
    height=220,
    placeholder=(
        "Primer:\n"
        "1  IB 684 M 04DEC VCE MAD 4 0620 0900 E0/320\n"
        "   IB 411 M 04DEC MAD 4 BCN 1 1125 1245 E0/320\n"
        "2VY IB5380 Z 09DEC BCN 1 VCE 0720 0910 E0/321"
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
            "vrstice z datumi, številkami letov, relacijami in časi."
        )

if st.session_state.get("parse_error"):
    st.error(st.session_state["parse_error"])

if st.session_state.get("segments"):
    segments = st.session_state["segments"]
    rows = display_table(segments)

    st.subheader("Tabela za Loop ali e-pošto")
    st.caption(
        "Klikni »Kopiraj tabelo« in jo prilepi v Loop ali e-pošto. "
        "Če se oblikovanje ne prenese, je to lahko omejitev "
        "brskalnika ali ciljnega programa."
    )

    render_copyable_table(rows)

    if not AIRLINE_DATABASE:
        st.caption(
            "Opomba: brezplačna baza letalskih družb trenutno ni "
            "dosegljiva. Številke letov so še vedno prikazane."
        )

