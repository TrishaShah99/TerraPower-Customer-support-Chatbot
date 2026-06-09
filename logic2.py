# logic2.py – Improved Version with Full Flows + Contact Collection
# TerraPower Electric ATV Support Logic Engine

from database2 import create_ticket, get_service_centers_by_city
import re
from datetime import datetime, date

SESSION_STATE = {}

FAKE_CENTERS = {
    "pune": [
        {"name": "TerraPower Service – Pune East", "address": "Survey 88, Magarpatta Road, Pune", "phone": "7722001122"},
        {"name": "TerraPower Workshop – Pune West", "address": "Baner Highway Side Lane, Pune", "phone": "7722002211"},
    ],
    "ahmedabad": [
        {"name": "TerraPower Care – Ahmedabad Central", "address": "SG Highway, Opp. City Mall, Ahmedabad", "phone": "8899776611"},
        {"name": "TerraPower EV Hub – Ahmedabad", "address": "Bodakdev Road, Ahmedabad", "phone": "8899776622"},
    ],
    "hyderabad": [
        {"name": "TerraPower Service – Hyderabad", "address": "Kondapur Main Road, Hyderabad", "phone": "9090887766"},
        {"name": "TerraPower EV Workshop – Hyderabad", "address": "Banjara Hills Road 12, Hyderabad", "phone": "9090887799"},
    ],
    "indore": [
        {"name": "TerraPower Care – Indore", "address": "Vijay Nagar Square, Indore", "phone": "8811223344"},
        {"name": "TerraPower EV Center – Indore", "address": "AB Road, Near Palasia, Indore", "phone": "8811223355"},
    ]
}

AVAILABLE_CITIES = ["Pune", "Ahmedabad", "Hyderabad", "Indore"]


def _get_state(session_id):
    if session_id not in SESSION_STATE:
        SESSION_STATE[session_id] = {"flow": None, "step": None, "data": {}, "last_intent": None}
    return SESSION_STATE[session_id]


def _reset_state(session_id):
    SESSION_STATE[session_id] = {"flow": None, "step": None, "data": {}, "last_intent": None}


def _title_case_city(c: str) -> str:
    if not c:
        return ""
    return c.strip().title()


def _set_home_quick_replies(result):
    result["quick_replies"] = [
        "Book a Service Appointment",
        "Show Nearby Service Centers",
        "Warranty Query",
        "Battery Not Charging",
        "Vehicle Not Starting",
        "Low Power Issue",
        "Brake Issue",
        "Spare Parts Query"
    ]


def _cities_list_html():
    # Show available cities and sample service centers (from FAKE_CENTERS)
    msg = "<b>Service currently available in:</b><br>"
    for city in AVAILABLE_CITIES:
        msg += f"• <b>{city}</b><br>"
    msg += "<br>You can reply with one of these city names."
    return msg


def _handle_city_not_available(result, city_text):
    city = _title_case_city(city_text)
    result["reply"] = (
        f"Sorry, service is not available in <b>{city}</b> right now.<br><br>"
        f"{_cities_list_html()}"
    )
    result["needs_city"] = True
    result["quick_replies"] = AVAILABLE_CITIES[:]  # quick choices
    return result


# ---------------------- CONTACT COLLECTION (GLOBAL) ---------------------- #

def _start_contact_collection(session_id, result, category: str, description: str, success_title: str = "Ticket Created"):
    """
    Instead of directly creating a ticket, route user into a single shared flow:
    Collect Name -> Collect Phone -> Create Ticket.
    """
    state = _get_state(session_id)
    state["flow"] = "collect_contact"
    state["step"] = "name"
    state["data"] = {
        "pending_ticket": {
            "category": category,
            "description": description,
            "success_title": success_title
        }
    }

    result["intent"] = "collect_contact"
    result["ticket_created"] = False
    result["ticket_id"] = None
    result["service_centers"] = result.get("service_centers", [])
    result["needs_city"] = False

    result["reply"] = (
        "To create your support ticket, please share a few details.<br><br>"
        "1️⃣ What is your <b>full name</b>?"
    )
    result["quick_replies"] = []
    return result


def _is_valid_name(name: str) -> bool:
    if not name:
        return False
    n = re.sub(r"\s+", " ", name.strip())
    if len(n) < 2:
        return False
    # allow letters, spaces, dot
    return bool(re.match(r"^[A-Za-z.\s]{2,60}$", n))


def _extract_phone_digits(text: str) -> str:
    # Extract digits and keep last 10 (common for +91)
    digits = re.sub(r"\D", "", text or "")
    if len(digits) >= 10:
        return digits[-10:]
    return digits


def _is_valid_indian_phone(phone10: str) -> bool:
    # Basic validation for Indian mobile: 10 digits, starts 6-9
    return bool(re.match(r"^[6-9]\d{9}$", phone10 or ""))


def _flow_collect_contact(text, session_id, result):
    state = _get_state(session_id)
    step = state["step"]
    data = state["data"]

    result["intent"] = "collect_contact"

    if step == "name":
        name = (text or "").strip()
        if not _is_valid_name(name):
            result["reply"] = (
                "Please enter a valid <b>name</b> (letters only).<br>"
                "Example: <b>Rahul Sharma</b>"
            )
            return result

        data["name"] = re.sub(r"\s+", " ", name)
        state["step"] = "phone"
        result["reply"] = (
            f"Thanks, <b>{data['name']}</b>.<br><br>"
            "2️⃣ Please share your <b>phone number</b> (10 digits).<br>"
            "Example: <b>9876543210</b>"
        )
        return result

    if step == "phone":
        phone10 = _extract_phone_digits(text)
        if not _is_valid_indian_phone(phone10):
            result["reply"] = (
                "Please enter a valid <b>10-digit</b> phone number.<br>"
                "Example: <b>9876543210</b>"
            )
            return result

        data["phone"] = phone10

        pending = data.get("pending_ticket", {})
        category = pending.get("category", "General Issue")
        desc = pending.get("description", "").strip()
        success_title = pending.get("success_title", "Ticket Created")

        # Append contact info in description (no DB schema changes required)
        desc_full = f"{desc} | Name: {data.get('name','')} | Phone: {data.get('phone','')}"

        ticket_id = create_ticket(session_id, category, desc_full)

        # Finalize response
        result["reply"] = f"Creating <b>{category}</b> ticket..."
        result["secondary_reply"] = (
            f"✅ <b>{success_title}</b><br>"
            f"Ticket ID: <b>TP-{ticket_id:05d}</b><br>"
            f"Name: <b>{data.get('name','')}</b><br>"
            f"Phone: <b>{data.get('phone','')}</b><br>"
            "Our service team will contact you soon."
        )
        result["ticket_created"] = True
        result["ticket_id"] = f"TP-{ticket_id:05d}"

        _reset_state(session_id)
        _set_home_quick_replies(result)
        return result

    # fallback
    _reset_state(session_id)
    result["reply"] = "Let's start again. Type <b>Raise ticket</b> or select an option."
    _set_home_quick_replies(result)
    return result


