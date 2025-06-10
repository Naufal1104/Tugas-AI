import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler
import serial
import time
import sys

# --- Konfigurasi Serial Port ESP32 ---
SERIAL_PORT = 'COM9' # Sesuaikan dengan port serial Anda
BAUD_RATE = 115200
ser = None # Inisialisasi serial object sebagai None

# --- Konfigurasi Model ML ---
FEATURE_COLUMNS_CSV = ['Soil Moisture', 'Temperature', 'Air Humidity']
TARGET_COLUMN_CSV = 'Pump Data'

FEATURE_COLUMNS_PROCESSED = ['Soil_Moisture', 'Temperature', 'Humidity']
TARGET_COLUMN_PROCESSED = 'Motor_Status'

target_mapping = None
inverse_target_mapping = None

# --- Nama file CSV dataset ---
CSV_FILE_NAME = 'download.csv'

# --- 1. Memuat dan Mempersiapkan Dataset Historis ---
print("Memuat dataset historis...")
try:
    df = pd.read_csv(CSV_FILE_NAME)
    print("Dataset berhasil dimuat.")
    print("Kolom yang tersedia di CSV:", df.columns.tolist())

    required_columns = FEATURE_COLUMNS_CSV + [TARGET_COLUMN_CSV]
    if not all(col in df.columns for col in required_columns):
        missing_cols = [col for col in required_columns if col not in df.columns]
        print(f"ERROR: Kolom berikut tidak ditemukan di CSV Anda: {missing_cols}")
        print(f"Pastikan header di CSV Anda adalah: {FEATURE_COLUMNS_CSV + [TARGET_COLUMN_CSV]}")
        sys.exit("Silakan perbaiki header CSV Anda atau sesuaikan `FEATURE_COLUMNS_CSV` dan `TARGET_COLUMN_CSV` di skrip.")

    df.rename(columns={
        'Soil Moisture': 'Soil_Moisture',
        'Temperature': 'Temperature',
        'Air Humidity': 'Humidity',
        'Pump Data': 'Motor_Status'
    }, inplace=True)

    print("Kolom setelah rename:", df.columns.tolist())

    if df[TARGET_COLUMN_PROCESSED].dtype == 'object':
        unique_targets = df[TARGET_COLUMN_PROCESSED].unique()
        target_mapping = {val: i for i, val in enumerate(unique_targets)}
        inverse_target_mapping = {i: val for val, i in target_mapping.items()}
        df[TARGET_COLUMN_PROCESSED] = df[TARGET_COLUMN_PROCESSED].map(target_mapping)
        print(f"Target column '{TARGET_COLUMN_PROCESSED}' mapped to: {target_mapping}")
    else:
        print(f"Target column '{TARGET_COLUMN_PROCESSED}' is already numeric. No string mapping needed.")

    df.dropna(inplace=True)
    print("Ukuran dataset setelah dropna:", df.shape)

    X = df[FEATURE_COLUMNS_PROCESSED]
    y = df[TARGET_COLUMN_PROCESSED]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    print(f"Ukuran training set: {X_train.shape[0]} samples")
    print(f"Ukuran testing set: {X_test.shape[0]} samples")

    # --- 2. Melatih Kedua Model Machine Learning ---
    print("\nMelatih model Machine Learning (KNN dan Decision Tree)...")
    
    # Model KNN
    knn_model = KNeighborsClassifier(n_neighbors=5)
    knn_model.fit(X_train, y_train)
    
    # Model Decision Tree
    dt_model = DecisionTreeClassifier(random_state=42)
    dt_model.fit(X_train, y_train)

    # Evaluasi Model KNN
    y_pred_knn = knn_model.predict(X_test)
    print("\n--- Evaluasi Model KNN ---")
    print(f"Akurasi KNN: {accuracy_score(y_test, y_pred_knn):.2f}")
    print("\nLaporan Klasifikasi KNN:\n", classification_report(y_test, y_pred_knn))

    # Evaluasi Model Decision Tree
    y_pred_dt = dt_model.predict(X_test)
    print("\n--- Evaluasi Model Decision Tree ---")
    print(f"Akurasi Decision Tree: {accuracy_score(y_test, y_pred_dt):.2f}")
    print("\nLaporan Klasifikasi Decision Tree:\n", classification_report(y_test, y_pred_dt))
    
    print("\nKedua model ML siap digunakan.")

