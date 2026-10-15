
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
# BESEDILNI PREGLED
# =========================================================

def format_text(