# ------------- INTENT CLASSIFICATION ---------------- #

def _classify_intent(text: str) -> str:
    t = text.lower().strip()

    if t == "__reset__":
        return "__reset__"

    if t in ["hi", "hello", "hey"]:
        return "greeting"

    if (
        "vehicle not starting" in t
        or "not starting" in t
        or "won't start" in t
        or "wont start" in t
        or "engine not starting" in t
        or ("vehicle" in t and "start" in t)
    ):
        return "vehicle_not_starting"

    if (
        "not charging" in t
        or "won't charge" in t
        or "wont charge" in t
        or "charging issue" in t
        or ("charger" in t and "problem" in t)
    ):
        return "battery_charging_issue"

    if any(w in t for w in ["low power", "no power", "slow", "pickup", "not pulling", "performance"]):
        return "low_power_issue"

    # 🔧 FIX: Recognize "Brake Issue" button text as brake flow too
    if (
        ("brake" in t and any(w in t for w in ["soft", "spongy", "weak", "hard", "very hard", "not working"]))
        or "brake issue" in t
        or "brake issues" in t
        or "brake problem" in t
    ):
        return "brake_issue"

    if ("display" in t or "screen" in t) and any(w in t for w in ["not turning on", "off", "blank", "dead"]):
        return "display_issue"

    if any(w in t for w in ["book service", "book a service", "service appointment", "schedule service"]):
        return "book_service"

    if "service center" in t or "service centre" in t or "nearby service" in t or "nearby center" in t:
        return "service_center_info"

    if "ticket" in t or "raise complaint" in t or "raise query" in t:
        return "raise_ticket"

    if "warranty" in t:
        return "warranty_query"

    if "spare" in t or "spares" in t or "spare part" in t:
        return "spare_parts_query"

    if "top speed" in t or "max speed" in t:
        return "top_speed_info"

    if any(w in t for w in ["price", "cost", "range"]):
        return "sales_redirect"

    if any(w in t for w in ["agent", "human", "contact", "call"]):
        return "human_contact"

    return "general_help"


# ------------- MAIN MESSAGE HANDLER ---------------- #

