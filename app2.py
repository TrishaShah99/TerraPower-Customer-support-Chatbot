from flask import Flask, render_template, request, jsonify, session
from uuid import uuid4

from database2 import (
    init_db,
    save_chat,
    get_chat_history,
    clear_history,
    create_ticket,
    get_tickets,
)
from logic2 import handle_message, maybe_auto_create_ticket

# Use your custom folders
app = Flask(__name__, template_folder="templates2", static_folder="static2")
app.secret_key = "replace-this-secret-key"

# Initialize DB
init_db()


def get_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid4())
    return session["session_id"]


@app.route("/")
def index():
    session_id = get_session_id()
    history = get_chat_history(session_id)
    tickets = get_tickets(session_id)
    return render_template("index2.html", history=history, tickets=tickets, phone="8788-9400")


@app.route("/chat", methods=["POST"])
def chat():
    session_id = get_session_id()
    data = request.get_json(force=True)
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Empty message"}), 400

    # Main chatbot logic
    logic_result = handle_message(message, session_id)

    # Optional auto ticket creation
    ticket_created, ticket_id = maybe_auto_create_ticket(
        message, session_id, logic_result["intent"]
    )
    if ticket_created:
        logic_result["ticket_created"] = True
        logic_result["ticket_id"] = f"TP-{ticket_id:05d}"
        logic_result["reply"] += (
            f"\n\n✅ A support ticket has been created automatically.\n"
            f"**Ticket ID:** TP-{ticket_id:05d}"
        )

    # ------------------------------------------------------------------
    # FIXED SECTION — COMBINE primary reply + secondary reply BEFORE saving
    # ------------------------------------------------------------------
    full_reply = logic_result["reply"]
    if logic_result.get("secondary_reply"):
        full_reply += "<br><br>" + logic_result["secondary_reply"]

    # Save combined reply into DB so the UI history loads correct flow messages
    save_chat(session_id, message, full_reply, logic_result["intent"])
    # ------------------------------------------------------------------

    return jsonify(logic_result)


@app.route("/history", methods=["GET"])
def history():
    session_id = get_session_id()
    return jsonify(get_chat_history(session_id))


@app.route("/tickets", methods=["GET"])
def tickets():
    session_id = get_session_id()
    t_list = get_tickets(session_id)
    formatted = []
    for t in t_list:
        d = dict(t)
        d["display_id"] = f"TP-{d['id']:05d}"
        formatted.append(d)
    return jsonify(formatted)


@app.route("/clear_history", methods=["POST"])
def clear():
    session_id = get_session_id()
    clear_history(session_id)
    return jsonify({"status": "ok"})


@app.route("/create_ticket", methods=["POST"])
def create_ticket_api():
    session_id = get_session_id()
    data = request.get_json(force=True)
    issue_category = data.get("issue_category", "General")
    description = data.get("description", "").strip()

    if not description:
        return jsonify({"error": "Description required"}), 400

    ticket_id = create_ticket(session_id, issue_category, description)
    return jsonify({
        "ticket_id": f"TP-{ticket_id:05d}",
        "status": "Open"
    })


if __name__ == "__main__":
    app.run(debug=True)
