from flask import Flask, request, jsonify
from groq import Groq
import os
import requests

app = Flask(__name__)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# TODO: Trage hier deine TRIGGERcmd-Daten ein!
TRIGGERCMD_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjZhNDYyOWQ2OWE4NTdkMDAxN2UyN2U2YSIsImlhdCI6MTc4Mjk4MzE5OH0.krWJy-_x2HD3HA4qywMD-YJUftK5-kfv1WKsgW44xYk"
COMPUTER_NAME = "DESKTOP-QQ9UGSB"

SYSTEM_PROMPT = (
    "Du bist ein absolut präzises KI-Gehirn für einen Alexa Skill. Antworte kurz "
    "in maximal 2-3 Sätzen. Wenn der Nutzer den PC steuern, herunterfahren oder "
    "etwas öffnen möchte, bestätige den Befehl einfach kurz und nett."
)

def trigger_pc_command(command_name):
    """Feuert den Befehl an deinen PC ab"""
    url = "https://www.triggercmd.com/api/run/trigger"
    headers = {"Authorization": f"Bearer {TRIGGERCMD_TOKEN}"}
    data = {
        "computer": COMPUTER_NAME,
        "trigger": command_name
    }
    try:
        requests.post(url, json=data, headers=headers)
    except Exception as e:
        print(f"Fehler bei TRIGGERcmd: {e}")

@app.route("/api/alexa", methods=["POST"])
def alexa_skill():
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
            try:
                user_text = data["request"]["intent"]["slots"]["meinText"]["value"]
                user_text_lower = user_text.lower()
                
                # Hier checken wir, ob der PC gesteuert werden soll
                if "taschenrechner" in user_text_lower or "rechner öffnen" in user_text_lower:
                    trigger_pc_command("Calculator") # Exakter Trigger-Name aus der App
                    ai_response = "Alles klar, ich öffne den Taschenrechner auf deinem PC."
                    chat_history.append({"role": "user", "content": user_text})
                    chat_history.append({"role": "assistant", "content": ai_response})
                    return respond(ai_response, chat_history)
                
                # Normaler KI-Chat, falls kein PC-Befehl erkannt wurde
                chat_history.append({"role": "user", "content": user_text})
                messages = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_history
                
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages
                )
                ai_response = completion.choices[0].message.content
                chat_history.append({"role": "assistant", "content": ai_response})
                
                return respond(ai_response, chat_history)
                
            except Exception as e:
                return respond("Fehler beim Verarbeiten der KI-Antwort.", chat_history)

    return respond("Alles klar, bis bald!", chat_history, end_session=True)

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