def handle_message(message: str, session_id: str):
    text = (message or "").strip()
    state = _get_state(session_id)

    # special reset
    if text.lower() == "__reset__":
        _reset_state(session_id)
        return {
            "reply": (
                "Hey! I’m Terra, your TerraPower electric ATV support assistant. 🚙⚡<br><br>"
                "I can help you with:<br>"
                "• Vehicle not starting<br>"
                "• Battery & charging issues<br>"
                "• Performance (low power) issues<br>"
                "• Brake issues<br>"
                "• Display not turning on<br>"
                "• Book a service<br>"
                "• Warranty & spare parts<br>"
                "• Service centers & ticket status<br><br>"
                "How can I help you today?"
            ),
            "quick_replies": [
                "Book a Service Appointment",
                "Show Nearby Service Centers",
                "Warranty Query",
                "Battery Not Charging",
                "Vehicle Not Starting",
                "Low Power Issue",
                "Brake Issue",
                "Spare Parts Query"
            ],
            "secondary_reply": None,
            "ticket_created": False,
            "ticket_id": None,
            "service_centers": [],
            "needs_city": False,
            "intent": "greeting",
        }

    # base result structure – always return all keys
    result = {
        "reply": "",
        "secondary_reply": None,
        "intent": None,
        "ticket_created": False,
        "ticket_id": None,
        "quick_replies": [],
        "needs_city": False,
        "service_centers": []
    }

    # ✅✅✅ FIX ADDED (ONLY CHANGE IN ENTIRE FILE)
    # If bot is waiting for CITY, do NOT re-classify intent.
    # Route the user input directly to the correct ongoing flow.
    if state.get("step") == "city" and state.get("flow"):
        if state["flow"] == "service_booking":
            return _flow_service_booking(text, session_id, result)
        if state["flow"] == "service_centers_lookup":
            return _flow_service_centers(text, session_id, result)
        if state["flow"] == "ticket_creation":
            return _flow_ticket(text, session_id, result)
        if state["flow"] == "spare_parts":
            return _flow_spare_parts(text, session_id, result)
    # ✅✅✅ END FIX

    # Continue ongoing flow
    if state["flow"] == "collect_contact":
        return _flow_collect_contact(text, session_id, result)

    if state["flow"] == "vehicle_not_starting":
        return _flow_not_starting(text, session_id, result)
    if state["flow"] == "battery_charging_issue":
        return _flow_charging(text, session_id, result)
    if state["flow"] == "low_power_issue":
        return _flow_low_power(text, session_id, result)
    if state["flow"] == "brake_issue":
        return _flow_brake(text, session_id, result)
    if state["flow"] == "display_issue":
        return _flow_display(text, session_id, result)
    if state["flow"] == "ticket_creation":
        return _flow_ticket(text, session_id, result)
    if state["flow"] == "service_booking":
        return _flow_service_booking(text, session_id, result)
    if state["flow"] == "service_centers_lookup":
        return _flow_service_centers(text, session_id, result)
    if state["flow"] == "spare_parts":
        return _flow_spare_parts(text, session_id, result)

    # New intent
    intent = _classify_intent(text)
    result["intent"] = intent
    state["last_intent"] = intent

    # GREETING
    if intent == "greeting":
        result["reply"] = (
            "Hey! I’m Terra, your TerraPower electric ATV support assistant. 🚙⚡<br><br>"
            "I can help you with:<br>"
            "• Vehicle not starting<br>"
            "• Battery & charging issues<br>"
            "• Performance (low power) issues<br>"
            "• Brake issues<br>"
            "• Display not turning on<br>"
            "• Book a service<br>"
            "• Warranty & spare parts<br>"
            "• Service centers & ticket status<br><br>"
            "How can I help you today?"
        )
        _set_home_quick_replies(result)
        return result

    # VEHICLE NOT STARTING
    if intent == "vehicle_not_starting":
        state["flow"] = "vehicle_not_starting"
        state["step"] = "hv_status"
        state["data"] = {}
        result["reply"] = (
            "Let's troubleshoot why your TerraPower ATV is <b>not starting</b>.<br><br>"
            "1️⃣ First, check the <b>HV / TSAL indicator</b> on the dash.<br>"
            "Is the <b>TSAL / HV light ON</b> when you turn the key ON?<br><br>"
            "Reply with <b>YES</b> or <b>NO</b>."
        )
        result["quick_replies"] = ["YES – TSAL ON", "NO – TSAL OFF"]
        return result

    # BATTERY / CHARGING ISSUE
    if intent == "battery_charging_issue":
        state["flow"] = "battery_charging_issue"
        state["step"] = "ac_socket"
        state["data"] = {}
        result["reply"] = (
            "Okay, let's check your <b>battery / charging issue</b> step by step.<br><br>"
            "1️⃣ First, <b>check the AC wall socket</b> using another device (like a phone charger).<br>"
            "Is the <b>AC socket working properly</b>?<br><br>"
            "Reply <b>YES</b> or <b>NO</b>."
        )
        result["quick_replies"] = ["YES – AC Socket OK", "NO – AC Socket Problem"]
        return result

    # LOW POWER / PERFORMANCE ISSUE
    if intent == "low_power_issue":
        state["flow"] = "low_power_issue"
        state["step"] = "soc"
        state["data"] = {}
        result["reply"] = (
            "You're facing a <b>performance / low power issue</b>.<br><br>"
            "1️⃣ What is the current <b>battery SoC</b> (approx)?<br>"
            "Reply like <b>80%</b>, <b>40%</b>, or <b>below 20%</b>."
        )
        return result

    # BRAKE ISSUE
    if intent == "brake_issue":
        state["flow"] = "brake_issue"
        state["step"] = "symptom_detail"
        state["data"] = {}
        result["reply"] = (
            "You mentioned a <b>brake issue</b>.<br><br>"
            "Please describe it briefly, for example:<br>"
            "• Lever feels soft / spongy<br>"
            "• Very weak braking<br>"
            "• Noise or vibration while braking<br><br>"
            "Type a short description."
        )
        return result

    # DISPLAY ISSUE
    if intent == "display_issue":
        state["flow"] = "display_issue"
        state["step"] = "hv_status"
        state["data"] = {}
        result["reply"] = (
            "Your <b>display is not turning ON</b>.<br><br>"
            "When you turn the key ON:<br>"
            "👉 Is the <b>TSAL / HV indicator</b> ON?<br><br>"
            "Reply <b>YES</b> or <b>NO</b>."
        )
        result["quick_replies"] = ["YES – TSAL ON", "NO – TSAL OFF"]
        return result

    # SERVICE BOOKING
    if intent == "book_service":
        state["flow"] = "service_booking"
        state["step"] = "city"
        state["data"] = {}
        result["reply"] = (
            "Sure, let's <b>book a service appointment</b>.<br><br>"
            "📍 Please tell me your <b>city</b> (example: Pune, Mumbai, Bengaluru)."
        )
        result["needs_city"] = True
        return result

    # RAISE TICKET (manual)
    if intent == "raise_ticket":
        state["flow"] = "ticket_creation"
        state["step"] = "issue"
        state["data"] = {}
        result["reply"] = (
            "Okay! Please type a short description of the <b>issue</b> you want to raise a ticket for."
        )
        return result

    # SERVICE CENTERS QUERY (nearby)
    if intent == "service_center_info":
        state["flow"] = "service_centers_lookup"
        state["step"] = "city"
        state["data"] = {}
        result["reply"] = (
            "Tell me your <b>city name</b>, and I’ll show the nearest TerraPower service centers."
        )
        result["needs_city"] = True
        return result

    # WARRANTY
    if intent == "warranty_query":
        result["reply"] = (
            "<b>TerraPower ATV – Warranty Overview</b><br><br>"
            "• Battery & BMS – limited period / cycle warranty<br>"
            "• PMSM motor & controller – manufacturing defects only<br>"
            "• Frame / chassis – structural warranty<br><br>"
            "If you want, I can raise a <b>warranty ticket</b> for your issue."
        )
        result["quick_replies"] = ["Raise Warranty Ticket", "Show Nearby Service Centers", "Book a Service Appointment"]
        return result

    # SPARE PARTS
    if intent == "spare_parts_query":
        state["flow"] = "spare_parts"
        state["step"] = "part"
        state["data"] = {}
        result["reply"] = (
            "We can help with <b>spare parts</b> like brake pads, lights, TSAL indicator, display unit, plastics, etc.<br><br>"
            "👉 Please type the <b>spare part name</b> you need (for example: rear brake pads, TSAL indicator, display)."
        )
        return result

    # TOP SPEED
    if intent == "top_speed_info":
        result["reply"] = (
            "The TerraPower electric ATV is tuned for a <b>60–75 km/h</b> top speed.<br>"
            "It focuses on <b>high torque and control</b> rather than pure top speed."
        )
        _set_home_quick_replies(result)
        return result

    # SALES REDIRECT
    if intent == "sales_redirect":
        result["reply"] = (
            "For <b>price, range, or offers</b>, please contact our sales team:<br>"
            "📞 <b>8788-9400</b><br><br>"
            "Or visit the TerraPower website."
        )
        _set_home_quick_replies(result)
        return result

    # HUMAN CONTACT
    if intent == "human_contact":
        result["reply"] = (
            "You can speak with a human support agent at:<br>"
            "📞 <b>8788-9400</b> (Call or WhatsApp)<br><br>"
            "Meanwhile, I can still troubleshoot or raise a ticket for you."
        )
        _set_home_quick_replies(result)
        return result

    # GENERAL HELP
    result["reply"] = (
        "I'm here to help with your TerraPower ATV. 💬<br><br>"
        "You can say:<br>"
        "• Vehicle not starting<br>"
        "• Battery not charging<br>"
        "• Low power issue<br>"
        "• Brake issue<br>"
        "• Display not turning on<br>"
        "• Book service<br>"
        "• Raise ticket"
    )
    _set_home_quick_replies(result)
    return result


# ---------------------- VEHICLE NOT STARTING FLOW ---------------------- #

