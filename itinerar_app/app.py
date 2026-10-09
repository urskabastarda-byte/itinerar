import re
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import streamlit as st

st.set_page_config(page_title="Amadeus Itinerary Generator", page_icon="✈️", layout="wide")

AIRPORTS = {
    "LJU": ("Ljubljana", "Europe/Ljubljana"), "TRS": ("Trst", "Europe/Rome"), "VCE": ("Benetke", "Europe/Rome"),
    "MXP": ("Milano Malpensa", "Europe/Rome"), "LIN": ("Milano Linate", "Europe/Rome"), "FCO": ("Rim Fiumicino", "Europe/Rome"),
    "CIA": ("Rim Ciampino", "Europe/Rome"), "NAP": ("Neapelj", "Europe/Rome"), "BRI": ("Bari", "Europe/Rome"),
    "BLQ": ("Bologna", "Europe/Rome"), "BGY": ("Bergamo", "Europe/Rome"), "VRN": ("Verona", "Europe/Rome"),
    "ZAG": ("Zagreb", "Europe/Zagreb"), "SPU": ("Split", "Europe/Zagreb"), "DBV": ("Dubrovnik", "Europe/Zagreb"),
    "BEG": ("Beograd", "Europe/Belgrade"), "SJJ": ("Sarajevo", "Europe/Sarajevo"), "SKP": ("Skopje", "Europe/Skopje"),
    "VIE": ("Dunaj", "Europe/Vienna"), "GRZ": ("Gradec", "Europe/Vienna"), "MUC": ("München", "Europe/Berlin"),
    "FRA": ("Frankfurt", "Europe/Berlin"), "BER": ("Berlin", "Europe/Berlin"), "HAM": ("Hamburg", "Europe/Berlin"),
    "DUS": ("Düsseldorf", "Europe/Berlin"), "ZRH": ("Zürich", "Europe/Zurich"), "GVA": ("Ženeva", "Europe/Zurich"),
    "CDG": ("Pariz Charles de Gaulle", "Europe/Paris"), "ORY": ("Pariz Orly", "Europe/Paris"), "AMS": ("Amsterdam", "Europe/Amsterdam"),
    "BRU": ("Bruselj", "Europe/Brussels"), "LHR": ("London Heathrow", "Europe/London"), "LGW": ("London Gatwick", "Europe/London"),
    "MAN": ("Manchester", "Europe/London"), "DUB": ("Dublin", "Europe/Dublin"), "MAD": ("Madrid", "Europe/Madrid"),
    "BCN": ("Barcelona", "Europe/Madrid"), "LIS": ("Lizbona", "Europe/Lisbon"), "ATH": ("Atene", "Europe/Athens"),
    "IST": ("Istanbul", "Europe/Istanbul"), "SAW": ("Istanbul Sabiha Gökçen", "Europe/Istanbul"), "DOH": ("Doha", "Asia/Qatar"),
    "DXB": ("Dubaj", "Asia/Dubai"), "AUH": ("Abu Dabi", "Asia/Dubai"), "JFK": ("New York JFK", "America/New_York"),
    "EWR": ("Newark", "America/New_York"), "LAX": ("Los Angeles", "America/Los_Angeles"), "SFO": ("San Francisco", "America/Los_Angeles"),
    "ORD": ("Chicago O’Hare", "America/Chicago"), "MIA": ("Miami", "America/New_York"), "YYZ": ("Toronto", "America/Toronto"),
    "YVR": ("Vancouver", "America/Vancouver"), "BKK": ("Bangkok", "Asia/Bangkok"), "SIN": ("Singapur", "Asia/Singapore"),
    "KUL": ("Kuala Lumpur", "Asia/Kuala_Lumpur"), "HKG": ("Hongkong", "Asia/Hong_Kong"), "PVG": ("Šanghaj Pudong", "Asia/Shanghai"),
    "PEK": ("Peking", "Asia/Shanghai"), "NRT": ("Tokio Narita", "Asia/Tokyo"), "HND": ("Tokio Haneda", "Asia/Tokyo"),
    "ICN": ("Seul Incheon", "Asia/Seoul"), "TPE": ("Taipei", "Asia/Taipei"), "SYD": ("Sydney", "Australia/Sydney"),
    "MEL": ("Melbourne", "Australia/Melbourne"), "CPT": ("Cape Town", "Africa/Johannesburg"), "JNB": ("Johannesburg", "Africa/Johannesburg"),
    "CAI": ("Kairo", "Africa/Cairo"), "NBO": ("Nairobi", "Africa/Nairobi"), "ADD": ("Adis Abeba", "Africa/Addis_Ababa"),
    "TBS": ("Tbilisi", "Asia/Tbilisi"), "EVN": ("Erevan", "Asia/Yerevan"), "ALA": ("Almaty", "Asia/Almaty"),
    "DEL": ("Delhi", "Asia/Kolkata"), "BOM": ("Mumbai", "Asia/Kolkata"), "CMB": ("Colombo", "Asia/Colombo"),
    "MLE": ("Malé", "Indian/Maldives"), "MRU": ("Mauritius", "Indian/Mauritius"), "TFS": ("Tenerife South", "Atlantic/Canary"),
    "LPA": ("Gran Canaria", "Atlantic/Canary"), "PMI": ("Palma de Mallorca", "Europe/Madrid"), "AGP": ("Málaga", "Europe/Madrid"),
    "ALC": ("Alicante", "Europe/Madrid"), "IBZ": ("Ibiza", "Europe/Madrid"), "HER": ("Heraklion", "Europe/Athens"),
    "RHO": ("Rodos", "Europe/Athens"), "AYT": ("Antalya", "Europe/Istanbul"), "DPS": ("Bali Denpasar", "Asia/Makassar"),
    "MNL": ("Manila", "Asia/Manila"), "SGN": ("Hošiminh", "Asia/Ho_Chi_Minh"), "HAN": ("Hanoj", "Asia/Ho_Chi_Minh"),
    "USM": ("Koh Samui", "Asia/Bangkok"), "HKT": ("Phuket", "Asia/Bangkok"), "KTM": ("Katmandu", "Asia/Kathmandu"),
}
MONTHS = {m.upper(): i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def airport(code):
    name, _ = AIRPORTS.get(code, (code, "UTC"))
    return name


def tz(code):
    return AIRPORTS.get(code, (code, "UTC"))[1]


def fmt_time(value):
    return value.strftime("%H:%M")


def fmt_duration(minutes):
    if minutes is None or minutes < 0:
        return "—"
    h, m = divmod(minutes, 60)
    return f"{h} h {m:02d} min"


def parse_date(token, year):
    token = token.upper()
    m = re.fullmatch(r"(\d{1,2})([A-Z]{3})", token)
    if not m or m.group(2) not in MONTHS:
        return None
    return date(year, MONTHS[m.group(2)], int(m.group(1)))


def parse_segments(raw, year):
    segments = []
    # A segment starts with an optional line/segment number, then a flight number and booking class.
    start_re = re.compile(r"^\s*(?:\d+\s+)?([A-Z0-9]{2,3}\s?\d{1,4}[A-Z]?)\s+([A-Z])\s+(\d{1,2}[A-Z]{3})\b(.*)$", re.I)
    time_re = re.compile(r"(?<!\d)(\d{4})(?:\+(\d))?\s+(\d{4})(?:\+(\d))?(?!\d)")
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
        # Remove common status/seat tokens; route can be written as TRSFCO or as TRS FCO 1.
        route_part = re.sub(r"\b(?:HK|HN|HL|TK|KL|SS|NN|GK)\d*\b", " ", route_part)
        route_part = re.sub(r"\b\d+\b", " ", route_part)
        route_tokens = re.findall(r"[A-Z]{3,6}", route_part)
        origin = destination = None
        if route_tokens:
            # Legacy display often joins both airport codes into a single six-letter token.
            joined = next((t for t in route_tokens if len(t) == 6 and t[:3] in AIRPORTS and t[3:] in AIRPORTS), None)
            if joined:
                origin, destination = joined[:3], joined[3:]
            else:
                three = [t for t in route_tokens if len(t) == 3]
                if len(three) >= 2:
                    origin, destination = three[0], three[1]
        if not origin or not destination:
            continue
        dep_date = parse_date(date_token, year)
        if not dep_date:
            continue
        dep_local = datetime.combine(dep_date, datetime.strptime(dep_token, "%H%M").time()).replace(tzinfo=ZoneInfo(tz(origin)))
        arr_date = dep_date + timedelta(days=int(arr_plus or 0))
        arr_local = datetime.combine(arr_date, datetime.strptime(arr_token, "%H%M").time()).replace(tzinfo=ZoneInfo(tz(destination)))
        if arr_local.astimezone(ZoneInfo("UTC")) < dep_local.astimezone(ZoneInfo("UTC")):
            arr_local += timedelta(days=1)
        duration = int((arr_local.astimezone(ZoneInfo("UTC")) - dep_local.astimezone(ZoneInfo("UTC"))).total_seconds() // 60)
        segments.append({
            "flight": re.sub(r"\s+", "", flight.upper()), "date": dep_date,
            "origin": origin, "destination": destination, "dep": dep_local, "arr": arr_local,
            "duration": duration,
        })
    # Compute connection time between consecutive segments, using local time zones.
    for i, seg in enumerate(segments):
        seg["layover"] = None
        if i + 1 < len(segments) and seg["destination"] == segments[i + 1]["origin"]:
            minutes = int((segments[i + 1]["dep"].astimezone(ZoneInfo("UTC")) - seg["arr"].astimezone(ZoneInfo("UTC"))).total_seconds() // 60)
            if 0 <= minutes <= 18 * 60:
                seg["layover"] = minutes
    return segments


def format_text(segments):
    lines = []
    for seg in segments:
        route = f"{airport(seg['origin'])} ({seg['origin']}) – {airport(seg['destination'])} ({seg['destination']})"
        date_text = seg["date"].strftime("%d.%m.%Y")
        arr_plus = " +1" if seg["arr"].date() > seg["date"] else ""
        line = f"{date_text}  {seg['flight']}  {route}  {fmt_time(seg['dep'])}–{fmt_time(seg['arr'])}{arr_plus}"
        if seg["layover"] is not None:
            line += f"    * Čas prestopa: {fmt_duration(seg['layover'])}"
        lines.append(line)
    return "\n".join(lines)


def display_table(segments):
    rows = []
    for seg in segments:
        rows.append({
            "Datum": seg["date"].strftime("%d.%m.%Y"),
            "Let": seg["flight"],
            "Relacija": f"{airport(seg['origin'])} ({seg['origin']}) – {airport(seg['destination'])} ({seg['destination']})",
            "Odhod": fmt_time(seg["dep"]),
            "Prihod": fmt_time(seg["arr"]) + (" +1" if seg["arr"].date() > seg["date"] else ""),
            "Trajanje leta": fmt_duration(seg["duration"]),
            "Čas prestopa": fmt_duration(seg["layover"]) if seg["layover"] is not None else "—",
        })
    return rows


st.title("✈️ Amadeus Itinerary Generator")
st.write("Prilepi Amadeus izpis letov in pripravi itinerar za kopiranje v e-pošto.")
col1, col2 = st.columns([3, 1])
with col2:
    year = st.number_input("Leto odhoda", min_value=2020, max_value=2040, value=datetime.now().year, step=1)
with col1:
    raw = st.text_area("Amadeus zapis", height=250, placeholder="Prilepi vrstice z leti iz Amadeusa …")

if st.button("Ustvari itinerar", type="primary", use_container_width=True):
    if not raw.strip():
        st.warning("Najprej prilepi Amadeus zapis letov.")
    else:
        segments = parse_segments(raw, int(year))
        if not segments:
            st.error("Nisem prepoznala nobenega leta. Prilepi vrstice z leti (številka leta, datum, relacija in časi) in poskusi znova.")
        else:
            st.success(f"Prepoznanih letov: {len(segments)}")
            st.subheader("Besedilo za e-pošto")
            output = format_text(segments)
            st.code(output, language=None)
            st.download_button("Prenesi besedilo (.txt)", data=output, file_name="itinerar.txt", mime="text/plain; charset=utf-8")
            st.subheader("Preglednica")
            st.dataframe(display_table(segments), use_container_width=True, hide_index=True)
            st.caption("Opomba: pri neznanih letališčih je za izračun trajanja uporabljena privzeta časovna cona UTC. Pred pošiljanjem preveri čase in prestope.")

st.divider()
st.caption("V orodje ne vnašaj imen potnikov, številk kart ali drugih osebnih podatkov — zadostujejo vrstice z leti.")
