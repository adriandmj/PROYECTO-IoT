import paho.mqtt.client as mqtt
import telepot
import json
import time
import ssl
import csv
from datetime import datetime

# --- TUS DATOS ---
TOKEN = '8251934467:AAFmLziBdweKuKpkpnqOA4cSvYCK9nPuGiU'
CHAT_ID = 1569528013
TOPIC = "proyecto/salud/equipo_adri/datos/oxigeno"
BROKER = "broker.emqx.io"

ultima_alerta = 0 
archivo_excel = "historial_salud.csv"

# Configuración SSL para Telegram
context = ssl._create_unverified_context()
telepot.api._pools['default'] = telepot.api.urllib3.PoolManager(ssl_context=context)
bot = telepot.Bot(TOKEN)

# Función para guardar en Excel
def guardar_en_excel(bpm, spo2):
    fecha = datetime.now().strftime('%Y-%m-%d')
    hora = datetime.now().strftime('%H:%M:%S')
    try:
        with open(archivo_excel, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([fecha, hora, bpm, spo2])
    except PermissionError:
        print("⚠️ No se pudo guardar en Excel: El archivo está abierto.")

# Crear el encabezado del Excel si no existe
try:
    with open(archivo_excel, mode='a', newline='') as file:
        if file.tell() == 0:
            writer = csv.writer(file)
            writer.writerow(["Fecha", "Hora", "BPM", "SpO2"])
except PermissionError:
    print("⚠️ Error inicial: Cierra el Excel antes de empezar.")

def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("✅ Conectado y listo para monitorear")
        client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    global ultima_alerta
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        bpm = data.get("bpm")
        spo2 = data.get("spo2")

        guardar_en_excel(bpm, spo2)
        
        tiempo_actual = time.time()
        
        if (tiempo_actual - ultima_alerta) > 20:
            status_emoji = "🟢"
            nota_medica = ""
            
            # Ajuste de mensajes de alerta
            if bpm < 50:
                status_emoji = "⚠️"
                nota_medica = "\n\n🚨 *ALERTA: Frecuencia cardíaca BAJA.* Por favor, revise sus niveles nuevamente y mantenga la calma."
                nota_medica += "\n\n📞 *Contacto de Emergencia:* [Llamar al 911](tel:911)"
            elif bpm > 120:
                status_emoji = "🆘"
                nota_medica = "\n\n🚨 *ALERTA: Frecuencia cardíaca ALTA.* Se recomienda reposar y consultar a un médico si persiste."
                nota_medica += "\n\n📞 *Contacto de Emergencia:* [Llamar al 911](tel:911)"
            
            if spo2 < 90:
                nota_medica += "\n📉 *Nivel de oxígeno bajo.*"
            
            texto_alerta = (
                f"{status_emoji} *REPORTE DE SALUD* {status_emoji}\n\n"
                f"💓 Pulso: {bpm} BPM\n"
                f"🩸 Oxígeno: {spo2}%\n"
                f"⏰ Hora: {datetime.now().strftime('%H:%M:%S')}"
                f"{nota_medica}"
            )
            
            bot.sendMessage(CHAT_ID, texto_alerta, parse_mode='Markdown')
            print(f"🚀 [TELEGRAM] Alerta enviada con {bpm} BPM.")
            ultima_alerta = tiempo_actual
        else:
            print(f"⏳ Dato ({bpm} BPM) guardado en Excel. Esperando para Telegram...")
            
    except Exception as e:
        print(f"⚠️ Error en procesamiento: {e}")

# Configuración MQTT
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

print("🔗 Puente activado. Iniciando monitoreo...")

# Bucle principal con protección contra cierres
try:
    while True:
        try:
            client.connect(BROKER, 1883, 60)
            client.loop_forever()
        except Exception as e:
            print(f"❌ Conexión perdida: {e}. Reintentando en 5 segundos...")
            time.sleep(5)
except KeyboardInterrupt:
    print("\n🛑 Sistema apagado por el usuario.")