def _flow_not_starting(text, session_id, result):
    state = _get_state(session_id)
    step = state["step"]
    t = text.lower()

    result["intent"] = "vehicle_not_starting"

    # STEP 1 — HV / TSAL status
    if step == "hv_status":
        if "yes" in t:
            state["step"] = "lv_status"
            result["reply"] = (
                "✅ HV / TSAL light is <b>ON</b>.<br><br>"
                "2️⃣ Now check the <b>LV / 12V indicator</b> on your vehicle (if available).<br>"
                "Is the <b>LV indicator ON</b>?<br><br>"
                "Reply <b>YES</b> or <b>NO</b>."
            )
            result["quick_replies"] = ["YES – LV ON", "NO – LV OFF"]
            return result

        elif "no" in t:
            # HV OFF
            state["step"] = "hv_retry_ticket"
            result["reply"] = (
                "⚠ HV / TSAL light is <b>OFF</b>.<br><br>"
                "1️⃣ Try a full restart:<br>"
                "• Turn key OFF<br>"
                "• Wait 30 seconds<br>"
                "• Turn key ON again and check TSAL<br><br>"
                "If it still does not come ON, the HV system is not enabling correctly.<br><br>"
                "If the problem still persists, reply <b>YES</b> and I will raise a "
                "<b>Vehicle Not Starting</b> ticket. Otherwise reply <b>NO</b>."
            )
            result["quick_replies"] = ["YES – Raise Ticket", "NO – Don't Raise Ticket"]
            return result

        else:
            result["reply"] = "Please reply with <b>YES</b> or <b>NO</b> about the TSAL / HV indicator."
            return result

    # STEP 2 — HV ON, check LV
    if step == "lv_status":
        if "yes" in t:
            state["step"] = "brake_light"
            result["reply"] = (
                "✅ Both <b>HV</b> and <b>LV</b> seem ON.<br><br>"
                "3️⃣ Please check the <b>brake light</b> at the rear when you press the brake lever / pedal.<br>"
                "Is the <b>brake light working</b>?<br><br>"
                "Reply <b>YES</b> or <b>NO</b>."
            )
            result["quick_replies"] = ["YES – Brake Light Working", "NO – Brake Light Not Working"]
            return result

        elif "no" in t:
            # LV OFF
            state["step"] = "lv_change_battery_ticket"
            result["reply"] = (
                "⚠ <b>LV indicator is OFF</b> while HV is ON.<br><br>"
                "This points to a <b>low-voltage supply problem</b> (12V battery or LV wiring).<br>"
                "👉 Try checking / changing the LV battery if accessible.<br><br>"
                "If the issue still persists, reply <b>YES</b> and I will raise a ticket for you."
            )
            result["quick_replies"] = ["YES – Raise Ticket", "NO – Don't Raise Ticket"]
            return result

        else:
            result["reply"] = "Please reply with <b>YES</b> or <b>NO</b> about the LV indicator."
            return result

    # STEP 3 — Brake light check
    if step == "brake_light":
        if "yes" in t:
            state["step"] = "tsal_rtds"
            result["reply"] = (
                "✅ Brake light is working.<br><br>"
                "4️⃣ When you try to start:<br>"
                "• Is <b>TSAL ON</b>?<br>"
                "• Is the <b>Ready To Drive Sound (RTDS)</b> coming?<br><br>"
                "Reply <b>YES</b> if both TSAL and RTDS are ON, else reply <b>NO</b>."
            )
            result["quick_replies"] = ["YES – TSAL & RTDS ON", "NO – One of them OFF"]
            return result

        elif "no" in t:
            state["step"] = "brake_light_ticket"
            result["reply"] = (
                "⚠ <b>Brake light is not working</b>.<br><br>"
                "This can prevent the start sequence from completing.<br>"
                "👉 Try restarting the vehicle once.<br><br>"
                "If the issue still persists, reply <b>YES</b> and I will raise a ticket for brake / LV diagnosis."
            )
            result["quick_replies"] = ["YES – Raise Ticket", "NO – Don't Raise Ticket"]
            return result

        else:
            result["reply"] = "Please reply with <b>YES</b> or <b>NO</b> about the brake light."
            return result

    # STEP 4 — TSAL + RTDS check
    if step == "tsal_rtds":
        if "yes" in t:
            # Problem in start sequence / procedure
            state["step"] = "start_sequence_ticket"
            result["reply"] = (
                "TSAL and RTDS are ON, but the vehicle is still <b>not starting</b>.<br><br>"
                "This usually means an issue with the <b>start sequence</b>.<br><br>"
                "✅ Please try this:<br>"
                "• Ensure vehicle is in <b>neutral / no throttle</b><br>"
                "• Press and hold <b>brake</b><br>"
                "• While holding brake, press <b>Start / Stop</b><br>"
                "• Do <b>not</b> press throttle while starting<br><br>"
                "If the problem still persists after trying the proper sequence, reply <b>YES</b> "
                "and I will raise a Vehicle Not Starting ticket."
            )
            result["quick_replies"] = ["YES – Raise Ticket", "NO – Don't Raise Ticket"]
            return result

        elif "no" in t:
            state["step"] = "tsal_rtds_off_ticket"
            result["reply"] = (
                "Either <b>TSAL</b> or <b>RTDS</b> is not coming when you try to start.<br><br>"
                "This indicates an issue in the <b>power-up or interlock chain</b>.<br><br>"
                "If the issue persists, reply <b>YES</b> and I will raise a full start-sequence diagnosis ticket."
            )
            result["quick_replies"] = ["YES – Raise Ticket", "NO – Don't Raise Ticket"]
            return result

        else:
            result["reply"] = "Please reply <b>YES</b> or <b>NO</b>."
            return result

    # TICKET CONFIRM STEPS
    if step in ["hv_retry_ticket", "lv_change_battery_ticket",
                "brake_light_ticket", "start_sequence_ticket",
                "tsal_rtds_off_ticket"]:
        if t.startswith("y"):
            # build description by step
            if step == "hv_retry_ticket":
                desc = "Vehicle not starting – TSAL/HV indicator OFF even after restart."
            elif step == "lv_change_battery_ticket":
                desc = "Vehicle not starting – HV ON, LV OFF (possible LV battery / wiring issue)."
            elif step == "brake_light_ticket":
                desc = "Vehicle not starting – Brake light not working (interlock issue)."
            elif step == "start_sequence_ticket":
                desc = "Vehicle not starting – TSAL + RTDS ON, start sequence not completing."
            else:
                desc = "Vehicle not starting – TSAL/RTDS abnormal, start sequence issue."

            # Route to contact collection instead of creating immediately
            return _start_contact_collection(
                session_id,
                result,
                category="Vehicle Not Starting",
                description=desc,
                success_title="Ticket Created"
            )
        else:
            _reset_state(session_id)
            result["reply"] = (
                "Okay, I won't create a ticket right now.<br>"
                "If the vehicle still does not start, you can type <b>Vehicle not starting</b> again "
                "or call support at <b>8788-9400</b>."
            )
            _set_home_quick_replies(result)
            return result

    # fallback
    _reset_state(session_id)
    result["reply"] = "To restart, type <b>Vehicle not starting</b>."
    _set_home_quick_replies(result)
    return result
# ---------------------- BATTERY / CHARGING ISSUE FLOW ---------------------- #

