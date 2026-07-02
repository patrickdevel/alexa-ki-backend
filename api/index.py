from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

SYSTEM_PROMPT = (
    "Du bist ein absolut präzises KI-Gehirn für einen Alexa Skill. Antworte kurz "
    "in maximal 2-3 Sätzen. Wenn der Nutzer den PC steuern, herunterfahren oder "
    "etwas öffnen möchte, bestätige den Befehl einfach kurz und nett."
)

TRIGGERCMD_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjZhNDYyOWQ2OWE4NTdkMDAxN2UyN2U2YSIsImlhdCI6MTc4Mjk4MzE5OH0.krWJy-_x2HD3HA4qywMD-YJUftK5-kfv1WKsgW44xYk"
COMPUTER_NAME = "DESKTOP-QQ9UGSB"

def trigger_pc_command(command_name):
    """Feuert den Befehl an deinen PC ab"""
    if "DEIN_TRIGGERCMD_TOKEN_HIER" in TRIGGERCMD_TOKEN:
        return False
    try:
        url = "https://www.triggercmd.com/api/run/trigger"
        headers = {"Authorization": f"Bearer {TRIGGERCMD_TOKEN}"}
        data = {
            "computer": COMPUTER_NAME,
            "trigger": command_name
        }
        res = requests.post(url, json=data, headers=headers)
        return res.status_code == 200
    except Exception:
        return False

def ask_groq_direct(messages):
    """Funkt Groq direkt über HTTP an, ganz ohne fehlerhafte Bibliothek"""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Groq API-Key fehlt in den Vercel-Umgebungsvariablen."
    
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
            return res.get_json()["choices"][0]["message"]["content"]
        else:
            return f"Groq API Fehler: Status {res.status_code}"
    except Exception as e:
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
            return respond("Hi! Ich bin dein KI-Assistent. Was gibt's?", chat_history)

        elif request_type == "IntentRequest":
            intent_name = data["request"]["intent"]["name"]
            
            if intent_name == "AskAiIntent":
                user_text = data["request"]["intent"]["slots"]["meinText"]["value"]
                user_text_lower = user_text.lower()
                
                # Befehls-Check für den PC
                if "taschenrechner" in user_text_lower or "rechner öffnen" in user_text_lower:
                    trigger_pc_command("Calculator")
                    ai_response = "Alles klar, ich öffne den Taschenrechner auf deinem PC."
                    chat_history.append({"role": "user", "content": user_text})
                    chat_history.append({"role": "assistant", "content": ai_response})
                    return respond(ai_response, chat_history)
                
                # Direkter HTTP-Aufruf an Groq
                chat_history.append({"role": "user", "content": user_text})
                messages = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_history
                
                ai_response = ask_groq_direct(messages)
                
                chat_history.append({"role": "assistant", "content": ai_response})
                return respond(ai_response, chat_history)

        return respond("Alles klar, bis bald!", chat_history, end_session=True)
        
    except Exception as e:
        return respond("Interner Fehler im Backend.", [])

def respond(text, chat_history, end_session=False):
    return jsonify({
        "version": "1.0",
        "sessionAttributes": {
            "chat_history": chat_history
        },
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": text
            },
            "shouldEndSession": end_session
        }
    })
