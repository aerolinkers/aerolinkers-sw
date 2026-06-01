from gtts import gTTS
import os

# Your passengers and devices from database
# Format: (name, pnr, device_id)
passengers = [
    ("Thiru", "TB2376", "DEV001"),
    ("John Doe", "AB1234", "DEV002"),
    # Add more passengers here
]

# Flights for boarding alerts
# Format: (flight_id, destination, gate, device_id)
flights = [
    ("AI202", "Mumbai", "Gate 12", "DEV001"),
    ("AI305", "Bangalore", "Gate 15", "DEV002"),
    # Add more
]

os.makedirs("audio", exist_ok=True)

# Generate init audio for each passenger
for name, pnr, device_id in passengers:
    message = f"Welcome {name}. Your PNR number is {pnr}."
    filepath = f"audio/init_{device_id}.wav"
    tts = gTTS(text=message, lang='en')
    tts.save(filepath)
    print(f"Generated: {filepath}")

# Generate boarding alert audio
for flight_id, destination, gate, device_id in flights:
    message = f"Boarding starts soon for flight {flight_id} to {destination}. Please proceed to {gate}."
    filepath = f"audio/alert_{device_id}.wav"
    tts = gTTS(text=message, lang='en')
    tts.save(filepath)
    print(f"Generated: {filepath}")

print("Done!")