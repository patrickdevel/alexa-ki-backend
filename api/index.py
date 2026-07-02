from flask import Flask, request, jsonify
import os

app = Flask(__name__)

SYSTEM_PROMPT = (
    "Du bist ein absolut präzises KI-Gehirn für einen Alexa Skill. Antworte kurz "
    "in maximal 2-3 Sätzen. Wenn der Nutzer den PC steuern, herunterfahren oder "
    "etwas öffnen möchte, bestätige den Befehl einfach kurz und nett."
)

# TODO: Trage hier deine echten Daten ein (Anführungszeichen stehen lassen!)
TRIGGERCMD_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjZhNDYyOWQ2OWE4NTdkMDAxN2UyN2U2YSIsImlhdCI6MTc4Mjk4MzE5OH0.krWJy-_x2HD3HA4qywMD-YJUftK5-kfv1WKsgW44xYk"
COMPUTER_NAME = "DESKTOP-QQ9UGSB"

def trigger_pc_command(command_name):
    """Feuert den Befehl an deinen PC ab"""
    if "DEIN_TRIGGERCMD_TOKEN_HIER" in TRIGGERCMD_TOKEN:
        return False
    try:
        import requests
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
                
                # Groq erst hier importieren, damit die App nicht beim Start crashed
                try:
                    from groq import Groq
                    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
                except Exception:
                    return respond("Fehler beim Laden der KI-Bibliothek.", chat_history)
                    
                chat_history.append({"role": "user", "content": user_text})
                messages = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_history
                
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages
                )
                ai_response = completion.choices[0].message.content
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
