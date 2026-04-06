#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <SPI.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>

// ===== TFT PIN CONFIG =====
#define TFT_CS    10   // CS
#define TFT_AO     9   // AO (Data/Command)
#define TFT_RST    8   // RST
#define TFT_SDA   11   // SDA (MOSI)
#define TFT_SCK   12   // SCK (Clock)

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

// ===== WiFi =====
const char* ssid     = "Thiru";
const char* password = "thiru123";

// ===== Server =====
const char* serverUrl = "https://aerolinkers.pythonanywhere.com/sync";

// ===== Data =====
String deviceMAC;
String passengerPNR   = "";
unsigned long lastRequestTime = 0;
const unsigned long REQUEST_DELAY = 2000;

// ============================================================
// TFT HELPERS
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
// SCREENS
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
  delay(2000);
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
  delay(2000);
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

  // Header
  tft.fillRect(0, 0, 128, 18, COLOR_HEADER);
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(1);
  tft.setCursor(4, 5);
  tft.print("BOARDING PASS");

  // PNR - large
  tft.setTextColor(COLOR_YELLOW);
  tft.setTextSize(2);
  int pnrX = (128 - pnr.length() * 12) / 2;
  tft.setCursor(pnrX, 22);
  tft.print(pnr);

  tftDivider(42);

  // Passenger name
  tftField("PASSENGER", name, 46);

  tftDivider(68);

  // Flight + Seat
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

  // Boarding time
  tftField("BOARDING TIME", boarding, 100);

  // Footer
  tft.fillRect(0, 148, 128, 12, COLOR_HEADER);
  tft.setTextColor(COLOR_GRAY);
  tft.setTextSize(1);
  tft.setCursor(8, 151);
  tft.print("Have a safe flight!");
}

// ============================================================
// WIFI
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
// SEND REQUEST
// ============================================================

void sendPNRRequest() {
  if (WiFi.status() != WL_CONNECTED) {
    tftError("No WiFi", "Check connection");
    return;
  }

  WiFiClientSecure client;
  client.setInsecure();

  HTTPClient http;
  http.begin(client, serverUrl);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(10000);

  StaticJsonDocument<256> requestDoc;
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
  Serial.println("\n👉 Enter next PNR:");
}

// ============================================================
// HANDLE SUCCESS
// ============================================================

void handleSuccessResponse(HTTPClient* http) {
  String response = http->getString();
  Serial.println("📨 " + response);

  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, response);

  if (error) {
    tftError("Parse Error", "Bad JSON");
    return;
  }

  if (!doc.containsKey("name")     || !doc.containsKey("flight") ||
      !doc.containsKey("seat")     || !doc.containsKey("boarding_time")) {
    tftError("Data Error", "Missing fields");
    return;
  }

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
  Serial.println("==================================");

  tftBoardingPass(pnr, name, flight, seat, boarding);
  delay(8000);
  tftReady();
}

// ============================================================
// SETUP & LOOP
// ============================================================

void setup() {
  Serial.begin(115200);
  delay(500);

  tft.initR(INITR_BLACKTAB);  // Change to INITR_REDTAB if colors look wrong
  tft.setRotation(0);
  tft.fillScreen(COLOR_BG);

  tftStatus("AeroLinkers", "v1.2 Starting...", COLOR_ACCENT, COLOR_GRAY);
  delay(1500);

  Serial.println("\n=== AeroLinkers Smart Band ===");

  connectToWiFi();

  deviceMAC = WiFi.macAddress();
  Serial.println("MAC: " + deviceMAC);

  tftReady();
  Serial.println("\n👉 Enter PNR in Serial Monitor:");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️ WiFi lost, reconnecting...");
    tftStatus("WiFi Lost!", "Reconnecting...", COLOR_RED, COLOR_GRAY);
    connectToWiFi();
  }

  if (Serial.available()) {
    passengerPNR = Serial.readStringUntil('\n');
    passengerPNR.trim();
    passengerPNR.toUpperCase();

    if (passengerPNR.length() > 0) {
      Serial.println("\nPNR: " + passengerPNR);
      tftFetching(passengerPNR);

      if (millis() - lastRequestTime < REQUEST_DELAY)
        delay(REQUEST_DELAY);

      sendPNRRequest();
      lastRequestTime = millis();
    }
  }
}