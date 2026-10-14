
import re
import html
import json
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
    "Prilepi segmente iz Amadeusa v katerikoli podprti obliki "
    "in ustvari pregledno tabelo za stranko."
)


# ---------------------------------------------------------
# LETALIŠČA
# ---------------------------------------------------------

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
    "DPS": ("Bali Denpasar", "Asia/Makassar"),
    "EZE": ("Buenos Aires Ezeiza", "America/Argentina/Buenos_Aires"),
}


# ---------------------------------------------------------
# POMOŽNE FUNKCIJE
# ---------------------------------------------------------

try:
    AIRPORT_DATABASE = airportsdata.load("IATA")
except Exception:
    AIRPORT_DATABASE = {}


def airport_info(code):
    code = (code or "").strip().upper()
    airport = AIRPORT_DATABASE.get(code, {})
    local_name, fallback_timezone = AIRPORTS.get(code, ("", "UTC"))

    city = (
        local_name
        or airport.get("city")
        or airport.get("name")
        or code
    )

    timezone_name = airport.get("tz") or fallback_timezone or "UTC"

    try:
        ZoneInfo(timezone_name)
    except Exception:
        timezone_name = "UTC"

    return city, timezone_name


def parse_date(token, year):
    token = token.upper().strip()
    match = re.fullmatch(r"(\d{1,2})([A-Z]{3})", token)

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
    """Trajanje prikaže v obliki 2 h 15 m oziroma 45 m."""
    if minutes is None or minutes < 0:
        return "—"

    hours, mins = divmod(minutes, 60)

    if hours and mins:
        return f"{hours} h {mins} m"
    if hours:
        return f"{hours} h"

    return f"{mins} m"


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
# PREPOZNAVANJE AMADEUS SEGMENTOV
# --------------------------------------------------------

def extract_segment(line):
    """Prebere en Amadeusov segment iz več pogostih zapisov."""
    line = line.strip().upper()

    if not line:
        return None

    # Odstranimo začetno številko segmenta oziroma povezave.
    # Deluje za "1 IB 684" in "2VY IB5380".
    line = re.sub(r"^\s*\d+\s*", "", line)

    # Odstranimo morebitno oznako pred zvezdico, npr. EN*OS 353.
    line = re.sub(
        r"^(?:[A-Z0-9]{1,3})?\*\s*",
        "",
        line,
    )

    # V zapisu "VY IB5380" ignoriramo operativnega prevoznika VY.
    # Ohranimo IB5380 kot številko, ki jo želimo prikazati.
    line = re.sub(
        r"^[A-Z]{2}\s+(?=[A-Z]{2}\s*\d)",
        "",
        line,
    )

    header = re.match(
        r"^(?P<airline>[A-Z0-9]{2})\s*"
        r"(?P<flight>\d{1,4}[A-Z]?)\s+"
        r"(?P<class>[A-Z])\s+"
        r"(?P<date>\d{1,2}[A-Z]{3})\b"
        r"(?P<rest>.*)$",
        line,
    )

    if not header:
        return None

    rest = header.group("rest")

    # Prva dva štirimestna niza sta odhod in prihod.
    times = re.findall(r"(?<!\d)(\d{4})(?!\d)", rest)

    if len(times) < 2:
        return None

    # Relacijo iščemo pred prvim časom.
    before_times = rest.split(times[0], 1)[0]

    # Podprti zapisi:
    # GGZVIE
    # GGZ VIE
    # VIE 3 LYS 1
    # VCE MAD 4
    route_match = re.search(
        r"(?<![A-Z])([A-Z]{6})(?![A-Z])",
        before_times,
    )

    if route_match:
        route = route_match.group(1)
        origin = route[:3]
        destination = route[3:]

    else:
        # Številke terminalov ignoriramo.
        airport_codes = re.findall(
            r"(?<![A-Z])([A-Z]{3})(?![A-Z])",
            before_times,
        )

        if len(airport_codes) < 2:
            return None

        origin = airport_codes[0]
        destination = airport_codes[1]

    return {
        "airline": header.group("airline"),
        "flight_number": header.group("flight"),
        "date_token": header.group("date"),
        "origin": origin,
        "destination": destination,
        "departure_time": times[0],
        "arrival_time": times[1],
        "is_train": bool(
            re.search(r"(?<![A-Z0-9])TRN(?![A-Z0-9])", line)
        ),
    }


def parse_segments(raw):
    """Podpira klasične in novejše oblike izpisa Amadeusa."""
    raw_lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip()
    ]

    matched_lines = []

    for line in raw_lines:
        item = extract_segment(line)

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

    parsed = []
    previous_date = None

    for item in matched_lines:
        flight_date = parse_date(
            item["date_token"],
            base_year,
        )

        if not flight_date:
            continue

        # Če se datum premakne nazaj, predpostavimo novo leto.
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

        # Če je prihod glede na lokalni čas pred odhodom,
        # preverimo, ali let prispe naslednji dan.
        if duration is not None and duration < 0:
            next_day = flight_date + timedelta(days=1)

            next_day_duration = time_difference_minutes(
                flight_date,
                departure_time,
                origin_tz,
                next_day,
                arrival_time,
                destination_tz,
            )

            if next_day_duration is not None and next_day_duration >= 0:
                arrival_date = next_day
                duration = next_day_duration

        parsed.append({
            "date": flight_date,
            "flight": f"{item['airline']}{item['flight_number']}",
            "is_train": item["is_train"],
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
        })

    # Izračun časa prestopa med zaporednimi segmenti.
    for i, segment in enumerate(parsed):
        segment["layover_minutes"] = None

        if i >= len(parsed) - 1:
            continue

        next_segment = parsed[i + 1]

        # Prestop izračunamo samo na istem letališču.
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

            layover_minutes = int(
                (next_departure_dt - arrival_dt).total_seconds() // 60
            )

            if 0 <= layover_minutes <= 18 * 60:
                segment["layover_minutes"] = layover_minutes

        except Exception:
            segment["layover_minutes"] = None

    return parsed

