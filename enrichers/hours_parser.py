"""
Japanese Opening Hours Parser for Restaurant Aggregators (Tabelog / HotPepper)
Normalizes freeform Japanese opening schedules into machine-readable weekday time slots.
"""
import re
from datetime import datetime, time
from typing import Dict, List, Any, Optional

DAYS_MAP = {
    '月': 0, '火': 1, '水': 2, '木': 3, '金': 4, '土': 5, '日': 6
}
DAY_NAMES = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
DAY_NAMES_JA = {'mon': '月', 'tue': '火', 'wed': '水', 'thu': '木', 'fri': '金', 'sat': '土', 'sun': '日'}

def parse_time_str(t_str: str) -> Optional[int]:
    """Converts HH:MM string into minutes since midnight (0..1439)."""
    m = re.match(r'^(\d{1,2}):(\d{2})$', t_str.strip())
    if not m:
        return None
    h, minute = int(m.group(1)), int(m.group(2))
    return h * 60 + minute

def parse_opening_hours(hours_text: str, holiday_text: str = "") -> Dict[str, Any]:
    """
    Parses Tabelog opening hours into structured daily schedules.
    Returns:
    {
        "days": {
            "mon": [{"start": "11:30", "end": "15:00", "overnight": False}, ...],
            ...
        },
        "raw_hours": str,
        "raw_holiday": str,
        "is_24h": bool,
        "is_unclear": bool
    }
    """
    cleaned_hours = (hours_text or "").strip()
    cleaned_holiday = (holiday_text or "").strip()
    
    schedule = {day: [] for day in DAY_NAMES}
    is_24h = False
    
    if "24時間営業" in cleaned_hours:
        is_24h = True
        for day in DAY_NAMES:
            schedule[day].append({"start": "00:00", "end": "24:00", "overnight": False})
        return {
            "days": schedule,
            "raw_hours": cleaned_hours,
            "raw_holiday": cleaned_holiday,
            "is_24h": True,
            "is_unclear": False
        }

    lines = [line.strip() for line in cleaned_hours.split('\n') if line.strip()]
    current_days: List[int] = []
    has_found_any_slot = False

    for line in lines:
        if any(stop_word in line for stop_word in ['■ 営業時間', '■ 定休日', '年末年始', '※新型コロナ', '※最新の']):
            break

        # Check for day ranges or lists, e.g. "月・火・水・木・金" or "月～金" or "土・日・祝日" or "日"
        day_matches = re.findall(r'[月火水木金土日]', line)
        if day_matches and any(k in line for k in ['・', '〜', '～', '月', '火', '水', '木', '金', '土', '日']):
            # Verify this line is not just a sentence with hours
            if not re.search(r'\d{1,2}:\d{2}', line) and not ('定休日' in line and len(day_matches) == 0):
                range_match = re.search(r'([月火水木金土日])\s*[～~-]\s*([月火水木金土日])', line)
                if range_match:
                    start_d = DAYS_MAP[range_match.group(1)]
                    end_d = DAYS_MAP[range_match.group(2)]
                    current_days = []
                    curr = start_d
                    while True:
                        current_days.append(curr)
                        if curr == end_d:
                            break
                        curr = (curr + 1) % 7
                else:
                    current_days = [DAYS_MAP[d] for d in day_matches]

                if '定休日' in line:
                    for d in current_days:
                        schedule[DAY_NAMES[d]] = []
                    current_days = []
                continue

        # Check for standalone "定休日" line following a day marker
        if '定休日' in line:
            target_days = current_days if current_days else []
            for d in target_days:
                schedule[DAY_NAMES[d]] = []
            current_days = []
            continue

        # Check for time range pattern: "11:30 - 15:00" or "17:00～23:00"
        time_matches = re.findall(r'(\d{1,2}:\d{2})\s*[-~～]\s*(\d{1,2}:\d{2})', line)
        if time_matches:
            target_days = current_days if current_days else list(range(7))
            for start_t, end_t in time_matches:
                s_min = parse_time_str(start_t)
                e_min = parse_time_str(end_t)
                overnight = False
                if s_min is not None and e_min is not None and e_min < s_min:
                    overnight = True
                
                for d_idx in target_days:
                    day_name = DAY_NAMES[d_idx]
                    exists = any(s['start'] == start_t and s['end'] == end_t for s in schedule[day_name])
                    if not exists:
                        schedule[day_name].append({
                            'start': start_t,
                            'end': end_t,
                            'overnight': overnight
                        })
                        has_found_any_slot = True

    # Parse explicit holiday text if any
    if cleaned_holiday:
        if "無休" in cleaned_holiday or "年中無休" in cleaned_holiday:
            pass
        else:
            hol_matches = re.findall(r'[月火水木金土日]', cleaned_holiday)
            for h in hol_matches:
                d_idx = DAYS_MAP[h]
                schedule[DAY_NAMES[d_idx]] = []

    return {
        "days": schedule,
        "raw_hours": cleaned_hours,
        "raw_holiday": cleaned_holiday,
        "is_24h": is_24h,
        "is_unclear": not has_found_any_slot
    }