def _flow_charging(text, session_id, result):
    state = _get_state(session_id)
    step = state["step"]
    t = text.lower()
    data = state["data"]

    result["intent"] = "battery_charging_issue"

    # STEP 1 — AC socket check
    if step == "ac_socket":
        if "no" in t:
            state["step"] = "ac_socket_ticket"
            result["reply"] = (
                "⚠ It looks like the <b>AC socket itself is not reliable</b>.<br><br>"
                "Please try a different wall socket or get the supply checked by an electrician.<br><br>"
                "If you still face charging issues even with a good AC socket, reply <b>YES</b> "
                "and I will raise a charging issue ticket. Otherwise reply <b>NO</b>."
            )
            result["quick_replies"] = ["YES – Raise Ticket", "NO – Don't Raise Ticket"]
            return result

        elif "yes" in t:
            state["step"] = "charger_led"
            result["reply"] = (
                "✅ AC socket seems fine.<br><br>"
                "2️⃣ Now look at the <b>charger itself</b>.<br>"
                "Is the <b>charger LED ON or blinking</b> when it is plugged in?<br><br>"
                "Reply <b>YES</b> or <b>NO</b>."
            )
            result["quick_replies"] = ["YES – Charger LED ON/Blipping", "NO – No LED / Dead"]
            return result

        else:
            result["reply"] = "Please reply with <b>YES</b> or <b>NO</b> about the AC socket."
            return result

    # STEP 2 — Charger LED status
    if step == "charger_led":
        if "no" in t:
            # Charger dead
            state["step"] = "charger_dead_ticket"
            result["reply"] = (
                "⚠ The <b>charger LED is not ON</b> – this usually means the <b>charger is dead</b> "
                "or not powering up correctly.<br><br>"
                "You should visit a TerraPower service center and get the charger checked / replaced.<br><br>"
                "If you want, reply <b>YES</b> and I will raise a <b>Charger Dead</b> ticket for you. "
                "Otherwise reply <b>NO</b>."
            )
            result["quick_replies"] = ["YES – Raise Ticket", "NO – Don't Raise Ticket"]
            return result

        elif "yes" in t:
            state["step"] = "app_detect"
            result["reply"] = (
                "✅ Charger LED is ON / blinking.<br><br>"
                "3️⃣ Now check the <b>display</b> and the <b>Terra app</b> (if connected).<br>"
                "Is the charging status / parameters being <b>detected correctly</b> "
                "(voltage, SoC, charging icon etc.)?<br><br>"
                "Reply <b>YES</b> if it looks correct, or <b>NO</b> if it is not detected / looks wrong."
            )
            result["quick_replies"] = ["YES – Detected Correctly", "NO – Not Detected / Wrong"]
            return result

        else:
            result["reply"] = "Please reply <b>YES</b> or <b>NO</b> about the charger LED."
            return result

    # STEP 3 — App / display detection
    if step == "app_detect":
        if "no" in t:
            state["step"] = "app_detect_ticket"
            result["reply"] = (
                "⚠ Charging is <b>not being detected correctly</b> by the display / app.<br><br>"
                "This is likely a <b>communication or BMS issue</b>.<br><br>"
                "Please contact service support, or reply <b>YES</b> and I will raise a "
                "<b>Charging Detection / BMS</b> ticket for you. Reply <b>NO</b> to skip."
            )
            result["quick_replies"] = ["YES – Raise Ticket", "NO – Don't Raise Ticket"]
            return result

        elif "yes" in t:
            # Store this info and go to parameter check
            data["detected_ok"] = True
            state["step"] = "parameters"
            result["reply"] = (
                "Charging is being <b>detected correctly</b>, but you still feel it's <b>not charging properly</b>.<br><br>"
                "4️⃣ Please check key <b>parameters</b> on the display / app:<br>"
                "• Battery temperature<br>"
                "• Battery voltage<br><br>"
                "If <b>temperature is very high (around 150°C)</b>, allow the battery to cool down before charging again.<br>"
                "If voltage is <b>undervoltage</b> (too low), ensure you are using proper AC supply and original charger.<br><br>"
                "After checking this, reply <b>YES</b> if you have already tried all this and issue still persists, "
                "or <b>NO</b> if you will try once (for example, overnight charging)."
            )
            result["quick_replies"] = ["YES – Tried, Still Problem", "NO – Will Try and Monitor"]
            return result

        else:
            result["reply"] = "Please reply <b>YES</b> or <b>NO</b> about the app / display detection."
            return result

    # STEP 4 — Parameter based final step
    if step == "parameters":
        if "no" in t:
            _reset_state(session_id)
            result["reply"] = (
                "Alright. Try the suggestions:<br>"
                "• Allow cooldown if temperature is high<br>"
                "• Ensure correct AC supply and original charger<br>"
                "• Try an <b>overnight charging session</b><br><br>"
                "If the problem still persists later, you can type <b>Battery not charging</b> again or call support at <b>8788-9400</b>."
            )
            _set_home_quick_replies(result)
            return result

        elif "yes" in t:
            # Offer ticket
            state["step"] = "parameters_ticket"
            result["reply"] = (
                "Understood – charging issue persists even after checking temperature, voltage and trying proper supply.<br><br>"
                "If you want, reply <b>YES</b> and I will raise a detailed <b>Charging Issue</b> ticket. "
                "Reply <b>NO</b> to skip."
            )
            result["quick_replies"] = ["YES – Raise Ticket", "NO – Don't Raise Ticket"]
            return result

        else:
            result["reply"] = "Please reply <b>YES</b> or <b>NO</b>."
            return result

    # TICKET CONFIRM STEPS
    if step in ["ac_socket_ticket", "charger_dead_ticket",
                "app_detect_ticket", "parameters_ticket"]:
        if t.startswith("y"):
            if step == "ac_socket_ticket":
                desc = "Charging issue – AC socket checked / changed, still not charging."
                cat = "Battery / Charging Issue"
            elif step == "charger_dead_ticket":
                desc = "Charging issue – Charger LED OFF, suspected dead charger."
                cat = "Battery / Charging Issue"
            elif step == "app_detect_ticket":
                desc = "Charging issue – display/app not detecting charging correctly."
                cat = "Battery / Charging Issue"
            else:
                desc = "Charging issue – parameters checked (temp/voltage), still not charging."
                cat = "Battery / Charging Issue"

            return _start_contact_collection(
                session_id,
                result,
                category=cat,
                description=desc,
                success_title="Ticket Created"
            )
        else:
            _reset_state(session_id)
            result["reply"] = (
                "Okay, I won't create a ticket right now.<br>"
                "If the charging problem continues, you can type <b>Battery not charging</b> again "
                "or contact support at <b>8788-9400</b>."
            )
            _set_home_quick_replies(result)
            return result

    # fallback
    _reset_state(session_id)
    result["reply"] = "To restart charging help, type <b>Battery not charging</b>."
    _set_home_quick_replies(result)
    return result
# ---------------------- LOW POWER / PERFORMANCE ISSUE FLOW ---------------------- #

