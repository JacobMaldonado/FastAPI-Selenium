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

async def my_task():
    log_in()
    loged_in = True

@app.on_event("startup")
def on_startup():
    asyncio.create_task(my_task())
    print("Task started")

@app.get("/login")
async def login():

    if loged_in:
        return {"message": "Success, Logged in"}
    else:
        return FileResponse("codigo_qr.png")

@app.post("/")
async def root(payload: dict, request: Request):
    import json
    fields = ["shipping_address","phone", "line_items", "total_price", "created_at"]
    print(request.headers)
    if len( payload["fulfillments"]) > 0:
        print(json.dumps({k:v for k,v in payload["fulfillments"][0].items() if k != 'line_items'}, indent=4))
        messenger = WhatsApp(get_driver())
        messenger.find_user(payload['phone'])
        messenger.send_message('')   
    else:
        print(json.dumps({k:v for k,v in payload.items() if k in fields}, indent=4))
        messenger = WhatsApp(get_driver())
        messenger.find_user(payload['phone'].replace('+',''))
        messenger.send_message(template_pedido(payload))   
    return {'hello': 'world'}
    




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
    return f"""Hola, Nombre Apellido

            Te confirmamos que hemos recibido tu pedido en nuestra tienda con los siguientes detalles:

            📱 Teléfono: {info['phone']}
            📦 Producto: Producto
            🏠 Direccion: {info['shipping_address']['address1']}
            🏙️ Ciudad: {info['shipping_address']['city']}
            💳 Total: ${info['total_price']}

            SELECCIONA A LA OPCION DE TU INTERES

            1️⃣ CONFIRMAR PEDIDO
            2️⃣ CANCELAR PEDIDO
            3️⃣ MODIFICAR DATOS"""
