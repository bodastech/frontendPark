#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <ArduinoJson.h>

// Network Configuration
const char* ssid = "RSI_BNA";       // Replace with your WiFi SSID
const char* password = "rsibna123";  // Replace with your WiFi password
const char* serverUrl = "http://192.168.2.6:5051/api";

// Pin Definitions
const int buttonPin = 2;     // Pin for the push button
const int relayPin = 3;      // Pin for the relay control
const int ledPin = LED_BUILTIN;  // Built-in LED for status indication

// Variables
bool buttonState = HIGH;      // Current state of the button (HIGH with pull-up)
bool lastButtonState = HIGH;  // Previous state of the button
bool isProcessing = false;    // Flag to prevent multiple requests
unsigned long lastDebounceTime = 0;  // Last time the button state changed
unsigned long debounceDelay = 50;    // Debounce delay in milliseconds

// JSON document for API communication
StaticJsonDocument<200> doc;

void setup() {
  // Initialize Serial communication
  Serial.begin(115200);
  
  // Configure pin modes
  pinMode(buttonPin, INPUT_PULLUP);  // Enable internal pull-up resistor
  pinMode(relayPin, OUTPUT);         // Relay as output
  pinMode(ledPin, OUTPUT);           // LED as output
  
  // Ensure the relay is initially off
  digitalWrite(relayPin, LOW);
  digitalWrite(ledPin, HIGH);  // LED off initially (active LOW)
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nConnected to WiFi");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // Read the current state of the button
  bool reading = digitalRead(buttonPin);
  
  // Check if the button state has changed
  if (reading != lastButtonState) {
    lastDebounceTime = millis();
  }
  
  // If the debounce time has passed, update the button state
  if ((millis() - lastDebounceTime) > debounceDelay) {
    if (reading != buttonState) {
      buttonState = reading;
      
      // If the button was pressed (falling edge) and not currently processing
      if (buttonState == LOW && !isProcessing) {
        isProcessing = true;
        processExit();
      }
    }
  }
  
  // Update the last button state
  lastButtonState = reading;
}

void processExit() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    
    // Blink LED to indicate processing
    digitalWrite(ledPin, LOW);
    
    // Get the ticket data from serial (from the main computer/scanner)
    String ticketData = "";
    while (Serial.available()) {
      char c = Serial.read();
      if (c == '\n') break;
      ticketData += c;
    }
    
    // If no ticket data, use a default test ticket
    if (ticketData.length() == 0) {
      ticketData = "TEST123";  // For testing purposes
    }
    
    // Create JSON payload
    doc.clear();
    doc["tiket"] = ticketData;
    doc["plat"] = "";  // Plate number can be empty for exit gate
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    // Configure HTTP request
    http.begin(String(serverUrl) + "/keluar");
    http.addHeader("Content-Type", "application/json");
    
    // Send POST request
    int httpResponseCode = http.POST(jsonString);
    
    if (httpResponseCode == 200) {
      String response = http.getString();
      
      // Parse response
      DeserializationError error = deserializeJson(doc, response);
      
      if (!error) {
        bool success = doc["success"];
        if (success) {
          // Open the gate
          digitalWrite(relayPin, HIGH);
          delay(500);  // Keep the relay on for 500ms
          digitalWrite(relayPin, LOW);
          
          // Blink LED twice to indicate success
          for (int i = 0; i < 2; i++) {
            digitalWrite(ledPin, LOW);
            delay(200);
            digitalWrite(ledPin, HIGH);
            delay(200);
          }
        } else {
          // Error indicated by rapid LED blinks
          for (int i = 0; i < 5; i++) {
            digitalWrite(ledPin, LOW);
            delay(100);
            digitalWrite(ledPin, HIGH);
            delay(100);
          }
        }
      }
    } else {
      Serial.print("Error on HTTP request: ");
      Serial.println(httpResponseCode);
      
      // Error indicated by rapid LED blinks
      for (int i = 0; i < 5; i++) {
        digitalWrite(ledPin, LOW);
        delay(100);
        digitalWrite(ledPin, HIGH);
        delay(100);
      }
    }
    
    http.end();
    digitalWrite(ledPin, HIGH);  // Turn LED off
  }
  
  isProcessing = false;  // Reset processing flag
} 