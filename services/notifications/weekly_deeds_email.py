import os
import sys
import json
import time
import math
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple

import urllib.parse
import urllib.request

try:
    from pyproj import Transformer
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


ARCGIS_FEATURE_URL = (
    "https://gis.tetoncountywy.gov/server/rest/services/Public_Services/land_records_search/FeatureServer/0/query"
)


def _epoch_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def transform_state_plane_to_wgs84(x: float, y: float) -> Optional[Tuple[float, float]]:
    """Transform State Plane Wyoming West (EPSG:3739) coordinates to WGS84 (EPSG:4326).
    
    Returns (lng, lat) tuple or None if transformation fails.
    """
    if not HAS_PYPROJ:
        # Rough approximation for Teton County area if pyproj unavailable
        # This is not accurate but better than nothing
        logger.warning("Using approximate coordinate transformation (pyproj not available)")
        # Teton County approximate center and offset
        ref_lng, ref_lat = -110.76, 43.49
        ref_x, ref_y = 2440000.0, 1410000.0
        scale = 0.0000009  # rough feet to degrees
        lng = ref_lng + (x - ref_x) * scale
        lat = ref_lat + (y - ref_y) * scale
        return (lng, lat)
    
    try:
        transformer = Transformer.from_crs("EPSG:3739", "EPSG:4326", always_xy=True)
        lng, lat = transformer.transform(x, y)
        return (lng, lat)
    except Exception as e:
        logger.warning(f"Coordinate transformation failed: {e}")
        return None


def estimate_zoom_from_bbox(minx: float, maxx: float, miny: float, maxy: float) -> float:
    """Estimate a reasonable zoom level based on bbox extent in feet."""
    max_dim = max(maxx - minx, maxy - miny)
    if not math.isfinite(max_dim) or max_dim <= 0:
        return 16.5
    if max_dim <= 60:
        return 18.0
    if max_dim <= 120:
        return 17.5
    if max_dim <= 250:
        return 17.0
    if max_dim <= 500:
        return 16.0
    if max_dim <= 1000:
        return 15.0
    if max_dim <= 2000:
        return 14.0
    return 13.0


def construct_map_url(lng: float, lat: float, highlights: Optional[str] = None, base_url: str = "http://localhost:3000", zoom: float = 15.0) -> str:
    """Construct map URL with center coordinates and optional highlights.
    
    Args:
        lng: Longitude (WGS84)
        lat: Latitude (WGS84)
        highlights: Optional highlights parameter in format "county_county_parcel_id" (e.g. "teton_county_wy_22-41-17-14-4-00-037")
        base_url: Base URL for the map application (with or without /map path)
        zoom: Desired map zoom level
    
    Returns:
        Full map URL string
    """
    parsed = urllib.parse.urlparse(base_url)
    query_params = {}
    query_params.update({
        "basemap": "streets-v11",
        "layers": "ownership",
        "lat": f"{lat:.5f}",
        "lng": f"{lng:.5f}",
        "zoom": f"{zoom:.2f}",
    })
    if highlights:
        highlight_values = [h for h in str(highlights).split(",") if h]
        if highlight_values:
            deduped = list(dict.fromkeys(highlight_values))
            query_params["highlights"] = ",".join(deduped)

    # Normalize path - ensure it ends with /map
    path = parsed.path or ""
    if not path or path == "/":
        path = "/map"
    else:
        trimmed = path.rstrip("/")
        if not trimmed.lower().endswith("/map"):
            path = f"{trimmed}/map"
        else:
            path = trimmed

    query_string = urllib.parse.urlencode(query_params)
    final_url = urllib.parse.urlunparse(parsed._replace(path=path, query=query_string, params="", fragment=""))
    return final_url


