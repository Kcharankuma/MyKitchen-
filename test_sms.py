import os
from twilio.rest import Client

# Read credentials from environment variables
ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE = os.getenv('TWILIO_PHONE_NUMBER', '+17372508034')
TO_PHONE = os.getenv('RECIPIENT_PHONE_NUMBER', '+917075575715')

try:
    if not ACCOUNT_SID or not AUTH_TOKEN:
        print("Error: Twilio credentials are not set in environment variables.")
    else:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        message = client.messages.create(
            body="MY KITCHEN: Test message successful!",
            from_=TWILIO_PHONE,
            to=TO_PHONE
        )
        print(f"Success! Message SID: {message.sid}")
except Exception as e:
    print(f"\n--- TWILIO ERROR DETAILS ---\n{e}\n-----------------------------")