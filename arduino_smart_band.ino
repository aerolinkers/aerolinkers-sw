#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <SPI.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>

// ===== TFT PIN CONFIG =====
#define TFT_CS    10
#define TFT_AO     9
#define TFT_RST    8
#define TFT_SDA   11
#define TFT_SCK   12

Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS, TFT_AO, TFT_SDA, TFT_SCK, TFT_RST);

// ===== COLORS =====
#define COLOR_BG      0x0000
#define COLOR_HEADER  0x041F
#define COLOR_ACCENT  0xFD20
#define COLOR_WHITE   0xFFFF
#define COLOR_GREEN   0x07E0
#define COLOR_RED     0xF800
#define COLOR_GRAY    0x8410
#define COLOR_YELLOW  0xFFE0

// ===== TIMING CONSTANTS =====
#define REQUEST_DELAY         2000
#define BOARDING_DISPLAY_MS   8000
#define NOTIFICATION_DISPLAY_MS 6000
#define SUCCESS_DISPLAY_MS    2000
#define POLL_INTERVAL         30000   // background poll every 30 seconds
#define RECONNECT_COOLDOWN    10000   // wait 10s before retrying WiFi

// ===== WiFi =====
const char* ssid     = "Thiru";
const char* password = "thiru123";

// ===== Server =====
const char* serverUrl = "https://aerolinkers.pythonanywhere.com/sync";

// ===== State =====
String deviceMAC;
String passengerPNR        = "";
unsigned long lastRequestTime  = 0;
unsigned long lastPollTime     = 0;
unsigned long lastReconnectTime = 0;


// ============================================================
// STEP 1 — TFT HELPERS (unchanged)
// ============================================================

void tftClear() {
  tft.fillScreen(COLOR_BG);
}

void tftHeader(String title) {
  tft.fillRect(0, 0, 128, 20, COLOR_HEADER);
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(1);
  tft.setCursor(4, 6);
  tft.print("* " + title);
}

void tftDivider(int y) {
  tft.drawFastHLine(4, y, 120, COLOR_GRAY);
}

void tftField(String label, String value, int y) {
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(1);
  tft.setCursor(6, y);
  tft.print(label);
  tft.setTextColor(COLOR_WHITE);
  tft.setCursor(6, y + 11);
  tft.print(value.substring(0, 20));
}

void tftStatus(String line1, String line2 = "", uint16_t color1 = COLOR_WHITE, uint16_t color2 = COLOR_GRAY) {
  tftClear();
  tftHeader("AeroLinkers");
  tft.setTextSize(1);
  tft.setTextColor(color1);
  tft.setCursor(8, 38);
  tft.print(line1);
  if (line2 != "") {
    tft.setTextColor(color2);
    tft.setCursor(8, 56);
    tft.print(line2);
  }
}


// ============================================================
// STEP 2 — EXISTING SCREENS (unchanged)
// ============================================================

void tftReady() {
  tftClear();
  tftHeader("AeroLinkers");
  tft.setTextColor(COLOR_GRAY);
  tft.setTextSize(1);
  tft.setCursor(8, 38);
  tft.print("Enter PNR in");
  tft.setCursor(8, 50);
  tft.print("Serial Monitor");
  tft.drawRect(10, 80, 108, 30, COLOR_ACCENT);
  tft.setTextColor(COLOR_ACCENT);
  tft.setCursor(18, 91);
  tft.print("e.g.  TB2376");
}

void tftFetching(String pnr) {
  tftClear();
  tftHeader("Fetching...");
  tft.setTextColor(COLOR_WHITE);
  tft.setTextSize(2);
  int x = (128 - pnr.length() * 12) / 2;
  tft.setCursor(x, 40);
  tft.print(pnr);
  tft.setTextColor(COLOR_GRAY);
  tft.setTextSize(1);
  tft.setCursor(24, 80);
  tft.print("Contacting server");
  tft.drawRect(14, 100, 100, 8, COLOR_ACCENT);
  for (int i = 0; i <= 96; i += 8) {
    tft.fillRect(16, 102, i, 4, COLOR_ACCENT);
    delay(80);
  }
}