def fetch_deed_records_since(since_dt: datetime, max_records: int = 10000) -> List[Dict[str, Any]]:
    """Fetch all clerk records since given datetime (no deed-only filter).

    Uses pagination with resultOffset to retrieve all matching features.
    """
    results: List[Dict[str, Any]] = []
    offset = 0
    page_size = 200
    since_ms = _epoch_ms(since_dt)
    now_ms = _epoch_ms(datetime.now(tz=timezone.utc))

    # Limit to deed-like descriptions server-side; URL encoding is handled by urlencode
    where = "UPPER(description) LIKE '%DEED%'"

    common_params = {
        "f": "json",
        "where": where,
        "outFields": ",".join([
            "grantor",
            "grantee",
            "datetimeoffiling",
            "description",
            "entrynumber",
            "statepin",
            "record_url",
            "record_name",
            "dateofinstrument",
            "legal",
            "sort_order",
            "objectid",
        ]),
        "returnGeometry": "true",
        "orderByFields": "sort_order ASC, entrynumber DESC",
    }

    while True:
        params = dict(common_params)
        params["resultOffset"] = str(offset)
        params["resultRecordCount"] = str(page_size)

        url = f"{ARCGIS_FEATURE_URL}?{urllib.parse.urlencode(params)}"
        logger.info(f"Fetching: offset={offset}")

        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        features = data.get("features", [])
        if not features:
            break

        older_than_window_count = 0
        for feat in features:
            attrs = feat.get("attributes", {})
            geom = feat.get("geometry") or {}
            dt_file_ms = attrs.get("datetimeoffiling")
            dt_instr_ms = attrs.get("dateofinstrument")

            # Decide if within window: prefer datetimeoffiling, else dateofinstrument
            effective_ms = None
            if isinstance(dt_file_ms, (int, float)):
                effective_ms = dt_file_ms
            elif isinstance(dt_instr_ms, (int, float)):
                effective_ms = dt_instr_ms

            if isinstance(effective_ms, (int, float)) and effective_ms < since_ms:
                older_than_window_count += 1
                continue
            # Additional client-side guard for deed-only
            desc_val = (attrs.get("description") or "")
            if "deed" not in str(desc_val).lower():
                continue
            # Normalize and retain only needed fields
            results.append({
                "grantor": attrs.get("grantor"),
                "grantee": attrs.get("grantee"),
                "datetimeoffiling": dt_file_ms,
                "description": attrs.get("description"),
                "entrynumber": attrs.get("entrynumber"),
                "statepin": attrs.get("statepin"),
                "record_url": attrs.get("record_url"),
                "record_name": attrs.get("record_name"),
                "dateofinstrument": dt_instr_ms,
                "legal": attrs.get("legal"),
                "geometry": geom,
            })

        offset += len(features)
        # If most of the page is older than window, assume remaining pages will be older too
        if older_than_window_count >= len(features) * 0.8:
            break
        if offset >= max_records:
            break

    return results


def construct_record_links(record: Dict[str, Any]) -> Dict[str, str]:
    links: Dict[str, str] = {}

    entrynumber = record.get("entrynumber")
    statepin = record.get("statepin")
    record_url = record.get("record_url")

    # Direct PDF when public and known by entry number
    if entrynumber and (not record_url or "no_documents.html" in str(record_url)):
        links["document"] = f"https://s3.us-west-2.amazonaws.com/tetoncountywy/clerk/pdf/{entrynumber}.pdf"
    elif record_url:
        links["document"] = str(record_url)

    # County clerk dashboard deep link by statepin
    if statepin:
        links["clerk_dashboard"] = (
            "https://gis.tetoncountywy.gov/portal/apps/dashboards/03ef10d8b8634909b6263e9016bcc986#statepin="
            + str(statepin)
        )

    return links


def load_subscribers(file_path: str) -> List[str]:
    emails: List[str] = []
    if not os.path.exists(file_path):
        return emails
    with open(file_path, "r") as f:
        for line in f:
            addr = line.strip()
            if addr and not addr.startswith("#"):
                emails.append(addr)
    return emails


def format_email_subject(week_start: datetime, week_end: datetime) -> str:
    return f"Weekly Deed Records in Jackson: {week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"


