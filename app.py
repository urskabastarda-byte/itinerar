
import re
import html
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(
    page_title="Amadeus – potovalni načrt",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ Amadeus – potovalni načrt")
st.caption("Prilepi letalske segmente iz Amadeusa in ustvari pregledno tabelo za stranko.")


# ---------------------------------------------------------
# LETALIŠČA
# Po potrebi lahko seznam razširiš.
# Ključ: IATA koda; vrednost: mesto, časovni pas
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
}


# ---------------------------------------------------------
# POMOŽNE FUNKCIJE
# ---------------------------------------------------------

def airport_info(code):
    code = code.upper()
    if code in AIRPORTS:
        city, tz = AIRPORTS[code]
        return city, tz
    return code, "UTC"


def parse_date(token, year):
    """Prebere datum v oblikah, kot so 24SEP ali 24OCT."""
    token = token.upper().strip()
    match = re.fullmatch(r"(\d{1,2})([A-Z]{3})", token)

    if not match:
        return None

    day = int(match.group(1))
    month_text = match.group(2)

    months = {
        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4,
        "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8,
        "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    }

    month = months.get(month_text)
    if not month:
        return None

    try:
        return date(year, month, day)
    except ValueError:
        return None


def format_duration(minutes):
    if minutes < 0:
        return "—"

    hours, mins = divmod(minutes, 60)

    if hours and mins:
        return f"{hours} h {mins} min"
    if hours:
        return f"{hours} h"
    return f"{mins} min"


def time_difference_minutes(start_date, start_time, start_tz,
                            end_date, end_time, end_tz):
    """Izračuna trajanje med lokalnima časoma z upoštevanjem časovnih pasov."""
    try:
        start_dt = datetime.strptime(
            f"{start_date} {start_time}", "%Y-%m-%d %H%M"
        ).replace(tzinfo=ZoneInfo(start_tz))

        end_dt = datetime.strptime(
            f"{end_date} {end_time}", "%Y-%m-%d %H%M"
        ).replace(tzinfo=ZoneInfo(end_tz))

        return int((end_dt - start_dt).total_seconds() // 60)
    except Exception:
        return None


# ---------------------------------------------------------
# PARSANJE AMADEUS SEGMENTOV
# ---------------------------------------------------------

def parse_segments(raw):
    """
    Podpira običajne vrstice Amadeus, npr.:
    2  AZ1358 Y 31OCT 6 TRSFCO HK1 1115 1225
    2  LH 123 C 24SEP 4 LJU FRA HK1 0600 0715
    """

    raw_lines = [line.strip() for line in raw.splitlines() if line.strip()]
    parsed = []

    # Zajamemo številko segmenta, letalsko družbo, številko leta,
    # datum, relacijo, status, čas odhoda in čas prihoda.
    pattern = re.compile(
        r"^\s*\d+\s+"
        r"([A-Z0-9]{2})\s*([A-Z0-9]{1,4})\s+"
        r"([A-Z])\s+"
        r"(\d{1,2}[A-Z]{3})\s+"
        r"(?:\d\s+)?"
        r"([A-Z]{3})\s*([A-Z]{3})\s+"
        r"([A-Z]{2}\d?)\s+"
        r"(?:\d\s+)?"
        r"(\d{4})\s+(\d{4})",
        re.IGNORECASE,
    )

    # Najprej poiščemo datume, da lahko ocenimo leto.
    today = date.today()
    first_date_token = None

    for line in raw_lines:
        match = pattern.search(line)
        if match:
            first_date_token = match.group(4)
            break

    if not first_date_token:
        return []

    current_year = today.year
    first_date = parse_date(first_date_token, current_year)

    if first_date and first_date < today:
        base_year = current_year + 1
    else:
        base_year = current_year

    previous_date = None

    for line in raw_lines:
        match = pattern.search(line)
        if not match:
            continue

        airline = match.group(1).upper()
        flight_number = match.group(2).upper()
        date_token = match.group(4).upper()
        origin = match.group(5).upper()
        destination = match.group(6).upper()
        departure_time = match.group(8)
        arrival_time = match.group(9)

        flight_date = parse_date(date_token, base_year)
        if not flight_date:
            continue

        # Če pot poteka čez novo leto, povečamo leto.
        if previous_date and flight_date < previous_date:
            base_year += 1
            flight_date = parse_date(date_token, base_year)

        previous_date = flight_date

        origin_city, origin_tz = airport_info(origin)
        destination_city, destination_tz = airport_info(destination)

        arrival_date = flight_date

        # Če je prihod po lokalni uri videti zgodnejši od odhoda,
        # predpostavimo prihod naslednji dan. Časovni pasovi se
        # upoštevajo pri izračunu trajanja.
        dep_minutes = int(departure_time[:2]) * 60 + int(departure_time[2:])
        arr_minutes = int(arrival_time[:2]) * 60 + int(arrival_time[2:])

        duration = time_difference_minutes(
            flight_date, departure_time, origin_tz,
            arrival_date, arrival_time, destination_tz,
        )

        if duration is not None and duration < 0:
            arrival_date += timedelta(days=1)
            duration = time_difference_minutes(
                flight_date, departure_time, origin_tz,
                arrival_date, arrival_time, destination_tz,
            )

        parsed.append({
            "date": flight_date,
            "flight": f"{airline}{flight_number}",
            "origin": origin,
            "destination": destination,
            "origin_city": origin_city,
            "destination_city": destination_city,
            "departure": departure_time[:2] + ":" + departure_time[2:],
            "arrival": arrival_time[:2] + ":" + arrival_time[2:],
            "duration_minutes": duration,
            "arrival_date": arrival_date,
        })

    # Izračunamo prestope med zaporednimi segmenti.
    for i, segment in enumerate(parsed):
        layover = None

        if i < len(parsed) - 1:
            next_segment = parsed[i + 1]

            if segment["destination"] == next_segment["origin"]:
                _, tz = airport_info(segment["destination"])

                try:
                    arrival_dt = datetime.strptime(
                        f"{segment['arrival_date']} {segment['arrival']}",
                        "%Y-%m-%d %H:%M",
                    ).replace(tzinfo=ZoneInfo(tz))

                    next_departure_dt = datetime.strptime(
                        f"{next_segment['date']} {next_segment['departure']}",
                        "%Y-%m-%d %H:%M",
                    ).replace(tzinfo=ZoneInfo(tz))

                    layover_minutes = int(
                        (next_departure_dt - arrival_dt).total_seconds() // 60
                    )

                    # Ohranimo le smiselne prestope.
                    if 0 <= layover_minutes <= 18 * 60:
                        layover = layover_minutes
                except Exception:
                    pass

        segment["layover_minutes"] = layover

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

        duration = (
            format_duration(segment["duration_minutes"])
            if segment["duration_minutes"] is not None
            else "—"
        )

        lines.append(
            f"{date_text} | {segment['flight']} | {route} | "
            f"{segment['departure']}–{segment['arrival']} | {duration}"
        )

    return "\n".join(lines)


def display_table(segments):
    rows = []

    for segment in segments:
        duration = (
            format_duration(segment["duration_minutes"])
            if segment["duration_minutes"] is not None
            else "—"
        )

        layover = (
            format_duration(segment["layover_minutes"])
            if segment["layover_minutes"] is not None
            else "—"
        )

        rows.append({
            "Datum": segment["date"].strftime("%d.%m.%Y"),
            "Let": segment["flight"],
            "Relacija": (
                f"{segment['origin_city']} ({segment['origin']}) – "
                f"{segment['destination_city']} ({segment['destination']})"
            ),
            "Odhod": segment["departure"],
            "Prihod": segment["arrival"],
            "Trajanje leta": duration,
            "Čas prestopa": layover,
        })

    return rows


# ---------------------------------------------------------
# HTML TABELE – MODEREN, A PREPROST MODER SLOG
# ---------------------------------------------------------

def render_copyable_table(rows):
    if not rows:
        return

    headers = list(rows[0].keys())

    # Slogi so zapisani neposredno v elementih, da se pri
    # kopiranju v Loop/e-pošto čim bolje ohranijo.
    table_style = (
        "border-collapse:collapse;"
        "width:auto;"
        "max-width:100%;"
        "font-family:Arial,Helvetica,sans-serif;"
        "font-size:13px;"
        "color:#263445;"
    )

    th_style = (
        "background-color:#23476A;"
        "color:#FFFFFF;"
        "font-weight:700;"
        "text-align:left;"
        "padding:7px 9px;"
        "border:1px solid #D5DEE7;"
        "white-space:nowrap;"
    )

    td_base = (
        "padding:7px 9px;"
        "border:1px solid #D5DEE7;"
        "vertical-align:top;"
    )

    nowrap_columns = {
        "Datum", "Let", "Odhod", "Prihod",
        "Trajanje leta", "Čas prestopa"
    }

    html_rows = []

    html_rows.append(
        f'<table style="{table_style}">'
        "<thead><tr>"
    )

    for header in headers:
        html_rows.append(
            f'<th style="{th_style}">{html.escape(header)}</th>'
        )

    html_rows.append("</tr></thead><tbody>")

    for row_index, row in enumerate(rows):
        background = "#F0F6FB" if row_index % 2 == 1 else "#FFFFFF"
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

            html_rows.append(
                f'<td style="{cell_style}">{value}</td>'
            )

        html_rows.append("</tr>")

    html_rows.append("</tbody></table>")

    table_html = "".join(html_rows)

    # TSV je rezervna možnost, če brskalnik ne dovoli kopiranja HTML.
    tsv_lines = ["\t".join(headers)]

    for row in rows:
        tsv_lines.append(
            "\t".join(str(row.get(header, "")) for header in headers)
        )

    tsv_text = "\n".join(tsv_lines)

    safe_html = table_html.replace("\\", "\\\\").replace("`", "\\`")
    safe_tsv = tsv_text.replace("\\", "\\\\").replace("`", "\\`")

    components.html(
        f"""
        <div style="font-family:Arial,Helvetica,sans-serif;">
          <button id="copyTable"
            style="
              background:#23476A;
              color:white;
              border:0;
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
            style="font-size:12px;color:#526579;margin-left:8px;"></span>
          <div style="overflow-x:auto;">
            {table_html}
          </div>
        </div>

        <script>
          const htmlTable = `{safe_html}`;
          const plainText = `{safe_tsv}`;

          document.getElementById("copyTable").addEventListener("click", async () => {{
            const status = document.getElementById("copyStatus");

            try {{
              if (navigator.clipboard && window.ClipboardItem) {{
                const item = new ClipboardItem({{
                  "text/html": new Blob([htmlTable], {{type:"text/html"}}),
                  "text/plain": new Blob([plainText], {{type:"text/plain"}})
                }});
                await navigator.clipboard.write([item]);
                status.textContent = "Tabela je kopirana.";
              }} else if (navigator.clipboard && navigator.clipboard.writeText) {{
                await navigator.clipboard.writeText(plainText);
                status.textContent = "Kopirano kot besedilo.";
              }} else {{
                status.textContent =
                  "Kopiranje ni podprto v tem brskalniku. Označi tabelo in jo kopiraj.";
              }}
            }} catch (err) {{
              status.textContent =
                "Kopiranje ni uspelo. Poskusi ponovno ali kopiraj tabelo ročno.";
            }}
          }});
        </script>
        """,
        height=max(190, 58 + 39 * len(rows)),
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
        "2  AZ1358 Y 31OCT 6 TRSFCO HK1 1115 1225\n"
        "3  AZ 204 Y 31OCT 6 FCOMAD HK1 1400 1630"
    ),
)

if st.button("Ustvari potovalni načrt", type="primary"):
    segments = parse_segments(raw_input)

    if segments:
        st.session_state["segments"] = segments
        st.session_state["raw_input"] = raw_input
    else:
        st.session_state.pop("segments", None)
        st.error(
            "Segmentov nisem prepoznala. Preveri, ali si prilepila "
            "vrstice z datumi, letalskimi številkami, relacijami in časi."
        )

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
        "Če se oblikovanje ne prenese, preveri možnost lepljenja "
        "v ciljnem programu."
    )

    render_copyable_table(rows)