void tftWiFiConnecting(String ssidName) {
  tftClear();
  tftHeader("AeroLinkers");
  tft.setTextColor(COLOR_GRAY);
  tft.setTextSize(1);
  tft.setCursor(8, 34);
  tft.print("Connecting to:");
  tft.setTextColor(COLOR_WHITE);
  tft.setCursor(8, 46);
  tft.print(ssidName);
  tft.setTextColor(COLOR_ACCENT);
  tft.setCursor(8, 70);
  tft.print("Please wait...");
}

void tftWiFiSuccess(String ip) {
  tftClear();
  tftHeader("WiFi Connected");
  tft.fillCircle(64, 70, 18, COLOR_GREEN);
  tft.setTextColor(COLOR_BG);
  tft.setTextSize(2);
  tft.setCursor(56, 63);
  tft.print("OK");
  tft.setTextColor(COLOR_GRAY);
  tft.setTextSize(1);
  tft.setCursor(8, 100);
  tft.print("IP: " + ip);
  delay(SUCCESS_DISPLAY_MS);
}

void tftWiFiFailed() {
  tftClear();
  tftHeader("WiFi Error");
  tft.fillCircle(64, 65, 18, COLOR_RED);
  tft.setTextColor(COLOR_WHITE);
  tft.setTextSize(2);
  tft.setCursor(55, 58);
  tft.print("!!");
  tft.setTextColor(COLOR_RED);
  tft.setTextSize(1);
  tft.setCursor(14, 96);
  tft.print("Connection Failed");
  delay(SUCCESS_DISPLAY_MS);
}

void tftError(String title, String msg) {
  tftClear();
  tft.fillRect(0, 0, 128, 18, COLOR_RED);
  tft.setTextColor(COLOR_WHITE);
  tft.setTextSize(1);
  tft.setCursor(4, 5);
  tft.print(title);
  tft.setTextColor(COLOR_GRAY);
  tft.setCursor(8, 34);
  tft.print(msg);
  delay(3000);
  tftReady();
}

void tftBoardingPass(String pnr, String name, String flight, String seat, String boarding) {
  tftClear();
  tft.fillRect(0, 0, 128, 18, COLOR_HEADER);
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(1);
  tft.setCursor(4, 5);
  tft.print("BOARDING PASS");

  tft.setTextColor(COLOR_YELLOW);
  tft.setTextSize(2);
  int pnrX = (128 - pnr.length() * 12) / 2;
  tft.setCursor(pnrX, 22);
  tft.print(pnr);

  tftDivider(42);
  tftField("PASSENGER", name, 46);
  tftDivider(68);

  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(1);
  tft.setCursor(6, 72);
  tft.print("FLIGHT");
  tft.setCursor(70, 72);
  tft.print("SEAT");
  tft.setTextColor(COLOR_WHITE);
  tft.setCursor(6, 83);
  tft.print(flight.substring(0, 8));
  tft.setCursor(70, 83);
  tft.print(seat);

  tftDivider(96);
  tftField("BOARDING TIME", boarding, 100);

  tft.fillRect(0, 148, 128, 12, COLOR_HEADER);
  tft.setTextColor(COLOR_GRAY);
  tft.setTextSize(1);
  tft.setCursor(8, 151);
  tft.print("Have a safe flight!");
}


// ============================================================
// STEP 3 — NEW: NOTIFICATION SCREEN (FIXED)
// ============================================================
// NOTE: The server only sends the message text, not a type.
// This function infers the urgency/style from keywords in the message.

