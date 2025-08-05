from openrgb import OpenRGBClient
from openrgb.utils import RGBColor, DeviceType
import time
import math
import threading
from noise import pnoise2
import paho.mqtt.client as paho
from paho import mqtt


client = OpenRGBClient()

flash = False
terminate= False
ringing = False

devices=client.devices
print(client.devices)
#client.clear() # Turns everything off
#client.devices[2].set_color(RGBColor(255,0,0))

# definizione palette dei colori
not_index=0
not_palettes = []
whatsapp=RGBColor(0, 255, 46) #0
not_palettes.append(whatsapp)
telegram=RGBColor(0,167,255) #1
not_palettes.append(telegram)
instagram=RGBColor(255,0,186) #2
not_palettes.append(instagram)
gmail=RGBColor(255,255,255) #3
not_palettes.append(gmail)
telefono=RGBColor(255,0,0) #4
not_palettes.append(telefono)

center = 21
brightness_array =[]
for i in range(60):
    brightness_array.append(0.0)

palette = [
    (20, 232, 30),
    (0, 234, 161),
    (70, 126, 213),
    (181, 61, 255),
    (255, 51, 204),
]

def on_log(client, userdata, level, buf):
    print(f"LOG: {buf}")



def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connesso con codice: {reason_code}")
    client.subscribe("Notification")

# Callback quando arriva un messaggio
def on_message(client, userdata, msg):
    global flash
    global not_index
    global ringing
    print(f"[{msg.topic}] {msg.payload.decode()}")
    match msg.payload.decode():
        case "com.whatsapp":
            flash=True
            not_index=0
        case "com.google.android.gm":
            flash=True
            not_index=3
        case "com.instagram.android":
            flash=True
            not_index=2
        case "org.telegram.messenger":
            flash=True
            not_index=1
        case "ringing": #il telefono sta squillando
            ringing=True
            flash=True
            not_index=4
        case "idle":
            ringing=False
        case "offhook":
            ringing=False


mqtt_client = paho.Client(
    client_id="OpenRGB_Client",
    userdata=None,
    protocol=paho.MQTTv311,
    callback_api_version=paho.CallbackAPIVersion.VERSION2
)
mqtt_client.on_log = on_log
mqtt_client.username_pw_set("mqtt_user", "Pisto3003")
mqtt_client.on_connect=on_connect
mqtt_client.on_message=on_message
mqtt_client.connect("192.168.1.100", 1883, 60) #3 valore tempo di keepalive

def interpolate_palette(t, luminosita):
    """t tra 0 e 1, restituisce colore RGB interpolato nella palette"""
    global palette
    n = len(palette)
    scaled = t * (n - 1)
    idx = int(scaled)
    frac = scaled - idx
    c1 = palette[idx]
    c2 = palette[(idx + 1) % n]  # loop della palette
    r = int((c1[0] + (c2[0] - c1[0]) * frac)*luminosita)
    g = int((c1[1] + (c2[1] - c1[1]) * frac)*luminosita)
    b = int((c1[2] + (c2[2] - c1[2]) * frac)*luminosita)
    return RGBColor(r, g, b)

def hsv_to_rgb(h, s, v):
    """Convert HSV [0-1] to RGBColor"""
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return RGBColor(int(r*255), int(g*255), int(b*255))

