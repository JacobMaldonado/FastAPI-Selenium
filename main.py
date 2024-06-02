from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from extract import *
import os
from time import sleep, time
from selenium import webdriver
import qrcode
from PIL import Image
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import sys
from alright import WhatsApp
from fastapi.responses import FileResponse
import traceback
import schedule
import threading

app = FastAPI()
loged_in = False
tasks_is_running = False
def get_driver():
    from webdriver_manager.chrome import ChromeDriverManager
    service = ChromeService(executable_path=ChromeDriverManager().install())
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--remote-debugging-port=9222')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0')
    #chrome_options.headless = True
    if sys.platform == "win32":
        chrome_options.add_argument("--profile-directory=Default")
        chrome_options.add_argument("--user-data-dir=C:/Temp/ChromeProfile")
    else:
        chrome_options.add_argument("start-maximized")
        chrome_options.add_argument("--user-data-dir=./User_Data")
    driver = webdriver.Chrome(service=service,options=chrome_options)
    return driver

driver = get_driver()
messenger = WhatsApp(driver)

def my_task():
    global loged_in, tasks_is_running
    tasks_is_running = True   
    log_in()
    loged_in = True


def check_messages() -> None:
    print("Checking for messages")
    if loged_in:
        print(messenger.get_list_of_messages())
    else:
        print("Not logged in")
    print("Done checking messages")

def run_continuously(interval=1):
    """Continuously run, while executing pending jobs at each
    elapsed time interval.
    @return cease_continuous_run: threading. Event which can
    be set to cease continuous run. Please note that it is
    *intended behavior that run_continuously() does not run
    missed jobs*. For example, if you've registered a job that
    should run every minute and you set a continuous run
    interval of one hour then your job won't be run 60 times
    at each interval but only once.
    """
    cease_continuous_run = threading.Event()

    class ScheduleThread(threading.Thread):
        @classmethod
        def run(cls):
            while not cease_continuous_run.is_set():
                schedule.run_pending()
                sleep(interval)

    continuous_thread = ScheduleThread()
    continuous_thread.start()
    return cease_continuous_run

schedule.every(10).seconds.do(check_messages)
#run_continuously()

@app.get("/login")
async def login(background_tasks: BackgroundTasks):
    print("login")
    if not tasks_is_running:
        print("adding task")
        background_tasks.add_task(my_task)
    if loged_in:
        return {"message": "Success, Logged in"}
    else:
        return FileResponse("codigo_qr.png")

@app.post("/")
async def root(payload: dict, request: Request, background_tasks: BackgroundTasks):
    print(payload)
    print(request.headers)
    background_tasks.add_task(process_webhook, payload)
    return {'hello': 'world'}

def process_webhook(payload):
    import json
    fields = ["shipping_address","phone", "line_items", "total_price", "created_at"]
    calling_code = next(filter(lambda x: x['name'] == "Country code", payload["note_attributes"]))['value']
    phone_number = next(filter(lambda x: x['name'] == "Teléfono", payload["note_attributes"]))['value']
    print(calling_code)
    full_number = "57" + phone_number
    messenger.find_user(full_number)
    
    sleep(1)

    if payload['closed_at'] == "None" and len( payload["fulfillments"]) == 0:
        print("initial message")
        send_message(driver, template_pedido(payload))
    elif len( payload["fulfillments"]) > 0 and payload['closed_at'] == "None":
        print("tracking recived")
        messenger.send_message(template_guia_creada(payload))
    elif payload['closed_at'] != "None":
        print("out to deliever")
        messenger.send_message(template_en_reparto(payload))
    sleep(5)
    return {'hello': 'world'}
    
@app.post("/test-message")
async def root2(payload: dict, request: Request):
    import json
    print(json.dumps(payload, indent=4))
    #messenger = WhatsApp(driver, 60)
    print("openning browser")
    messenger.find_user(payload['phone'])
    sleep(5)
    messenger.send_message( payload['message'])
    print("message sent")
    sleep(5)
    return {'phone': payload['phone'], 'message': payload['message']}



# Inicializa el navegador (debes tener instalado ChromeDriver o el driver correspondiente)



def log_in():
    #driver = get_driver()
    print("running log in")
    # Abre la página web con el div que contiene los datos
    driver.get("https://web.whatsapp.com/")
    #input("Presiona Enter para continuar...")
    while True:
        try:
            element = WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.CLASS_NAME, "_akau"))
                        )
            # Encuentra el div y extrae el texto
            sleep(15)
            data_div = driver.find_element(By.CLASS_NAME,"_akau")
            # get attribute data-ref
            data_text = data_div.get_attribute("data-ref")
            print(data_text)

            # Genera el código QR
            img = qrcode.make(data_text)

            # Guarda la imagen
            img.save("codigo_qr.png")
            sleep(1)
        except Exception as bug:
            print(traceback.format_exc())
            print("Loged in")
            break
    #driver.close()
    return True
    #input("Presiona Enter para continuar...")
    # Cierra el navegador
    
