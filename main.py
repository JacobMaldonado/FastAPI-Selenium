import asyncio
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
import phonenumbers

app = FastAPI()
loged_in = False
tasks_is_running = False
orders_db = {}

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
        try:
            messages = messenger.get_list_of_messages()
            messages_to_reply = list(filter(lambda x: x['message'] == "1" or x['message'] == "2" or x['message'] == "3" , messages))
            print(messages_to_reply)
            for message in messages_to_reply:
                messenger.find_user(message["sender"].replace("+", "").replace(" ", ""))
                if message['message'] == "1":
                    send_message(driver, template_aceptado())
                elif message['message'] == "2":
                    send_message(driver, template_cancelado())
                elif message['message'] == "3":
                    send_message(driver, template_modificar())
        except Exception as bug:
            print(bug)
    else:
        print("Not logged in")
    print("Done checking messages")

class BackgroundTask:
    def __init__(self):
        pass

    async def my_task(self):
        while True:
            await asyncio.sleep(20)
            check_messages()

bgtask = BackgroundTask()

@app.on_event('startup')
def on_startup():
    #asyncio.ensure_future(bgtask.my_task())
    pass

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
    
@app.post("/pedidos-preliminares")
async def pedidos_preliminares(payload: dict, request: Request):
    
    telefono = next(filter(lambda x: x['name'] == "Teléfono", payload["note_attributes"]), None)
    if telefono is None:
        return {"message": "No phone number found"}
    telefono = telefono['value']
    messenger.find_user(telefono)
    sleep(5)
    send_message2(driver, template_pedido(payload))

    return {'hello': 'world'}


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
    region = next(filter(lambda x: x['name'] == "Country code", payload["note_attributes"]))['value']
    print(calling_code)
    full_number = str(phonenumbers.country_code_for_region(region)) + phone_number
    messenger.find_user(full_number)
    
    sleep(1)

    if (payload['closed_at'] == "None" or payload['closed_at'] == None) and len( payload["fulfillments"]) == 0:
        if payload["id"] in orders_db:
            return
        print("initial message")
        send_message2(driver, template_pedido(payload))
        orders_db[payload["id"]] = "INITIAL_MESSAGE"
    elif len( payload["fulfillments"]) > 0 and (payload['closed_at'] == "None" or payload['closed_at'] == None):
        if payload["id"] not in orders_db or orders_db[payload["id"]] != "INITIAL_MESSAGE":
            return
        print("tracking recived")
        send_message2(driver,template_guia_creada(payload))
        orders_db[payload["id"]] = "TRACKING_MESSAGE"
    elif payload['closed_at'] != "None" or payload['closed_at'] != None :
        if payload["id"] not in orders_db or orders_db[payload["id"]] != "TRACKING_MESSAGE":
            return
        print("out to deliever")
        send_message2(driver,template_en_reparto(payload))
        orders_db[payload["id"]] = "OUT_TO_DELIEVER"
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
    send_message2(driver, payload['message'])
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
                input_box.send_keys(":number")
                ActionChains(driver).key_down(Keys.ARROW_RIGHT).key_up(Keys.ARROW_RIGHT).key_down(Keys.ARROW_RIGHT).key_up(Keys.ARROW_RIGHT).key_down(Keys.ARROW_RIGHT).key_up(Keys.ARROW_RIGHT).key_down(Keys.TAB).key_up(Keys.TAB).perform()    
                line = line.replace(":three", "")
            if ":two" in line:
                input_box.send_keys(":number")
                ActionChains(driver).key_down(Keys.ARROW_RIGHT).key_up(Keys.ARROW_RIGHT).key_down(Keys.ARROW_RIGHT).key_up(Keys.ARROW_RIGHT).key_down(Keys.TAB).key_up(Keys.TAB).perform()  
                line = line.replace(":two", "")
            if ":one" in line:
                input_box.send_keys(":number")
                ActionChains(driver).key_down(Keys.ARROW_RIGHT).key_up(Keys.ARROW_RIGHT).key_down(Keys.TAB).key_up(Keys.TAB).perform()  
                line = line.replace(":one", "")
            if ":writing hand" in line:
                input_box.send_keys(":writing hand")
                ActionChains(driver).key_down(Keys.RETURN).key_up(Keys.RETURN).perform()    
                line = line.replace(":writing hand", "")
            while ":down" in line:
                input_box.send_keys(line[:line.find(":down")])
                input_box.send_keys(":down")
                ActionChains(driver).key_down(Keys.ARROW_RIGHT).key_up(Keys.ARROW_RIGHT).key_down(Keys.TAB).key_up(Keys.TAB).perform()        
                line = line[line.find(":down") + len(":down"):]
            while ":person raising" in line:
                input_box.send_keys(line[:line.find(":person raising")])
                input_box.send_keys(":person raising")
                ActionChains(driver).key_down(Keys.TAB).key_up(Keys.TAB).perform()        
                line = line[line.find(":person raising") + len(":person raising"):]
            print(line)
            #input_box.send_keys(line)
            driver.execute_script("arguments[0].innerHTML = '{}'".format(line),input_box)
            input_box.send_keys('.')
            input_box.send_keys(Keys.BACKSPACE)
            ActionChains(driver).key_down(Keys.SHIFT).key_down(
                Keys.ENTER
            ).key_up(Keys.ENTER).key_up(Keys.SHIFT).perform()
        input_box.send_keys(Keys.ENTER)
        print(f"Message sent successfuly ")
    except Exception as bug:
        print(bug)