def _flow_low_power(text, session_id, result):
    state = _get_state(session_id)
    step = state["step"]
    t = text.lower()
    data = state["data"]

    result["intent"] = "low_power_issue"

    # STEP 1 — Battery SoC
    if step == "soc":
        # Extract percentage if provided
        percent = None
        m = re.search(r"(\d{1,3})\s*%", t)
        if m:
            percent = int(m.group(1))

        if percent is not None:
            data["soc"] = percent
            if percent < 20:
                state["step"] = "low_soc_advice"
                result["reply"] = (
                    f"🔋 Your battery SoC is around <b>{percent}%</b>, which is quite low.<br><br>"
                    "At low SoC, the vehicle automatically limits power to protect the battery.<br><br>"
                    "👉 Please fully <b>charge the vehicle</b> and try again.<br><br>"
                    "If you still face low power even after full charge, reply <b>YES</b> and I will raise a ticket."
                )
                result["quick_replies"] = ["YES – Raise Ticket", "NO – Will Charge First"]
                state["step"] = "low_soc_ticket"
                return result
            else:
                state["step"] = "mode_check"
                result["reply"] = (
                    f"Battery SoC is around <b>{percent}%</b>, which should be sufficient.<br><br>"
                    "2️⃣ Please check the <b>drive mode</b> on your ATV.<br>"
                    "Is it currently in <b>ECO / LOW power mode</b>?<br><br>"
                    "Reply <b>YES</b> or <b>NO</b>."
                )
                result["quick_replies"] = ["YES – In ECO Mode", "NO – In Normal/Power Mode"]
                return result

        else:
            result["reply"] = (
                "Please reply with an approximate <b>battery percentage</b>.<br>"
                "Example: <b>80%</b>, <b>45%</b>, <b>15%</b>."
            )
            return result

    # STEP 2 — Drive mode check
    if step == "mode_check":
        if "yes" in t:
            state["step"] = "eco_mode_advice"
            result["reply"] = (
                "Your ATV is currently in <b>ECO / LOW power mode</b>.<br><br>"
                "👉 Switch to <b>Normal / Power mode</b> and test the performance again.<br><br>"
                "If you still face low power after switching modes, reply <b>YES</b> and I will raise a ticket."
            )
            result["quick_replies"] = ["YES – Still Low Power", "NO – Issue Resolved"]
            state["step"] = "eco_mode_ticket"
            return result

        elif "no" in t:
            state["step"] = "brake_drag"
            result["reply"] = (
                "Okay, drive mode seems fine.<br><br>"
                "3️⃣ Please check if the vehicle feels like it is <b>dragging</b> or "
                "<b>slowing down abnormally</b> even without throttle.<br><br>"
                "This can happen due to <b>brake drag</b> or mechanical resistance.<br><br>"
                "Do you feel any abnormal drag? Reply <b>YES</b> or <b>NO</b>."
            )
            result["quick_replies"] = ["YES – Feels Dragging", "NO – Feels Normal"]
            return result

        else:
            result["reply"] = "Please reply <b>YES</b> or <b>NO</b> about the drive mode."
            return result

    # STEP 3 — Brake drag check
    if step == "brake_drag":
        if "yes" in t:
            state["step"] = "brake_drag_ticket"
            result["reply"] = (
                "⚠ The vehicle feels like it is <b>dragging</b>.<br><br>"
                "This often indicates <b>brake binding</b> or mechanical resistance.<br><br>"
                "It is recommended to get the brakes inspected at a service center.<br><br>"
                "If you want, reply <b>YES</b> and I will raise a <b>Low Power / Brake Drag</b> ticket for you."
            )
            result["quick_replies"] = ["YES – Raise Ticket", "NO – Don't Raise Ticket"]
            return result

        elif "no" in t:
            state["step"] = "thermal_limit"
            result["reply"] = (
                "Okay, no brake drag detected.<br><br>"
                "4️⃣ Have you noticed the vehicle reducing power after <b>continuous riding</b>, "
                "especially in hot conditions?<br><br>"
                "This could be due to <b>thermal limiting</b> of battery or motor.<br><br>"
                "Reply <b>YES</b> or <b>NO</b>."
            )
            result["quick_replies"] = ["YES – After Long Ride", "NO – Happens Always"]
            return result

        else:
            result["reply"] = "Please reply <b>YES</b> or <b>NO</b>."
            return result

    # STEP 4 — Thermal limiting check
    if step == "thermal_limit":
        if "yes" in t:
            state["step"] = "thermal_advice"
            result["reply"] = (
                "⚠ This sounds like <b>thermal power limiting</b>.<br><br>"
                "When battery or motor temperature rises too much, the system reduces power to protect components.<br><br>"
                "👉 Allow the vehicle to <b>cool down</b> for 15–20 minutes and try again.<br><br>"
                "If low power still persists even after cooldown, reply <b>YES</b> and I will raise a ticket."
            )
            result["quick_replies"] = ["YES – Raise Ticket", "NO – Will Monitor"]
            state["step"] = "thermal_ticket"
            return result

        elif "no" in t:
            state["step"] = "low_power_general_ticket"
            result["reply"] = (
                "Understood. The low power issue does not seem related to SoC, mode, brake drag, or temperature.<br><br>"
                "This may require a <b>controller or motor diagnostic</b> at a service center.<br><br>"
                "If you want, reply <b>YES</b> and I will raise a <b>Low Power</b> ticket for you."
            )
            result["quick_replies"] = ["YES – Raise Ticket", "NO – Don't Raise Ticket"]
            return result

        else:
            result["reply"] = "Please reply <b>YES</b> or <b>NO</b>."
            return result

    # TICKET CONFIRM STEPS
    if step in ["low_soc_ticket", "eco_mode_ticket",
                "brake_drag_ticket", "thermal_ticket",
                "low_power_general_ticket"]:
        if t.startswith("y"):
            if step == "low_soc_ticket":
                desc = "Low power issue – Battery SoC low, power limited."
            elif step == "eco_mode_ticket":
                desc = "Low power issue – ECO mode switched off, still low power."
            elif step == "brake_drag_ticket":
                desc = "Low power issue – Brake drag / mechanical resistance suspected."
            elif step == "thermal_ticket":
                desc = "Low power issue – Thermal limiting suspected after continuous riding."
            else:
                desc = "Low power issue – General performance drop, needs diagnosis."

            return _start_contact_collection(
                session_id,
                result,
                category="Low Power / Performance Issue",
                description=desc,
                success_title="Ticket Created"
            )
        else:
            _reset_state(session_id)
            result["reply"] = (
                "Okay, I won't create a ticket right now.<br>"
                "If the low power issue continues, you can type <b>Low power issue</b> again "
                "or contact support at <b>8788-9400</b>."
            )
            _set_home_quick_replies(result)
            return result

    # fallback
    _reset_state(session_id)
    result["reply"] = "To restart performance troubleshooting, type <b>Low power issue</b>."
    _set_home_quick_replies(result)
    return result


# ---------------------- BRAKE ISSUE FLOW ---------------------- #