def send_message(driver, message):
    """send_message ()
        Sends a message to a target user

        Args:
            message ([type]): [description]
        """
    try:
        inp_xpath = '//*[@id="main"]/footer/div/div/span[2]/div/div[2]/div/div/div'
        input_box = WebDriverWait(driver, 600).until(
            EC.presence_of_element_located((By.XPATH, inp_xpath))
        )
        for line in message.split("\n"):
            if ":three" in line:
                input_box.send_keys(":three")
                ActionChains(driver).key_down(Keys.ARROW_RIGHT).key_up(Keys.ARROW_RIGHT).key_down(Keys.TAB).key_up(Keys.TAB).perform()    
                line = line.replace(":three", "")
            print(line)
            input_box.send_keys(line)
            ActionChains(driver).key_down(Keys.SHIFT).key_down(
                Keys.ENTER
            ).key_up(Keys.ENTER).key_up(Keys.SHIFT).perform()
        input_box.send_keys(Keys.ENTER)
        print(f"Message sent successfuly ")
    except Exception as bug:
        print(bug)

def paste_content(driver, el, content):
    driver.execute_script("arguments[0].innerHTML = '{}'".format(content),el)

def template_pedido(info):
    telefono = next(filter(lambda x: x['name'] == "Teléfono", info["note_attributes"]))['value']
    Direccion = next(filter(lambda x: x['name'] == "Dirección", info["note_attributes"]))['value']
    Ciudad = next(filter(lambda x: x['name'] == "Ciudad", info["note_attributes"]))['value']
    Nombre = next(filter(lambda x: x['name'] == "Nombre", info["note_attributes"]))['value']
    Apellido = next(filter(lambda x: x['name'] == "Apellido", info["note_attributes"]))['value']

    return f"""
Hola, {Nombre} {Apellido}

Te confirmamos que hemos recibido tu pedido en nuestra tienda con los siguientes detalles:

:mobile phone\t Teléfono: {telefono}
:package\t Producto: {info['line_items'][0]['title']}
:house\t Direccion: {Direccion}
:citys\t Ciudad: {Ciudad}
:card\t Total: ${info['total_price']}

SELECCIONA A LA OPCION DE TU INTERES

:one\t CONFIRMAR PEDIDO
:two\t CANCELAR PEDIDO
:three MODIFICAR DATOS"""


def template_guia_creada(info):
    telefono = next(filter(lambda x: x['name'] == "Teléfono", info["note_attributes"]))['value']
    Direccion = next(filter(lambda x: x['name'] == "Dirección", info["note_attributes"]))['value']
    Ciudad = next(filter(lambda x: x['name'] == "Ciudad", info["note_attributes"]))['value']
    Nombre = next(filter(lambda x: x['name'] == "Nombre", info["note_attributes"]))['value']
    Apellido = next(filter(lambda x: x['name'] == "Apellido", info["note_attributes"]))['value']
    guia_info = next(filter(lambda x: x['name'] == "_dropi_shipping_guide", info["note_attributes"]))['value']
    guia = guia_info.replace("# Guia: ", "").split(" ")[0]
    transportadora = guia_info.split(" ")[-1]

    return f"""
Hola {Nombre} {Apellido} :person raising\t

Queremos informarte hemos preparado tu envío, y ahora está en ruta con el número de guía {guia} a través de la transportadora {transportadora} :delivery\t

Recuerda que el tiempo estimado de entrega es de 2 a 4 días hábiles:package\t

Por favor mantente atento a este chat, donde te proporcionaremos más detalles sobre tu pedido.:mobile phone with arrow\t

:writing hand\tPuedes hacer un seguimiento en tiempo real de tu paquete a través de este enlace:backhand index pointing down\t:backhand index pointing down\t

https://interrapidisimo.com"""

def obtener_enlace_por_transportadora(transportadora):
    if transportadora == "INTERRAPIDISIMO":
        return "https://interrapidisimo.com"
    elif transportadora == "COORDINADORA":
        return "https://coordinadora.com/rastreo/rastreo-de-guia/"
    elif transportadora == "ENVIA":
        return "https://envia.co/"
    else:
        return ""
    


def template_en_reparto(info):
    telefono = next(filter(lambda x: x['name'] == "Teléfono", info["note_attributes"]))['value']
    Direccion = next(filter(lambda x: x['name'] == "Dirección", info["note_attributes"]))['value']
    Ciudad = next(filter(lambda x: x['name'] == "Ciudad", info["note_attributes"]))['value']
    Nombre = next(filter(lambda x: x['name'] == "Nombre", info["note_attributes"]))['value']
    Apellido = next(filter(lambda x: x['name'] == "Apellido", info["note_attributes"]))['value']
    total = info['total_price']
    return f"""
Hola {Nombre} {Apellido} :person raising\t

¡Prepárate para recibir tu pedido! Informamos que estamos a punto de entregar tu pedido:package\t Hoy está en Reparto en tu Ciudad :delivery\t

Recuerda que si tu pedido es CONTRAENTREGA debes tener el valor de ${total} en efectivo. Al momento de recibir.

En caso de no estar en casa, por favor autorizar a alguien de recibir :grinning face\t
"""