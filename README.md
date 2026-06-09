# TerraPower Electric ATV Support Chatbot

A Flask-based rule-based customer support chatbot created by me for **TerraPower Electric ATV**, the business presentation idea of **Team Stallions** for **SAE BAJA India 2026**.

The chatbot helps users troubleshoot common electric ATV issues, find service centers, book service appointments, and raise support tickets.

---

## Features

* Rule-based chatbot with multiple troubleshooting flows
* Step-by-step support for common ATV issues
* Automatic support ticket creation
* Name and phone number collection before ticket generation
* Chat history and ticket history using SQLite
* Service center lookup by city
* Service booking, warranty, and spare parts support

---

## Supported Flows

The chatbot supports:

* Vehicle not starting
* Battery not charging
* Low power / performance issue
* Brake issue
* Display not turning on
* Service appointment booking
* Nearby service center lookup
* Warranty query
* Spare parts query
* General support ticket creation

---

## Tech Stack

* Python
* Flask
* SQLite
* HTML
* CSS
* JavaScript

---

## Project Structure

```text
haha_chatbot/
│
├── app2.py              # Main Flask application
├── logic2.py            # Chatbot logic and conversation flows
├── database2.py         # SQLite database handling
├── chatbot2.db          # SQLite database file
│
├── templates2/
│   └── index2.html      # Frontend HTML template
│
├── static2/
│   ├── style.css        # CSS file
│   └── script.js        # JavaScript file
│
└── README.md
```

---

## How to Run

### 1. Open the project folder

```bash
cd C:\Users\User\Downloads\haha_chatbot
```

### 2. Install Flask

```bash
pip install flask
```

### 3. Run the application

```bash
python app2.py
```

### 4. Open in browser

```text
http://127.0.0.1:5000
```

---

## Important Note

This is a **Python Flask project**, not a Node.js project.

So commands like these are not required:

```bash
npm install
npm run dev
```

If you get a `package.json` error, it means npm is being run in the wrong type of project folder.

---

## Main Files

### `app2.py`

Main Flask application file. It handles routes, sessions, chat requests, ticket APIs, and connects the frontend with the chatbot logic.

### `logic2.py`

Contains the rule-based chatbot engine, intent detection, conversation flows, service booking flow, and ticket creation logic.

### `database2.py`

Handles the SQLite database for chat history, support tickets, and service center information.

---

## Example Inputs

```text
Hi
Vehicle not starting
Battery not charging
Low power issue
Brake issue
Book a service appointment
Show nearby service centers
Warranty query
Spare parts query
Raise ticket
```

---

## Future Improvements

* Admin dashboard for ticket management
* Ticket status update system
* Real service center database
* Email or WhatsApp ticket notifications
* Deployment on Render, Railway, or PythonAnywhere
* Improved natural language understanding

---

## Author

Created as a rule-based customer support chatbot project for **TerraPower Electric ATV**.