void tftNotification(String message) {
  tftClear();

  // Infer header style based on message keywords
  uint16_t headerBg   = COLOR_HEADER;
  uint16_t headerText = COLOR_YELLOW;
  String   headerLabel = "ALERT";

  String msgLower = message;
  msgLower.toLowerCase();

  if (msgLower.indexOf("gate") >= 0) {
    headerBg    = COLOR_HEADER;
    headerText  = COLOR_ACCENT;
    headerLabel = "GATE CHANGE";
  } else if (msgLower.indexOf("delay") >= 0 || msgLower.indexOf("delayed") >= 0) {
    headerBg    = COLOR_RED;
    headerText  = COLOR_WHITE;
    headerLabel = "DELAY";
  } else if (msgLower.indexOf("boarding") >= 0 || msgLower.indexOf("board") >= 0) {
    headerBg    = COLOR_GREEN;
    headerText  = COLOR_BG;
    headerLabel = "NOW BOARDING";
  } else if (msgLower.indexOf("cancel") >= 0) {
    headerBg    = COLOR_RED;
    headerText  = COLOR_WHITE;
    headerLabel = "CANCELLED";
  }

  // Draw header
  tft.fillRect(0, 0, 128, 20, headerBg);
  tft.setTextColor(headerText);
  tft.setTextSize(1);
  tft.setCursor(4, 6);
  tft.print("* " + headerLabel);

  // Flashing border for urgency
  tft.drawRect(2, 22, 124, 120, headerText);

  // Message — auto-wrap every 18 chars
  tft.setTextColor(COLOR_WHITE);
  tft.setTextSize(1);

  int lineHeight = 14;
  int y = 36;
  int maxChars = 18;
  int msgLen = message.length();
  int pos = 0;

  while (pos < msgLen && y < 120) {
    tft.setCursor(8, y);
    tft.print(message.substring(pos, pos + maxChars));
    pos += maxChars;
    y += lineHeight;
  }

  // Dismiss hint
  tft.setTextColor(COLOR_GRAY);
  tft.setCursor(8, 134);
  tft.print("Refreshing in 6s...");

  Serial.println("🔔 Notification: " + message);
  delay(NOTIFICATION_DISPLAY_MS);
}


// ============================================================
// STEP 4 — WIFI (improved: backoff on reconnect)
// ============================================================

void connectToWiFi() {
  tftWiFiConnecting(ssid);
  Serial.print("Connecting to WiFi...");

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi Connected! IP: " + WiFi.localIP().toString());
    tftWiFiSuccess(WiFi.localIP().toString());
  } else {
    Serial.println("\n❌ WiFi Failed!");
    tftWiFiFailed();
  }
}


// ============================================================
// STEP 5 — SEND REQUEST (unchanged structure)
// ============================================================

void sendPNRRequest() {
  if (WiFi.status() != WL_CONNECTED) {
    tftError("No WiFi", "Check connection");
    return;
  }

  WiFiClientSecure client;
  client.setInsecure();   // NOTE: swap for CA cert in production

  HTTPClient http;
  http.begin(client, serverUrl);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(10000);

  // Build request JSON
  DynamicJsonDocument requestDoc(512);
  requestDoc["device_id"] = deviceMAC;
  requestDoc["pnr"]       = passengerPNR;

  String requestBody;
  serializeJson(requestDoc, requestBody);
  Serial.println("\n📤 " + requestBody);

  int httpCode = http.POST(requestBody);
  Serial.println("📨 HTTP: " + String(httpCode));

  switch (httpCode) {
    case 200:  handleSuccessResponse(&http);               break;
    case 404:  tftError("PNR Not Found", passengerPNR);    break;
    case 400:  tftError("Bad Request",   "Check PNR");     break;
    case 500:  tftError("Server Error",  "Try again");     break;
    case -1:   tftError("No Connection", "Server unreachable"); break;
    default:   tftError("Error " + String(httpCode), "Unexpected"); break;
  }

  http.end();
}


// ============================================================
// STEP 6 — HANDLE SUCCESS (FIXED: notification as string)
// ============================================================

