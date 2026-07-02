from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

SYSTEM_PROMPT = (
    "Du bist die Steuereinheit für den Windows-PC des Nutzers via Alexa. "
    "Wenn der Nutzer eine Aktion auf seinem PC ausführen möchte (z.B. App starten, herunterfahren, im Browser suchen), "
    "antworte EXAKT in einem der folgenden Formate und füge KEINEN anderen Text hinzu:\n"
    "- Für PC herunterfahren: ACTION: shutdown\n"
    "- Für Suche im Browser: ACTION: search | <suchbegriff>\n"
    "- Für App/Programm starten: ACTION: run | <programmname>\n\n"
    "Wenn es sich um eine normale Frage handelt, antworte ganz normal, kurz und knackig in maximal 2-3 Sätzen."
)

TRIGGERCMD_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjZhNDYyOWQ2OWE4NTdkMDAxN2UyN2U2YSIsImlhdCI6MTc4Mjk4MzE5OH0.krWJy-_x2HD3HA4qywMD-YJUftK5-kfv1WKsgW44xYk"
COMPUTER_NAME = "DESKTOP-QQ9UGSB"

def trigger_pc_command(command_name, parameter=None):
    """Feuert den Befehl inklusive optionaler Parameter an den PC ab"""
    if "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjZhNDYyOWQ2OWE4NTdkMDAxN2UyN2U2YSIsImlhdCI6MTc4Mjk4MzE5OH0.krWJy-_x2HD3HA4qywMD-YJUftK5-kfv1WKsgW44xYk" in TRIGGERCMD_TOKEN:
        return False
    try:
        url = "https://www.triggercmd.com/api/run/trigger"
        headers = {"Authorization": f"Bearer {TRIGGERCMD_TOKEN}"}
        data = {
            "computer": COMPUTER_NAME,
            "trigger": command_name
        }
        if parameter:
            data["parameter"] = parameter
            
        res = requests.post(url, json=data, headers=headers)
        return res.status_code == 200
    except Exception:
        return False

def ask_groq_direct(messages):
    """Funkt Groq direkt über HTTP an"""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Groq API-Key fehlt."
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"]
        return f"Groq API Fehler: {res.status_code}"
    except Exception:
        return "Verbindung zu Groq fehlgeschlagen."

@app.route("/api/alexa", methods=["POST"])
def alexa_skill():
    try:
        data = request.get_json()
        request_type = data.get("request", {}).get("type")
        
        session = data.get("session", {})
        attributes = session.get("attributes", {})
        chat_history = attributes.get("chat_history", [])

        if request_type == "LaunchRequest":
            return respond("Hi! Was gibt's?", chat_history)

        elif request_type == "IntentRequest":
            intent_name = data["request"]["intent"]["name"]
            
            if intent_name == "AskAiIntent":
                user_text = data["request"]["intent"]["slots"]["meinText"]["value"]
                
                chat_history.append({"role": "user", "content": user_text})
                messages = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_history
                
                ai_response = ask_groq_direct(messages)
                
                if ai_response.startswith("ACTION:"):
                    parts = ai_response.replace("ACTION:", "").strip().split("|")
                    action_type = parts[0].strip().lower()
                    
                    if action_type == "shutdown":
                        trigger_pc_command("Shutdown")
                        respond_text = "Alles klar, ich fahre deinen PC herunter."
                    
                    elif action_type == "search" and len(parts) > 1:
                        # Bereinigt den Suchbegriff radikal von Anführungszeichen und Punkten
                        search_term = parts[1].strip().replace('"', '').replace("'", "").replace(".", "")
                        trigger_pc_command("Search", parameter=search_term)
                        respond_text = f"Ich habe das Web nach '{search_term}' auf deinem PC durchsucht."
                    
                    elif action_type == "run" and len(parts) > 1:
                        # Macht App-Namen klein und sauber (z.B. "notepad")
                        app_name = parts[1].strip().replace('"', '').replace("'", "").replace(".", "").lower()
                        trigger_pc_command("Run", parameter=app_name)
                        respond_text = f"Ich starte {app_name} auf deinem PC."
                    
                    else:
                        respond_text = "Ungültige PC-Aktion."
                    
                    chat_history.append({"role": "assistant", "content": respond_text})
                    return respond(respond_text, chat_history)
                
                chat_history.append({"role": "assistant", "content": ai_response})
                return respond(ai_response, chat_history)

        return respond("Alles klar, bis bald!", chat_history, end_session=True)
        
    except Exception:
        return respond("Interner Fehler im Backend.", [])

def respond(text, chat_history, end_session=False):
    return jsonify({
        "version": "1.0",
        "sessionAttributes": {"chat_history": chat_history},
        "response": {
            "outputSpeech": {"type": "PlainText", "text": text},
            "shouldEndSession": end_session
        }
    })