except FileNotFoundError:
    print(f"ERROR: File '{CSV_FILE_NAME}' tidak ditemukan. Pastikan file ada di direktori yang sama.")
    sys.exit()
except Exception as e:
    print(f"Terjadi kesalahan saat memproses dataset: {e}")
    sys.exit()

# --- Fungsi untuk Melakukan Prediksi dan Perbandingan Model ---
def run_prediction_and_compare(sensor_data_scaled):
    print("\n--- Analisis Model ---")
    
    # Prediksi dengan KNN
    start_time_knn = time.perf_counter()
    knn_prediction = knn_model.predict(sensor_data_scaled)
    end_time_knn = time.perf_counter()
    durasi_knn = end_time_knn - start_time_knn

    # Prediksi dengan Decision Tree
    start_time_dt = time.perf_counter()
    dt_prediction = dt_model.predict(sensor_data_scaled)
    end_time_dt = time.perf_counter()
    durasi_dt = end_time_dt - start_time_dt

    # Mendapatkan label prediksi
    predicted_motor_status_knn = knn_prediction[0]
    predicted_motor_status_dt = dt_prediction[0]

    if inverse_target_mapping:
        output_knn = inverse_target_mapping.get(predicted_motor_status_knn, f"Unknown ({predicted_motor_status_knn})")
        output_dt = inverse_target_mapping.get(predicted_motor_status_dt, f"Unknown ({predicted_motor_status_dt})")
    else:
        output_knn = predicted_motor_status_knn
        output_dt = predicted_motor_status_dt

    print(f"Output KNN : {output_knn} --- Durasi : {durasi_knn:.6f} detik")
    print(f"Output Decision Tree : {output_dt} --- Durasi : {durasi_dt:.6f} detik")

    if durasi_knn < durasi_dt:
        print(f"Waktu analisis tercepat : KNN (Durasi: {durasi_knn:.6f} detik)")
        return predicted_motor_status_knn # Mengembalikan prediksi KNN jika lebih cepat
    else:
        print(f"Waktu analisis tercepat : Decision Tree (Durasi: {durasi_dt:.6f} detik)")
        return predicted_motor_status_dt # Mengembalikan prediksi Decision Tree jika lebih cepat

