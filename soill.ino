#include <DHT.h>       // Library untuk sensor DHT
#include <DHT_U.h>     // Library pelengkap untuk sensor DHT

// Definisikan Pin sesuai PDF (Halaman 3)
const int SOIL_MOISTURE_PIN = 34; // Pin analog untuk sensor kelembaban tanah
const int DHT_PIN = 26;       // Pin digital untuk sensor DHT11/DHT22
const int RELAY_PIN = 27;         // Pin digital untuk mengontrol relay motor
const int LED1_PIN = 13;           // Pin digital untuk LED1 (status sensor aman)

// Definisikan Tipe Sensor DHT (DHT11 atau DHT22)
#define DHTTYPE DHT11 // Ganti dengan DHT22 jika Anda menggunakan DHT22

// Inisialisasi Sensor DHT
DHT dht(DHT_PIN, DHTTYPE);

// Kalibrasi Sensor Kelembaban Tanah (Nilai ADC)
// Sesuaikan nilai-nilai ini dengan kalibrasi sensor Anda
// Pastikan DRY_VALUE > WET_VALUE jika sensor mengeluarkan nilai ADC lebih tinggi saat kering.
const int WET_VALUE = 1700; // Contoh: Pembacaan ADC saat tanah sangat basah
const int DRY_VALUE = 4000; // Contoh: Pembacaan ADC saat tanah sangat kering

// Fungsi untuk memetakan nilai dari satu rentang ke rentang lain untuk float
float mapfloat(float x, float in_min, float in_max, float out_min, float out_max) {
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

void setup() {
  Serial.begin(115200); // Inisialisasi Serial Monitor
  while (!Serial);      // Tunggu Serial Monitor siap (khusus ESP32)

  dht.begin(); // Inisialisasi sensor DHT
  pinMode(RELAY_PIN, OUTPUT); // Set pin relay sebagai output
  pinMode(LED1_PIN, OUTPUT);  // Set pin LED1 sebagai output

  // Pastikan motor mati dan LED1 mati saat startup (HIGH untuk relay aktif LOW)
  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(LED1_PIN, LOW); // LED mati saat awal

  Serial.println("ESP32 siap. Mengirim data sensor...");
}

void loop() {
  // --- Baca Data Sensor Kelembaban Tanah ---
  int soilMoistureADC = analogRead(SOIL_MOISTURE_PIN);

  // Konversi nilai ADC ke rentang 0.00 hingga 1000.00
  float soilMoistureValue = mapfloat(soilMoistureADC, DRY_VALUE, WET_VALUE, 0.0, 1000.0);

  // Batasi nilai agar tetap dalam rentang 0.00 hingga 1000.00
  if (soilMoistureValue < 0.0) {
    soilMoistureValue = 0.0;
  } else if (soilMoistureValue > 1000.0) {
    soilMoistureValue = 1000.0;
  }

  // --- Baca Data Sensor Suhu dan Kelembaban Udara (DHT) ---
  float humidity = dht.readHumidity();
  float temperatureC = dht.readTemperature(); // Celcius

  // --- Kirim Data ke Serial Monitor dalam Format Komma-Separated ---
  // Format: "soil_moisture_value,temperature_celsius,humidity_percent"
  if (isnan(humidity) || isnan(temperatureC)) {
    Serial.println("SENSOR_ERROR"); // Kirim pesan error jika DHT gagal
    digitalWrite(LED1_PIN, LOW); // LED1 mati jika ada error
  } else {
    // Menggunakan Serial.print(value, num_decimal_places) untuk memformat output
    Serial.print(soilMoistureValue, 2); // Soil Moisture dengan 2 desimal (0.00 - 1000.00)
    Serial.print(",");
    Serial.print(temperatureC, 2);       // Suhu dengan 2 desimal
    Serial.print(",");
    Serial.println(humidity, 2);         // Kelembaban Udara dengan 2 desimal, dan newline
    digitalWrite(LED1_PIN, HIGH); // LED1 menyala jika pembacaan sensor aman
  }

  // --- Menerima Perintah dari Serial (dari Python) ---
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    Serial.print("Received command: ");
    Serial.println(command);

    if (command == "MOTOR_ON") {
      digitalWrite(RELAY_PIN, HIGH); // Nyalakan motor (sesuaikan dengan modul relay Anda, LOW/HIGH)
      Serial.println("--> Motor is ON.");
    } else if (command == "MOTOR_OFF") {
      digitalWrite(RELAY_PIN, LOW); // Matikan motor
      Serial.println("--> Motor is OFF.");
    } else {
      Serial.println("--> Unknown command received.");
    }
  }

  delay(2000); // Tunggu 2 detik sebelum pembacaan/pengiriman data sensor berikutnya
}