def format_email_body(records: List[Dict[str, Any]], week_start: datetime, week_end: datetime) -> str:
    if not records:
        return (
            f"No deed-related property changes were recorded between "
            f"{week_start.strftime('%Y-%m-%d')} and {week_end.strftime('%Y-%m-%d')}"
        )

    lines: List[str] = []
    lines.append(
        f"Deed records filed {week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')} (Jackson/Teton County, WY):"
    )
    lines.append("")

    for r in records:
        dt_ms = r.get("datetimeoffiling") or r.get("dateofinstrument")
        dt_str = datetime.fromtimestamp(dt_ms / 1000, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M") if dt_ms else ""
        grantor = r.get("grantor") or ""
        grantee = r.get("grantee") or ""
        desc = r.get("description") or ""
        entry = r.get("entrynumber") or ""
        statepin = r.get("statepin") or ""
        legal = r.get("legal") or ""
        geom = r.get("geometry") or {}

        links = construct_record_links(r)
        doc_link = links.get("document")
        dash_link = links.get("clerk_dashboard")

        # Compute bbox if polygon geometry present and generate map link
        bbox_line = None
        map_link = None
        rings = geom.get("rings") if isinstance(geom, dict) else None
        if isinstance(rings, list) and rings:
            xs = []
            ys = []
            try:
                for ring in rings:
                    for pt in ring:
                        if isinstance(pt, list) and len(pt) >= 2:
                            xs.append(float(pt[0]))
                            ys.append(float(pt[1]))
                if xs and ys:
                    minx, maxx = min(xs), max(xs)
                    miny, maxy = min(ys), max(ys)
                    bbox_line = f"BBOX (state plane ft): [{minx:.3f}, {miny:.3f}, {maxx:.3f}, {maxy:.3f}]"
                    
                    # Calculate center and transform to lat/lng for map link
                    center_x = (minx + maxx) / 2.0
                    center_y = (miny + maxy) / 2.0
                    coords = transform_state_plane_to_wgs84(center_x, center_y)
                    if coords:
                        lng, lat = coords
                        map_base_url = os.getenv("MAP_BASE_URL", "http://localhost:3000")
                        
                        # Construct highlights parameter: county_county_parcel_id
                        # Format: teton_county_wy_{statepin}
                        highlights_param = None
                        if statepin:
                            highlights_param = f"teton_county_wy_{statepin}"
                        
                        zoom_level = estimate_zoom_from_bbox(minx, maxx, miny, maxy)
                        map_link = construct_map_url(lng, lat, highlights_param, map_base_url, zoom_level)
            except Exception as e:
                logger.debug(f"Error processing geometry: {e}")
                bbox_line = None
                map_link = None

        lines.append(f"- {dt_str} | {desc} | Entry #{entry}")
        lines.append(f"  Grantor: {grantor}")
        lines.append(f"  Grantee: {grantee}")
        if statepin:
            lines.append(f"  State PIN (PIDN): {statepin}")
        if legal:
            lines.append(f"  Legal: {legal}")
        if bbox_line:
            lines.append(f"  {bbox_line}")
        if map_link:
            lines.append(f"  View on Map: {map_link}")
        if doc_link:
            lines.append(f"  Document: {doc_link}")
        if dash_link:
            lines.append(f"  Clerk Dashboard: {dash_link}")
        lines.append("")

    return "\n".join(lines)


def send_email_smtp(subject: str, body: str, to_email: str) -> None:
    """Lightweight SMTP sender using environment variables for credentials.

    Env vars:
      SMTP_USER, SMTP_PASS, SMTP_FROM
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    if not smtp_user or not smtp_pass:
        raise RuntimeError("SMTP_USER/SMTP_PASS not configured in environment")

    msg = MIMEMultipart()
    msg['From'] = smtp_from
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(smtp_user, smtp_pass)
    server.sendmail(smtp_from, to_email, msg.as_string())
    server.quit()


def main() -> None:
    # Week window: last 7 full days ending now
    now = datetime.now(tz=timezone.utc)
    week_start = now - timedelta(days=7)

    logger.info("Fetching clerk records for last 7 days...")
    records = fetch_deed_records_since(week_start)
    logger.info(f"Fetched {len(records)} deed-like records")

    # Compose email
    subject = format_email_subject(week_start.astimezone(), now.astimezone())
    body = format_email_body(records, week_start.astimezone(), now.astimezone())

    # Log a short preview to stdout for debugging/verification
    try:
        preview_lines = body.splitlines()[:60]
        logger.info("Email preview (first lines):\n" + "\n".join(preview_lines))
    except Exception:
        pass

    # Load subscribers
    script_dir = os.path.dirname(os.path.abspath(__file__))
    subscribers_file = os.path.join(script_dir, "subscribers.txt")
    subscribers = load_subscribers(subscribers_file)

    # Fallback to single recipient if desired
    if not subscribers:
        env_to = os.getenv("EMAIL_TO")
        if env_to:
            subscribers = [env_to]

    if not subscribers:
        logger.warning("No subscribers configured; skipping send")
        return

    # Send emails individually to avoid BCC complexity
    sent = 0
    for addr in subscribers:
        try:
            send_email_smtp(subject, body, addr)
            sent += 1
            logger.info(f"Sent to {addr}")
        except Exception as e:
            logger.error(f"Failed sending to {addr}: {e}")

    logger.info(f"Weekly deeds email sent to {sent}/{len(subscribers)} subscribers")


if __name__ == "__main__":
    main()