def send_message2(driver, message):
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
        paste_content(driver, input_box, message)
        input_box.send_keys(Keys.ENTER)
        print(f"Message sent successfuly ")
    except Exception as bug:
        print(bug)


def template_pedido(info):
    telefono = next(filter(lambda x: x['name'] == "Teléfono", info["note_attributes"]))['value']
    Direccion = next(filter(lambda x: x['name'] == "Dirección", info["note_attributes"]))['value']
    Ciudad = next(filter(lambda x: x['name'] == "Ciudad", info["note_attributes"]))['value']
    Nombre = next(filter(lambda x: x['name'] == "Nombre", info["note_attributes"]))['value']
    Apellido = next(filter(lambda x: x['name'] == "Apellido", info["note_attributes"]))['value']

    return f"""
Hola, *{Nombre}* *{Apellido}*

Te confirmamos que hemos recibido tu pedido en nuestra tienda con los siguientes detalles:

📱 *Teléfono*: {telefono}
📦 *Producto*: { ' + '.join(list(map(lambda x : x['title'], info['line_items'])))}
🏠 *Direccion*: {Direccion}
🏙️ *Ciudad*: {Ciudad}
💳 *Total*: *${info['total_price']}*

*SELECCIONA A LA OPCION DE TU INTERES*

1️⃣ *CONFIRMAR PEDIDO*
2️⃣ *CANCELAR PEDIDO*
3️⃣ *MODIFICAR DATOS*"""


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
Hola *{Nombre}* *{Apellido}* 🙋 

Queremos informarte hemos preparado tu envío, y ahora está en ruta con el número de guía *{guia}* a través de la transportadora *{transportadora}* 🚚

Recuerda que el tiempo estimado de entrega es de 2 a 4 días hábiles 📦

Por favor mantente atento a este chat, donde te proporcionaremos más detalles sobre tu pedido.📲

✍️ Puedes hacer un seguimiento en tiempo real de tu paquete a través de este enlace 👇🏻👇🏻 \n\n{obtener_enlace_por_transportadora(transportadora)}\n"""

def obtener_enlace_por_transportadora(transportadora):
    if transportadora == "INTERRAPIDISIMO":
        return "https://interrapidisimo.com"
    elif transportadora == "COORDINADORA":
        return "https://coordinadora.com/rastreo/rastreo-de-guia/"
    elif transportadora == "ENVIA":
        return "https://envia.co/"
    elif transportadora == "SERVIENTREGA":
        return "https://www.servientrega.com"
    elif transportadora == "TCC":
        return "https://www.tcc.com.co"
    elif transportadora == "DOMINA":
        return "https://www.domina.com.co/"
    elif transportadora == "99MINUTOS":
        return "https://www.99minutos.com/"
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
Hola *{Nombre}* *{Apellido}* 🙋


¡Prepárate para recibir tu pedido! Informamos que estamos a punto de entregar tu pedido📦 Hoy está en Reparto en tu Ciudad 🚛

Recuerda que si tu pedido es *CONTRAENTREGA* debes tener el valor de *${total}* en efectivo. Al momento de recibir.

*En caso de no estar en casa, por favor autorizar a alguien de recibir* 😃
"""

def template_aceptado():
    return """*Muchas gracias por confirmar tu pedido* 🥰 procederemos a despacharlo de inmediato 🚚 Cualquier inconveniente por aquí estaremos ✨"""

def template_cancelado():
    return """¡Vaya, qué lástima escuchar eso! ¿Te importaría contarme qué te hizo cambiar de opinión? Estoy aquí para ayudar y mejorar tu experiencia en lo que pueda."""

def template_modificar():
    return """Me regalas los datos correctos, por favor 😊 O indícanos si quieres que te llamemos 📞"""

def template_orden_pendiente(payload):
    nombre = next(filter(lambda x: x['name'] == "Nombre", payload["note_attributes"]))['value']
    apellido = next(filter(lambda x: x['name'] == "Apellido", payload["note_attributes"]))['value']
    link = payload['invoice_url']
    productos = list(map(lambda x : x['title'], payload['line_items']))
    return f"""Hola, *{nombre}* *{apellido}* Dejaste un pedido pendiente de {' + '.join(productos)}, completalo para recibir tus productos {link}"""

def paste_content(driver, el, content):
    driver.execute_script(
      f'''
const text = `{content}`;
const dataTransfer = new DataTransfer();
dataTransfer.setData('text', text);
const event = new ClipboardEvent('paste', {{
  clipboardData: dataTransfer,
  bubbles: true
}});
arguments[0].dispatchEvent(event)
''',
      el)