void handleSuccessResponse(HTTPClient* http) {
  String response = http->getString();
  Serial.println("📨 " + response);

  // Use DynamicJsonDocument — handles larger/variable payloads
  DynamicJsonDocument doc(1024);
  DeserializationError error = deserializeJson(doc, response);

  if (error) {
    tftError("Parse Error", "Bad JSON");
    return;
  }

  // Validate required passenger fields
  if (!doc.containsKey("name")     || !doc.containsKey("flight") ||
      !doc.containsKey("seat")     || !doc.containsKey("boarding_time")) {
    tftError("Data Error", "Missing fields");
    return;
  }

  // Extract passenger data
  String name     = doc["name"].as<String>();
  String flight   = doc["flight"].as<String>();
  String seat     = doc["seat"].as<String>();
  String boarding = doc["boarding_time"].as<String>();
  String pnr      = doc["pnr"].as<String>();

  Serial.println("\n==================================");
  Serial.println("PNR:      " + pnr);
  Serial.println("Name:     " + name);
  Serial.println("Flight:   " + flight);
  Serial.println("Seat:     " + seat);
  Serial.println("Boarding: " + boarding);

  // ---- FIXED: notification is a STRING, not an object ----
  // The server sends either a message string or null
  if (doc.containsKey("notification") && !doc["notification"].isNull()) {
    String notifMessage = doc["notification"].as<String>();
    Serial.println("🔔 Notification: " + notifMessage);
    tftNotification(notifMessage);  // Call with just the message
  }
  // -------------------------------------------------------

  Serial.println("==================================\n");

  // Show boarding pass after any notification
  tftBoardingPass(pnr, name, flight, seat, boarding);
  delay(BOARDING_DISPLAY_MS);
  tftReady();
}


// ============================================================
// STEP 7 — SETUP (unchanged)
// ============================================================

void setup() {
  Serial.begin(115200);
  delay(500);

  tft.initR(INITR_BLACKTAB);
  tft.setRotation(0);
  tft.fillScreen(COLOR_BG);

  tftStatus("AeroLinkers", "v2.0 Starting...", COLOR_ACCENT, COLOR_GRAY);
  delay(1500);

  Serial.println("\n=== AeroLinkers Smart Band v2.0 ===");

  connectToWiFi();

  deviceMAC = WiFi.macAddress();
  Serial.println("MAC: " + deviceMAC);

  tftReady();
  Serial.println("\n👉 Enter PNR in Serial Monitor:");
}


// ============================================================
// STEP 8 — LOOP (updated: backoff reconnect + background poll)
// ============================================================

void loop() {

  // --- WiFi watchdog with cooldown (no spam reconnect) ---
  if (WiFi.status() != WL_CONNECTED) {
    if (millis() - lastReconnectTime > RECONNECT_COOLDOWN) {
      lastReconnectTime = millis();
      Serial.println("⚠️ WiFi lost, reconnecting...");
      tftStatus("WiFi Lost!", "Reconnecting...", COLOR_RED, COLOR_GRAY);
      connectToWiFi();
    }
    return;  // skip everything else until WiFi is back
  }

  // --- Manual PNR entry via Serial ---
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    input.toUpperCase();

    // Basic PNR validation: 4–8 alphanumeric characters
    if (input.length() >= 4 && input.length() <= 8) {
      passengerPNR = input;
      Serial.println("\nPNR: " + passengerPNR);
      tftFetching(passengerPNR);

      if (millis() - lastRequestTime < REQUEST_DELAY)
        delay(REQUEST_DELAY);

      sendPNRRequest();
      lastRequestTime = millis();
      lastPollTime    = millis();  // reset poll timer after manual fetch
    } else if (input.length() > 0) {
      Serial.println("⚠️ Invalid PNR: must be 4–8 characters. Got: " + input);
      tftError("Invalid PNR", input.substring(0, 10));
    }
  }

  // --- Background poll (only if we already have a PNR loaded) ---
  if (passengerPNR.length() > 0 && millis() - lastPollTime > POLL_INTERVAL) {
    lastPollTime = millis();
    Serial.println("\n🔄 Background poll for: " + passengerPNR);
    sendPNRRequest();
  }
}