def _flow_brake(text, session_id, result):
    state = _get_state(session_id)
    step = state["step"]
    t = text.lower()

    result["intent"] = "brake_issue"

    # STEP 1 — Symptom description
    if step == "symptom_detail":
        state["data"]["symptom"] = text.strip()
        state["step"] = "lever_feel"
        result["reply"] = (
            "Thanks for the details.<br><br>"
            "2️⃣ How does the <b>brake lever / pedal feel</b>?<br><br>"
            "Choose one:<br>"
            "• Soft / spongy<br>"
            "• Very hard<br>"
            "• Normal but braking is weak"
        )
        result["quick_replies"] = [
            "Soft / Spongy",
            "Very Hard",
            "Normal Feel but Weak Braking"
        ]
        return result

    # STEP 2 — Lever feel
    if step == "lever_feel":
        if "soft" in t or "spongy" in t:
            state["step"] = "brake_soft_ticket"
            result["reply"] = (
                "⚠ A <b>soft or spongy brake</b> usually indicates air in brake lines or worn brake pads.<br><br>"
                "It is recommended to get the brake system bled and inspected.<br><br>"
                "Reply <b>YES</b> and I will raise a brake service ticket for you."
            )
            result["quick_replies"] = ["YES – Raise Ticket", "NO – Don't Raise Ticket"]
            return result

        elif "hard" in t:
            state["step"] = "brake_hard_ticket"
            result["reply"] = (
                "⚠ A <b>very hard brake lever</b> may indicate a jammed caliper or mechanical obstruction.<br><br>"
                "This requires immediate inspection at a service center.<br><br>"
                "Reply <b>YES</b> and I will raise a brake inspection ticket."
            )
            result["quick_replies"] = ["YES – Raise Ticket", "NO – Don't Raise Ticket"]
            return result

        elif "weak" in t or "normal" in t:
            state["step"] = "brake_weak_ticket"
            result["reply"] = (
                "⚠ Brakes feel normal but braking performance is <b>weak</b>.<br><br>"
                "This may be due to worn brake pads or disc issues.<br><br>"
                "Reply <b>YES</b> and I will raise a brake performance ticket."
            )
            result["quick_replies"] = ["YES – Raise Ticket", "NO – Don't Raise Ticket"]
            return result

        else:
            result["reply"] = "Please choose one of the given brake feel options."
            return result

    # TICKET CONFIRM STEPS
    if step in ["brake_soft_ticket", "brake_hard_ticket", "brake_weak_ticket"]:
        if t.startswith("y"):
            if step == "brake_soft_ticket":
                desc = "Brake issue – Lever feels soft/spongy, possible air in lines."
            elif step == "brake_hard_ticket":
                desc = "Brake issue – Lever very hard, possible caliper jam."
            else:
                desc = "Brake issue – Normal lever feel but weak braking."

            return _start_contact_collection(
                session_id,
                result,
                category="Brake Issue",
                description=desc,
                success_title="Ticket Created"
            )
        else:
            _reset_state(session_id)
            result["reply"] = (
                "Okay, no ticket created right now.<br>"
                "If braking still feels unsafe, please visit a service center or call <b>8788-9400</b>."
            )
            _set_home_quick_replies(result)
            return result

    # fallback
    _reset_state(session_id)
    result["reply"] = "To restart brake troubleshooting, type <b>Brake issue</b>."
    _set_home_quick_replies(result)
    return result
# ---------------------- DISPLAY ISSUE FLOW ---------------------- #

def _flow_display(text, session_id, result):
    state = _get_state(session_id)
    step = state["step"]
    t = text.lower()

    result["intent"] = "display_issue"

    # STEP 1 — HV indicator check
    if step == "hv_status":
        if "yes" in t:
            state["step"] = "lv_check"
            result["reply"] = (
                "✅ HV / TSAL indicator is ON, but the <b>display is not turning on</b>.<br><br>"
                "This usually indicates a <b>low-voltage (12V) supply issue</b> to the display.<br><br>"
                "👉 Please check:<br>"
                "• LV fuse<br>"
                "• Display wiring connector<br><br>"
                "If the issue still persists, reply <b>YES</b> and I will raise a display ticket."
            )
            result["quick_replies"] = ["YES – Raise Ticket", "NO – Will Check"]
            state["step"] = "display_lv_ticket"
            return result

        elif "no" in t:
            state["step"] = "hv_off_ticket"
            result["reply"] = (
                "⚠ HV / TSAL indicator is OFF and display is also OFF.<br><br>"
                "This means the vehicle is <b>not powering up</b> correctly.<br><br>"
                "Possible causes:<br>"
                "• HV interlock open<br>"
                "• BMS not enabling contactors<br>"
                "• Key switch or HV relay issue<br><br>"
                "Reply <b>YES</b> and I will raise a <b>Power-Up / Display</b> ticket."
            )
            result["quick_replies"] = ["YES – Raise Ticket", "NO – Don't Raise Ticket"]
            return result

        else:
            result["reply"] = "Please reply <b>YES</b> or <b>NO</b> regarding the TSAL indicator."
            return result

    # TICKET CONFIRM STEPS
    if step in ["display_lv_ticket", "hv_off_ticket"]:
        if t.startswith("y"):
            if step == "display_lv_ticket":
                desc = "Display issue – HV ON but display OFF, suspected LV supply/wiring issue."
                cat = "Display Issue"
            else:
                desc = "Power-up failure – HV OFF and display OFF."
                cat = "Power-Up Issue"

            return _start_contact_collection(
                session_id,
                result,
                category=cat,
                description=desc,
                success_title="Ticket Created"
            )
        else:
            _reset_state(session_id)
            result["reply"] = (
                "Okay, no ticket created right now.<br>"
                "If the display still does not turn on, please contact support at <b>8788-9400</b>."
            )
            _set_home_quick_replies(result)
            return result

    # fallback
    _reset_state(session_id)
    result["reply"] = "To restart display troubleshooting, type <b>Display not turning on</b>."
    _set_home_quick_replies(result)
    return result


# ---------------------- TICKET CREATION FLOW (MANUAL) ---------------------- #

def _flow_ticket(text, session_id, result):
    state = _get_state(session_id)
    step = state["step"]
    data = state["data"]

    result["intent"] = "raise_ticket"

    # STEP 1 — Issue description
    if step == "issue":
        data["issue"] = text.strip()
        state["step"] = "city"
        result["reply"] = (
            "Thanks. Please tell me your <b>city</b> so I can assign the nearest service team."
        )
        result["needs_city"] = True
        return result

    # STEP 2 — City
    if step == "city":
        data["city"] = text.strip()
        city_lower = data["city"].lower()

        centers = get_service_centers_by_city(data["city"])
        if not centers and city_lower in FAKE_CENTERS:
            centers = FAKE_CENTERS[city_lower]

        if not centers and city_lower not in FAKE_CENTERS:
            return _handle_city_not_available(result, data["city"])

        state["step"] = "confirm"
        result["reply"] = (
            "<b>Please confirm your ticket details:</b><br><br>"
            f"Issue: {data['issue']}<br>"
            f"City: {data['city']}<br><br>"
            "Reply <b>YES</b> to submit or <b>NO</b> to cancel."
        )
        return result

    # STEP 3 — Confirm
    if step == "confirm":
        if text.lower().startswith("y"):
            desc = f"{data['issue']} (City: {data['city']})"
            return _start_contact_collection(
                session_id,
                result,
                category="General Issue",
                description=desc,
                success_title="Ticket Created"
            )
        else:
            _reset_state(session_id)
            result["reply"] = "Ticket creation cancelled."
            _set_home_quick_replies(result)
            return result

    _reset_state(session_id)
    result["reply"] = "To raise a ticket again, type <b>Raise ticket</b>."
    _set_home_quick_replies(result)
    return result


# ---------------------- SERVICE BOOKING FLOW ---------------------- #

def _parse_date_ddmmyyyy(date_str: str):
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
    except Exception:
        return None


