const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const userInput = document.getElementById("user-input");
const quickRepliesDiv = document.getElementById("quick-replies");
const historyList = document.getElementById("history-list");
const ticketList = document.getElementById("ticket-list");

let previousIntent = null;
let lastAskedForCity = false;

// ---------------- CLEAN STRING NORMALIZER ---------------- //
function cleanText(text) {
  if (!text) return "";
  return text.toString().replace(/\s+/g, " ").trim();
}

// ---------------- ADD MESSAGE TO CHAT WINDOW ---------------- //
function appendMessage(text, from) {
  const msgDiv = document.createElement("div");
  msgDiv.classList.add("msg", from === "user" ? "msg-user" : "msg-bot");

  const labelDiv = document.createElement("div");
  labelDiv.classList.add("msg-label");
  labelDiv.textContent = from === "user" ? "You" : "Terra";

  const textDiv = document.createElement("div");
  textDiv.classList.add("msg-text");
  textDiv.innerHTML = text;

  msgDiv.appendChild(labelDiv);
  msgDiv.appendChild(textDiv);

  chatWindow.appendChild(msgDiv);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// ---------------- QUICK REPLIES ---------------- //
function setQuickReplies(list) {
  quickRepliesDiv.innerHTML = "";
  if (!list || !list.length) return;

  list.forEach(text => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = text;

    btn.addEventListener("click", () => {
      const clean = cleanText(text);
      sendQuick(clean);
    });

    quickRepliesDiv.appendChild(btn);
  });
}

function sendQuick(text) {
  const clean = cleanText(text);
  userInput.value = clean;
  chatForm.dispatchEvent(new Event("submit"));
}

// ---------------- SEND MESSAGE TO BACKEND ---------------- //
async function sendMessage(message) {
  const cleanMessage = cleanText(message);

  if (!cleanMessage) return;

  console.log("[CHAT] Sending message to backend:", JSON.stringify(cleanMessage));
  appendMessage(cleanMessage, "user");

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: cleanMessage })
    });

    const data = await res.json();

    console.log("[CHAT] Backend response:", data);

    if (data.error) {
      appendMessage("Sorry, something went wrong.", "bot");
      return;
    }

    previousIntent = data.intent;
    lastAskedForCity = !!data.needs_city;

    appendMessage(data.reply, "bot");

    if (data.secondary_reply && cleanText(data.secondary_reply) !== "") {
      appendMessage(data.secondary_reply, "bot");
    }

    setQuickReplies(data.quick_replies);

    loadHistory();
    loadTickets();
  } catch (err) {
    console.error(err);
    appendMessage("Network error. Please try again.", "bot");
  }
}

// ---------------- SEND ON FORM SUBMIT ---------------- //
chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const msg = cleanText(userInput.value);
  if (!msg) return;
  userInput.value = "";
  sendMessage(msg);
});

// ---------------- GLOBAL SAFETY NET FOR ANY BUTTON ---------------- //
// This catches ANY button that visually says "Vehicle Not Starting"
// even if it's a static HTML button not created by setQuickReplies().
document.addEventListener("click", (e) => {
  const target = e.target;
  if (!target || target.tagName !== "BUTTON") return;

  const btnText = cleanText(target.textContent).toLowerCase();

  // extra guard: only for vehicle not starting text
  if (btnText.includes("vehicle not starting")) {
    e.preventDefault();
    console.log("[CHAT] Intercepted button for Vehicle Not Starting:", btnText);
    sendQuick("Vehicle Not Starting");  // exact phrase logic2.py expects
  }
});

// ---------------- CLEAR CHAT (IMPROVED) ---------------- //
document.getElementById("btn-clear-history").addEventListener("click", async () => {
  try {
    await fetch("/clear_history", { method: "POST" });

    chatWindow.innerHTML = "";

    const resetRes = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "__reset__" })
    });

    const resetData = await resetRes.json();

    console.log("[CHAT] Reset response:", resetData);

    appendMessage(resetData.reply, "bot");
    setQuickReplies(resetData.quick_replies);

    historyList.innerHTML = "";
  } catch (err) {
    console.error(err);
  }
});

// ---------------- MANUAL TICKET CREATION ---------------- //
document.getElementById("btn-raise-ticket").addEventListener("click", async () => {
  const desc = prompt("Describe your issue (short line):");
  if (!desc) return;
  createTicket("Manual", cleanText(desc));
});

async function createTicket(category, description) {
  try {
    const res = await fetch("/create_ticket", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ issue_category: category, description })
    });

    const data = await res.json();
    if (data.error) {
      alert("Could not create ticket: " + data.error);
      return;
    }

    appendMessage(
      `✅ Your support ticket has been created.<br>` +
      `Ticket ID: <b>${data.ticket_id}</b><br>` +
      `Category: ${category}<br>` +
      `Issue: ${description}<br><br>` +
      `📞 Our service team will contact you shortly.`,
      "bot"
    );

    loadTickets();
  } catch (err) {
    console.error(err);
    alert("Network error while creating ticket.");
  }
}

// ---------------- LOAD HISTORY (RIGHT PANEL) ---------------- //
async function loadHistory() {
  try {
    const res = await fetch("/history");
    const history = await res.json();
    historyList.innerHTML = "";
    history.forEach(item => {
      const li = document.createElement("li");
      li.innerHTML = `<strong>You:</strong> ${item.user_message}<br>
        <span style="color:#7d84a6;">Terra: ${item.bot_reply}</span>`;
      historyList.appendChild(li);
    });
  } catch (err) {
    console.error(err);
  }
}

// ---------------- LOAD TICKETS (RIGHT PANEL) ---------------- //
async function loadTickets() {
  try {
    const res = await fetch("/tickets");
    const tickets = await res.json();
    ticketList.innerHTML = "";
    tickets.forEach(t => {
      const li = document.createElement("li");
      li.innerHTML = `
        <strong>${t.display_id}</strong> – ${t.issue_category}<br>
        <span style="color:#7d84a6;">${t.description}</span><br>
        <span>Status: ${t.status}</span>`;
      ticketList.appendChild(li);
    });
  } catch (err) {
    console.error(err);
  }
}

// ---------------- INITIAL LOAD ---------------- //
loadHistory();
loadTickets();