# ---------------------------------------------------------
# BESEDILNI PREGLED IN VRSTICE TABELE
# ---------------------------------------------------------

def format_text(segments):
    lines = []

    for segment in segments:
        date_text = segment["date"].strftime("%d.%m.%Y")

        route = (
            f"{segment['origin_city']} ({segment['origin']}) – "
            f"{segment['destination_city']} ({segment['destination']})"
        )

        flight_label = segment["flight"]

        if segment["is_train"]:
            flight_label += " (vlak)"

        lines.append(
            f"{date_text} | {flight_label} | {route} | "
            f"{segment['departure']}–{segment['arrival']} | "
            f"{format_duration(segment['duration_minutes'])}"
        )

    return "\n".join(lines)


def display_table(segments):
    rows = []

    for segment in segments:
        flight_label = segment["flight"]

        if segment["is_train"]:
            flight_label += "\nvlak"

        rows.append({
            "Datum": segment["date"].strftime("%d.%m.%Y"),
            "Let": flight_label,
            "Relacija": (
                f"{segment['origin_city']} ({segment['origin']}) – "
                f"{segment['destination_city']} ({segment['destination']})"
            ),
            "Odhod": segment["departure"],
            "Prihod": segment["arrival"],
            "Trajanje leta": format_duration(segment["duration_minutes"]),
            "Čas prestopa": format_duration(segment["layover_minutes"]),
        })

    return rows


# ---------------------------------------------------------
# HTML TABELA – MODRO-ZLATA + ROBOTO
# ---------------------------------------------------------

def render_copyable_table(rows):
    if not rows:
        return

    headers = list(rows[0].keys())

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
        "border:1px solid #D5DEE7;"
        "border-bottom:4px solid #FBB900;"
        "white-space:nowrap;"
    )

    td_base = (
        "padding:8px 10px;"
        "border:1px solid #D5DEE7;"
        "vertical-align:top;"
        "font-family:Roboto,Arial,Helvetica,sans-serif;"
        "font-size:13px;"
        "font-weight:400;"
    )

    nowrap_columns = {
        "Datum", "Let", "Odhod", "Prihod",
        "Trajanje leta", "Čas prestopa",
    }

    html_rows = [f'<table style="{table_style}"><thead><tr>']

    for header in headers:
        html_rows.append(
            f'<th style="{th_style}">{html.escape(header)}</th>'
        )

    html_rows.append("</tr></thead><tbody>")

    for row_index, row in enumerate(rows):
        background = "#FFF9E8" if row_index % 2 else "#FFFFFF"
        html_rows.append("<tr>")

        for header in headers:
            raw_value = str(row.get(header, ""))

            cell_style = td_base + f"background-color:{background};"

            if header in nowrap_columns:
                cell_style += "white-space:nowrap;"
            else:
                cell_style += (
                    "white-space:normal;"
                    "overflow-wrap:anywhere;"
                    "max-width:280px;"
                )

            if header == "Let" and "\n" in raw_value:
                flight_number, label = raw_value.split("\n", 1)

                value = (
                    f"{html.escape(flight_number)}"
                    f'<br><span style="font-size:10px;'
                    f'font-weight:400;color:#526579;">'
                    f"{html.escape(label)}</span>"
                )
            else:
                value = html.escape(raw_value)

            html_rows.append(
                f'<td style="{cell_style}">{value}</td>'
            )

        html_rows.append("</tr>")

    html_rows.append("</tbody></table>")
    table_html = "".join(html_rows)

    # Besedilna različica za kopiranje v Loop ali e-pošto.
    tsv_lines = ["\t".join(headers)]

    for row in rows:
        values = []

        for header in headers:
            value = str(row.get(header, ""))

            if header == "Let":
                value = value.replace("\nvlaк", " (vlak)")
                value = value.replace("\nvlak", " (vlak)")

            values.append(value)

        tsv_lines.append("\t".join(values))

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

          <button id="copyTable"
            style="
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
                      [htmlTable], {{type: "text/html"}}
                    ),
                    "text/plain": new Blob(
                      [plainText], {{type: "text/plain"}}
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
        "Primer 1:\n"
        "1  OS3580 S 08NOV 7 GGZVIE HK1 0600 0857 TRN E 1\n\n"
        "Primer 2:\n"
        "1  *OS3580 S 08NOV GGZ VIE 3 0600 0857 E1/TRN\n"
        "EN*OS 353 S 08NOV VIE 3 LYS 1 1015 1205 E0/E95 0605"
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
            "Segmentov nisem prepoznala. Preveri obliko izpisa "
            "in ali vrstice vsebujejo datume, relacije ter čase."
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
        "Če se oblikovanje ne prenese, je to lahko omejitev "
        "brskalnika ali ciljnega programa."
    )

    render_copyable_table(rows)