def is_open_now(schedule_data: Dict[str, Any], check_dt: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Evaluates whether a restaurant is open at check_dt (defaults to now).
    Returns status:
    {
        "open": True/False,
        "current_slot": {"start": "17:00", "end": "22:00"} or None,
        "status_label": "Open Now" / "Closed" / "Closing Soon",
        "next_change": "Closes at 22:00" / "Opens tomorrow at 11:30"
    }
    """
    if check_dt is None:
        check_dt = datetime.now()

    if schedule_data.get("is_24h"):
        return {
            "open": True,
            "status_label": "Open 24 Hours",
            "next_change": "Open all day"
        }

    if schedule_data.get("is_unclear"):
        return {
            "open": True, # Assume open if unclear, but flag it
            "status_label": "Hours Unconfirmed",
            "next_change": "Check with store"
        }

    weekday = check_dt.weekday() # 0 = Monday, 6 = Sunday
    today_key = DAY_NAMES[weekday]
    yesterday_key = DAY_NAMES[(weekday - 1) % 7]
    current_minutes = check_dt.hour * 60 + check_dt.minute

    # Check 1: Did yesterday's overnight shift spill over into today?
    for slot in schedule_data.get("days", {}).get(yesterday_key, []):
        if slot.get("overnight"):
            e_min = parse_time_str(slot["end"])
            if e_min is not None and current_minutes < e_min:
                mins_left = e_min - current_minutes
                return {
                    "open": True,
                    "status_label": "Closing Soon" if mins_left <= 30 else "Open Now",
                    "next_change": f"Closes at {slot['end']} (in {mins_left}m)",
                    "current_slot": slot
                }

    # Check 2: Active slot today
    today_slots = schedule_data.get("days", {}).get(today_key, [])
    for slot in today_slots:
        s_min = parse_time_str(slot["start"])
        e_min = parse_time_str(slot["end"])
        if s_min is None or e_min is None:
            continue

        if slot.get("overnight"):
            # e.g. 17:00 - 02:00. Today's part is current_minutes >= 17:00
            if current_minutes >= s_min:
                return {
                    "open": True,
                    "status_label": "Open Late",
                    "next_change": f"Closes at {slot['end']}",
                    "current_slot": slot
                }
        else:
            if s_min <= current_minutes < e_min:
                mins_left = e_min - current_minutes
                return {
                    "open": True,
                    "status_label": "Closing Soon" if mins_left <= 30 else "Open Now",
                    "next_change": f"Closes at {slot['end']} ({mins_left}m left)",
                    "current_slot": slot
                }

    # If closed, find when it next opens
    for slot in today_slots:
        s_min = parse_time_str(slot["start"])
        if s_min is not None and current_minutes < s_min:
            mins_until = s_min - current_minutes
            return {
                "open": False,
                "status_label": "Closed",
                "next_change": f"Opens today at {slot['start']} (in {mins_until // 60}h {mins_until % 60}m)",
                "current_slot": None
            }

    tomorrow_key = DAY_NAMES[(weekday + 1) % 7]
    tomorrow_slots = schedule_data.get("days", {}).get(tomorrow_key, [])
    if tomorrow_slots:
        return {
            "open": False,
            "status_label": "Closed for the day",
            "next_change": f"Opens tomorrow at {tomorrow_slots[0]['start']}",
            "current_slot": None
        }

    return {
        "open": False,
        "status_label": "Closed",
        "next_change": "Check schedule",
        "current_slot": None
    }