# --- Main Program Loop (Dibungkus dalam try-finally) ---
try: # <--- Penambahan try block di sini
    while True:
        print("\n==============================================")
        print("Pilih Mode Input:")
        print("1. Otomatis (dari sensor ESP32)")
        print("2. Manual (input nilai sensor)")
        print("q. Keluar")
        mode_choice = input("Masukkan pilihan Anda (1/2/q): ").strip().lower()

        if mode_choice == 'q':
            break # Keluar dari program

        if mode_choice == '1': # Mode Otomatis
            print("\n--- Mode Input Otomatis (Menunggu data dari ESP32) ---")
            if ser is None: # Coba sambungkan serial jika belum tersambung
                try:
                    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
                    time.sleep(2) # Beri waktu agar koneksi serial stabil
                    print("Berhasil terhubung ke ESP32.")
                except serial.SerialException as e:
                    print(f"ERROR: Gagal terhubung ke ESP32 di {SERIAL_PORT}. Pesan: {e}")
                    print("Pastikan ESP32 terhubung dan port yang benar dipilih, serta tidak ada program lain yang menggunakan port ini.")
                    print("Tidak dapat melanjutkan mode otomatis tanpa koneksi serial.")
                    ser = None # Pastikan ser kembali ke None jika gagal
                    continue # Kembali ke pilihan mode

            if ser: # Lanjutkan jika serial terhubung
                print("Menunggu data dari ESP32...")
                try:
                    while True: # Loop untuk membaca data sensor
                        if ser.in_waiting > 0:
                            line = ser.readline().decode('utf-8').strip()

                            if line == "SENSOR_ERROR":
                                print(f"[{time.strftime('%H:%M:%S')}] ESP32 Error: Gagal membaca DHT dari sensor.")
                                continue
                            elif "Received command:" in line or "--> Motor is" in line:
                                print(f"[{time.strftime('%H:%M:%S')}] ESP32 Status: {line}")
                                continue

                            try:
                                soil_moisture_value, temperature_c, humidity_percent = map(float, line.split(','))

                                print(f"[{time.strftime('%H:%M:%S')}] Data Sensor Real-time:")
                                print(f"  Kelembaban Tanah (0-1000): {soil_moisture_value:.2f}")
                                print(f"  Suhu: {temperature_c:.2f} *C")
                                print(f"  Kelembaban Udara: {humidity_percent:.2f}%")

                                current_data_raw = pd.DataFrame([[soil_moisture_value, temperature_c, humidity_percent]],
                                                                columns=FEATURE_COLUMNS_PROCESSED)
                                current_data_scaled = scaler.transform(current_data_raw)
                                
                                # Lakukan prediksi dan perbandingan model
                                predicted_motor_status = run_prediction_and_compare(current_data_scaled)

                                # Mengirim perintah ke ESP32 berdasarkan prediksi yang lebih cepat
                                motor_command_to_send = ""
                                if predicted_motor_status == 1:
                                    motor_command_to_send = "MOTOR_ON"
                                elif predicted_motor_status == 0:
                                    motor_command_to_send = "MOTOR_OFF"

                                if motor_command_to_send:
                                    ser.write(f"{motor_command_to_send}\n".encode('utf-8'))
                                    print(f"  Mengirim perintah ke ESP32: '{motor_command_to_send}'")
                                else:
                                    print(f"  Tidak ada perintah motor yang dikirim untuk prediksi: {predicted_motor_status}")

                            except ValueError:
                                print(f"[{time.strftime('%H:%M:%S')}] ERROR: Format data sensor tidak valid atau tidak lengkap: {line}")
                            except Exception as e:
                                print(f"[{time.strftime('%H:%M:%S')}] ERROR saat memproses data: {e}")
                                
                except KeyboardInterrupt:
                    print("\nMode otomatis dihentikan.")
                except Exception as e:
                    print(f"\nTerjadi kesalahan di mode otomatis: {e}")
                finally:
                    # Tutup koneksi serial saat keluar dari loop otomatis
                    if ser:
                        ser.close()
                        print("Koneksi serial ditutup.")
                    ser = None # Reset ser ke None agar bisa disambungkan lagi jika mode 1 dipilih lagi
                
            print("Kembali ke menu utama.")
            
        elif mode_choice == '2': # Mode Manual
            print("\n--- Mode Input Manual ---")
            try:
                soil_m = float(input("Masukkan nilai Kelembaban Tanah (0-1000, e.g., 550.25): "))
                temp_c = float(input("Masukkan nilai Suhu (°C, e.g., 28.50): "))
                humid_p = float(input("Masukkan nilai Kelembaban Udara (%, e.g., 72.10): "))

                current_data_raw = pd.DataFrame([[soil_m, temp_c, humid_p]],
                                                columns=FEATURE_COLUMNS_PROCESSED)
                current_data_scaled = scaler.transform(current_data_raw)

                # Lakukan prediksi dan perbandingan model
                predicted_motor_status = run_prediction_and_compare(current_data_scaled)

                # Opsi: Kirim perintah ke ESP32 juga di mode manual jika terhubung
                if ser:
                    motor_command_to_send = ""
                    if predicted_motor_status == 1:
                        motor_command_to_send = "MOTOR_ON"
                    elif predicted_motor_status == 0:
                        motor_command_to_send = "MOTOR_OFF"

                    if motor_command_to_send:
                        ser.write(f"{motor_command_to_send}\n".encode('utf-8'))
                        print(f"  (Mode Manual) Mengirim perintah ke ESP32: '{motor_command_to_send}'")
                    else:
                        print(f"  (Mode Manual) Tidak ada perintah motor yang dikirim untuk prediksi: {predicted_motor_status}")
                else:
                    print("  (Koneksi ESP32 tidak aktif, tidak dapat mengirim perintah relay.)")

            except ValueError:
                print("Input tidak valid. Pastikan Anda memasukkan angka.")
            except Exception as e:
                print(f"Terjadi kesalahan saat input manual: {e}")

        else:
            print("Pilihan tidak valid. Silakan masukkan '1', '2', atau 'q'.")

except KeyboardInterrupt: # <--- Menangani KeyboardInterrupt untuk seluruh program
    print("\nProgram dihentikan oleh pengguna.")
finally: # <--- Finally block yang sesuai untuk try di atasnya
    if ser:
        ser.close()
        print("Koneksi serial ditutup.")
    print("Program selesai.")