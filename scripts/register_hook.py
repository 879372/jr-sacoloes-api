import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('FOCUSNFE_TOKEN')
PUBLIC_URL = os.getenv('PUBLIC_URL')
BASE_URL = "https://homologacao.focusnfe.com.br/v2"

def register_hook():
    if not TOKEN:
        print("Erro: FOCUSNFE_TOKEN não encontrado no .env")
        return
    
    url = f"{BASE_URL}/hooks"
    webhook_url = f"{PUBLIC_URL}/api/fiscal/webhooks/focusnfe/"
    
    payload = {
        "event": "nfe",
        "url": webhook_url
    }
    
    print(f"Registrando hook para: {webhook_url}")
    
    try:
        response = requests.post(url, json=payload, auth=(TOKEN, ""))
        if response.status_code in [200, 201]:
            print("Sucesso! Webhook registrado.")
            print(response.json())
        else:
            print(f"Erro ao registrar: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    register_hook()