def _flow_service_booking(text, session_id, result):
    state = _get_state(session_id)
    step = state["step"]
    data = state["data"]

    result["intent"] = "book_service"

    # STEP 1 — City
    if step == "city":
        data["city"] = text.strip()
        city_lower = data["city"].lower()

        centers = get_service_centers_by_city(data["city"])
        if not centers and city_lower in FAKE_CENTERS:
            centers = FAKE_CENTERS[city_lower]

        if not centers and city_lower not in FAKE_CENTERS:
            return _handle_city_not_available(result, data["city"])

        data["centers"] = centers
        state["step"] = "center_choice"

        msg = f"📍 <b>Service Centers near {data['city'].title()}:</b><br><br>"
        for i, c in enumerate(centers, start=1):
            msg += (
                f"<b>{i}. {c['name']}</b><br>"
                f"{c['address']}<br>"
                f"📞 {c['phone']}<br><br>"
            )
        msg += "Reply with the <b>number</b> of your preferred center, or type <b>any</b>."
        result["reply"] = msg
        result["service_centers"] = centers
        return result

    # STEP 2 — Center selection
    if step == "center_choice":
        centers = data.get("centers", [])
        choice = text.strip().lower()

        if choice.isdigit() and centers and 1 <= int(choice) <= len(centers):
            data["center"] = centers[int(choice) - 1]["name"]
        else:
            data["center"] = "Any authorized nearby center"

        state["step"] = "date"
        result["reply"] = (
            "Please enter your <b>preferred service date</b>.<br>"
            "Format: <b>DD/MM/YYYY</b>"
        )
        return result

    # STEP 3 — Date
    if step == "date":
        dt = _parse_date_ddmmyyyy(text)
        if not dt:
            result["reply"] = "Invalid date format. Please use <b>DD/MM/YYYY</b>."
            return result

        today = date.today()
        if dt <= today:
            result["reply"] = (
                "Please choose a <b>future date</b> (not today or past).<br>"
                "Format: <b>DD/MM/YYYY</b>."
            )
            return result

        data["date"] = dt.strftime("%d/%m/%Y")
        state["step"] = "issue"
        result["reply"] = "Please briefly describe the <b>reason for service</b>."
        return result

    # STEP 4 — Issue description
    if step == "issue":
        data["issue"] = text.strip()
        state["step"] = "confirm"
        result["reply"] = (
            "<b>Please confirm your service booking:</b><br><br>"
            f"City: {data['city']}<br>"
            f"Center: {data['center']}<br>"
            f"Date: {data['date']}<br>"
            f"Issue: {data['issue']}<br><br>"
            "Reply <b>YES</b> to confirm or <b>NO</b> to cancel."
        )
        return result

    # STEP 5 — Confirm
    if step == "confirm":
        if text.lower().startswith("y"):
            desc = (
                f"Service booking – City: {data['city']} | "
                f"Center: {data['center']} | "
                f"Date: {data['date']} | "
                f"Issue: {data['issue']}"
            )
            return _start_contact_collection(
                session_id,
                result,
                category="Service Booking",
                description=desc,
                success_title="Service Booked"
            )
        else:
            _reset_state(session_id)
            result["reply"] = "Service booking cancelled."
            _set_home_quick_replies(result)
            return result

    _reset_state(session_id)
    result["reply"] = "To book a service again, type <b>Book service</b>."
    _set_home_quick_replies(result)
    return result
# ---------------------- NEARBY SERVICE CENTERS FLOW ---------------------- #

def _flow_service_centers(text, session_id, result):
    state = _get_state(session_id)
    step = state["step"]
    data = state["data"]

    result["intent"] = "service_center_info"

    if step == "city":
        data["city"] = text.strip()
        city_lower = data["city"].lower()

        centers = get_service_centers_by_city(data["city"])
        if not centers and city_lower in FAKE_CENTERS:
            centers = FAKE_CENTERS[city_lower]

        _reset_state(session_id)

        if centers:
            msg = f"📍 <b>TerraPower Service Centers near {data['city'].title()}:</b><br><br>"
            for i, c in enumerate(centers, start=1):
                msg += (
                    f"<b>{i}. {c['name']}</b><br>"
                    f"{c['address']}<br>"
                    f"📞 {c['phone']}<br><br>"
                )
            msg += (
                "You can type <b>Book a service</b> to schedule an appointment "
                "or <b>Raise ticket</b> for support."
            )
            result["reply"] = msg
            result["service_centers"] = centers
            _set_home_quick_replies(result)
            return result

        return _handle_city_not_available(result, data["city"])

    _reset_state(session_id)
    result["reply"] = "To check again, type <b>Nearby service centers</b>."
    _set_home_quick_replies(result)
    return result


# ---------------------- SPARE PARTS FLOW ---------------------- #

def _flow_spare_parts(text, session_id, result):
    state = _get_state(session_id)
    step = state["step"]
    data = state["data"]

    result["intent"] = "spare_parts_query"

    # STEP 1 — Part name
    if step == "part":
        data["part"] = text.strip()
        state["step"] = "city"
        result["reply"] = (
            f"Got it. You are looking for <b>{data['part']}</b>.<br><br>"
            "Please tell me your <b>city</b> so I can check availability."
        )
        result["needs_city"] = True
        return result

    # STEP 2 — City
    if step == "city":
        data["city"] = text.strip()
        city_lower = data["city"].lower()

        centers = get_service_centers_by_city(data["city"])
        if not centers and city_lower in FAKE_CENTERS:
            centers = FAKE_CENTERS[city_lower]

        if not centers and city_lower not in FAKE_CENTERS:
            return _handle_city_not_available(result, data["city"])

        data["centers"] = centers
        state["step"] = "confirm"

        msg = (
            f"📦 <b>Spare Part:</b> {data['part']}<br>"
            f"📍 <b>City:</b> {data['city'].title()}<br><br>"
            "Available at the following service centers:<br><br>"
        )

        for i, c in enumerate(centers, start=1):
            msg += (
                f"<b>{i}. {c['name']}</b><br>"
                f"{c['address']}<br>"
                f"📞 {c['phone']}<br><br>"
            )

        msg += (
            "Reply <b>YES</b> to raise a spare parts enquiry ticket, "
            "or <b>NO</b> to skip."
        )
        result["reply"] = msg
        result["service_centers"] = centers
        result["quick_replies"] = ["YES – Raise Ticket", "NO – Don't Raise Ticket"]
        return result

    # STEP 3 — Confirm
    if step == "confirm":
        if text.lower().startswith("y"):
            desc = (
                f"Spare parts enquiry – Part: {data['part']} | "
                f"City: {data['city']} | "
                f"Centers: {', '.join(c['name'] for c in data.get('centers', []))}"
            )
            return _start_contact_collection(
                session_id,
                result,
                category="Spare Parts Enquiry",
                description=desc,
                success_title="Ticket Created"
            )
        else:
            _reset_state(session_id)
            result["reply"] = (
                "Okay, no ticket created.<br>"
                "You can directly visit a service center for spare availability."
            )
            _set_home_quick_replies(result)
            return result

    _reset_state(session_id)
    result["reply"] = "To check spare parts again, type <b>Spare parts query</b>."
    _set_home_quick_replies(result)
    return result


# ---------------------- MAIN MESSAGE HANDLER ---------------------- #

def maybe_auto_create_ticket(message: str, session_id: str, intent: str):
    return False, None