def noise_effect(step=0.05, speed=0.6, scale=0.25):
    """
    step: tempo tra aggiornamenti
    speed: velocità scorrimento nel noise
    scale: quanto variano i colori tra LED vicini
    """
    global flash
    global terminate
    global center
    global ringing
    t = 0
    t2=0.0
    while not terminate:
        index=0
        for dev in devices:
            colors=[]
            luminosita=1.0
            led_strip=False
            if dev.name.find("Addressable")!=-1: 
                luminosita=0.5
                led_strip=True
            for i, _ in enumerate(dev.leds):
                # Noise basato su posizione LED e tempo
                n = pnoise2(index * scale, t * speed)
                n = (n + 1) / 2  # normalizza 0-1
                # Mappo il noise su una tonalità (HSV)
                color=interpolate_palette(n, luminosita)

                # if led_strip and flash:                      #notifiche
                #     brightness = abs(math.sin(t2 * math.pi))*luminosita
                #     color=interpolate_palette(n, luminosita-brightness)
                #     color.red=color.red+int(not_palettes[not_index].red*brightness)
                #     color.green=color.green+int(not_palettes[not_index].green*brightness)
                #     color.blue=color.blue+int(not_palettes[not_index].blue*brightness)
                # else:
                #     color=interpolate_palette(n, luminosita)

                # if i >= center:
                #     color.red=255
                #     color.green=0
                #     color.blue=0

                colors.append(color)
                index+=1
            if(led_strip):
                for i in range(59,center, -1):
                    brightness_array[i]=brightness_array[i-1]
                    colors[i].red=int(colors[i].red*(luminosita*(1-brightness_array[i])))+int(not_palettes[not_index].red*brightness_array[i])
                    colors[i].green=int(colors[i].green*(luminosita*(1-brightness_array[i])))+int(not_palettes[not_index].green*brightness_array[i])
                    colors[i].blue=int(colors[i].blue*(luminosita*(1-brightness_array[i])))+int(not_palettes[not_index].blue*brightness_array[i])
                for i in range(0,center-1):
                    brightness_array[i]=brightness_array[i+1]
                    colors[i].red=int(colors[i].red*(luminosita*(1-brightness_array[i])))+int(not_palettes[not_index].red*brightness_array[i])
                    colors[i].green=int(colors[i].green*(luminosita*(1-brightness_array[i])))+int(not_palettes[not_index].green*brightness_array[i])
                    colors[i].blue=int(colors[i].blue*(luminosita*(1-brightness_array[i])))+int(not_palettes[not_index].blue*brightness_array[i])
                if flash:
                    brightness_array[center -1] = abs(math.sin(t2 * math.pi))
                    brightness_array[center]=brightness_array[center -1]
                #led center
                colors[center].red=int(colors[center].red*(luminosita*(1-brightness_array[center])))+int(not_palettes[not_index].red*brightness_array[center])
                colors[center].green=int(colors[center].green*(luminosita*(1-brightness_array[center])))+int(not_palettes[not_index].green*brightness_array[center])
                colors[center].blue=int(colors[center].blue*(luminosita*(1-brightness_array[center])))+int(not_palettes[not_index].blue*brightness_array[center])
                #led center -1
                colors[center-1].red=int(colors[center-1].red*(luminosita*(1-brightness_array[center-1])))+int(not_palettes[not_index].red*brightness_array[center-1])
                colors[center-1].green=int(colors[center-1].green*(luminosita*(1-brightness_array[center-1])))+int(not_palettes[not_index].green*brightness_array[center -1])
                colors[center-1].blue=int(colors[center-1].blue*(luminosita*(1-brightness_array[center-1])))+int(not_palettes[not_index].blue*brightness_array[center-1])

            #print(brightness_array)

            if led_strip and flash:
                if ringing==False and t2>=2.0:
                    flash=False
                    brightness_array[center -1]=0
                    brightness_array[center]=0
                    t2=0.0
                else: 
                    t2=t2%2.0
                    t2+=0.05
            dev.set_colors(colors)
        t += 0.05
        t = t % 1000.0  # 1000 di solito basta
        time.sleep(step)

thread = threading.Thread(target=noise_effect)
thread.start()
mqtt_client.loop_start()
try:
    while True:
        usr_input= input()
        # if int(usr_input)>= 0:
        #     center=int(usr_input)
        # else:
        flash=True 

        not_index=0
except KeyboardInterrupt:

    print("Chiusura...")
    mqtt_client.loop_stop()
    terminate = True
    thread.join()