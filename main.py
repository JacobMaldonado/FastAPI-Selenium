from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from extract import *
import os
from time import sleep
from selenium import webdriver
import qrcode
from PIL import Image
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys
from alright import WhatsApp
from fastapi.responses import FileResponse
import asyncio

app = FastAPI()
loged_in = False
tasks_is_running = False

def my_task():
    global loged_in, tasks_is_running
    tasks_is_running = True   
    log_in()
    loged_in = True

@app.get("/login")
async def login(background_tasks: BackgroundTasks):
    if not tasks_is_running:
        background_tasks.add_task(my_task)
    if loged_in:
        return {"message": "Success, Logged in"}
    else:
        return FileResponse("codigo_qr.png")

@app.post("/")
async def root(payload: dict, request: Request):
    import json
    fields = ["shipping_address","phone", "line_items", "total_price", "created_at"]
    print(request.headers)
    if payload['closed_at'] is None and len( payload["fulfillments"]) == 0:
        messenger = WhatsApp(get_driver())
        messenger.find_user(payload['phone'].replace('+',''))
        messenger.send_message(template_pedido(payload))
    elif len( payload["fulfillments"]) > 0 and payload['closed_at'] is None:
        print(json.dumps({k:v for k,v in payload["fulfillments"][0].items() if k != 'line_items'}, indent=4))
        messenger = WhatsApp(get_driver())
        messenger.find_user( "57" + next(filter(lambda x: x['name'] == "Teléfono", payload["note_attributes"])))
        messenger.send_message('hello')   
        sleep(5)
    elif payload['closed_at'] is not None:
        print(json.dumps({k:v for k,v in payload.items() if k in fields}, indent=4))
        messenger = WhatsApp(get_driver())
        messenger.find_user(payload['phone'].replace('+',''))
        messenger.send_message(template_pedido(payload))   
    return {'hello': 'world'}
    
@app.post("/test-message")
async def root2(payload: dict, request: Request):
    import json
    print(json.dumps(payload, indent=4))
    messenger = WhatsApp(get_driver())
    messenger.send_direct_message(payload['phone'], payload['message'], saved=False)
    sleep(5)
    return {'phone': payload['phone'], 'message': payload['message']}



# Inicializa el navegador (debes tener instalado ChromeDriver o el driver correspondiente)

def get_driver():
    service = ChromeService(executable_path=r'chromedriver.exe')
    chrome_options = webdriver.ChromeOptions()
    #chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    #chrome_options.headless = True
    if sys.platform == "win32":
        chrome_options.add_argument("--profile-directory=Default")
        chrome_options.add_argument("--user-data-dir=C:/Temp/ChromeProfile")
    else:
        chrome_options.add_argument("start-maximized")
        chrome_options.add_argument("--user-data-dir=./User_Data")
    driver = webdriver.Chrome(service=service,options=chrome_options)
    return driver

def log_in():
    driver = get_driver()

    # Abre la página web con el div que contiene los datos
    driver.get("https://web.whatsapp.com/")
    #input("Presiona Enter para continuar...")
    while True:
        try:
            element = WebDriverWait(driver, 10).until(
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
        except:
            print("Loged in")
            break
    driver.close()
    return True
    #input("Presiona Enter para continuar...")
    # Cierra el navegador
    

def template_pedido(info):
    telefono = next(filter(lambda x: x['name'] == "Teléfono", info["note_attributes"]))
    Direccion = next(filter(lambda x: x['name'] == "Dirección", info["note_attributes"]))
    Ciudad = next(filter(lambda x: x['name'] == "Ciudad", info["note_attributes"]))
    Nombre = next(filter(lambda x: x['name'] == "Nombre", info["note_attributes"]))
    Apellido = next(filter(lambda x: x['name'] == "Apellido", info["note_attributes"]))

    return f"""Hola, {Nombre} {Apellido}

            Te confirmamos que hemos recibido tu pedido en nuestra tienda con los siguientes detalles:

            📱 Teléfono: {telefono}
            📦 Producto: Producto
            🏠 Direccion: {Direccion}
            🏙️ Ciudad: {Ciudad}
            💳 Total: ${info['total_price']}

            SELECCIONA A LA OPCION DE TU INTERES

            1️⃣ CONFIRMAR PEDIDO
            2️⃣ CANCELAR PEDIDO
            3️⃣ MODIFICAR DATOS"""
