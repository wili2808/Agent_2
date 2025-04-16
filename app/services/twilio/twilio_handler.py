from twilio.rest import Client
from dotenv import load_dotenv
import os

load_dotenv()

class TwilioHandler:
    def __init__(self):
        self.client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )
        self.phone_number = os.getenv("TWILIO_PHONE_NUMBER")

    async def send_message(self, to: str, message: str):
        try:
            message = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to
            )
            return {"status": "success", "message_id": message.sid}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def handle_incoming_message(self, from_number: str, message: str):
        # Aquí procesaremos los mensajes entrantes
        # y los enviaremos al agente IA
        pass 