import os
import subprocess
import time
import hashlib
import logging
from jnius import autoclass

# Configuración del registro
logging.basicConfig(filename=os.path.join(os.getenv('HOME'), 'wifite_installer.log'), 
                     level=logging.INFO, 
                     format='%(asctime)s - %(message)s')

# Obtener el contexto de Android y WifiManager usando jnius
Context = autoclass('android.content.Context')
context = Context.getApplicationContext()
wifi_manager = context.getSystemService(Context.WIFI_SERVICE)

def run_command(command, shell=False):
    try:
        process = subprocess.run(command, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return process.stdout, process.stderr, process.returncode
    except Exception as e:
        logging.error(f"Error al ejecutar el comando {' '.join(command)}: {e}")
        return None, None, 1

def get_mac_address():
    # Obtener la dirección MAC del dispositivo
    wifi_info = wifi_manager.getConnectionInfo()
    mac = wifi_info.getMacAddress()
    if not mac:
        logging.warning("Dirección MAC no disponible. Es posible que los permisos no estén concedidos.")
        mac = "00:00:00:00:00:00"  # Dirección MAC predeterminada si no está disponible
    return mac

def check_internet_connection():
    logging.info("Verificando conexión a Internet...")
    stdout, stderr, returncode = run_command(["ping", "-c", "1", "8.8.8.8"])
    if returncode != 0:
        logging.error("No hay conexión a Internet. Saliendo...")
        exit(1)
    logging.info("Conexión a Internet verificada.")

def install_dependencies():
    logging.info("Instalando dependencias...")
    dependencies = [
        ["pkg", "update"],
        ["pkg", "install", "-y", "python", "nmap", "tshark", "tcpdump", "git", "wget"],
        ["pip", "install", "pyarmor"],
    ]
    for dep in dependencies:
        logging.info(f"Ejecutando: {' '.join(dep)}")
        stdout, stderr, returncode = run_command(dep)
        if returncode != 0:
            logging.error(f"Error: {stderr}")
        else:
            logging.info(stdout)

def clone_wifite():
    logging.info("Clonando Wifite desde GitHub...")
    url = "https://github.com/derv82/wifite2.git"
    if os.path.exists("wifite2"):
        logging.info("Wifite ya está clonado. Saltando clonación...")
        return
    stdout, stderr, returncode = run_command(["git", "clone", url])
    if returncode != 0:
        logging.error(f"Error: {stderr}")
    else:
        logging.info(stdout)

def enable_monitor_mode():
    logging.info("Habilitando modo monitor...")
    commands = [
        ["ifconfig", "wlan0", "down"],
        ["iwconfig", "wlan0", "mode", "monitor"],
        ["ifconfig", "wlan0", "up"],
    ]
    for cmd in commands:
        logging.info(f"Ejecutando: {' '.join(cmd)}")
        stdout, stderr, returncode = run_command(cmd)
        if returncode != 0:
            logging.error(f"Error: {stderr}")
            logging.warning("No se pudo habilitar el modo monitor. Continuando sin él.")
            break
        else:
            logging.info(stdout)

def download_dictionaries():
    logging.info("¿Deseas descargar diccionarios para ataques de diccionario? (s/n)")
    choice = input().strip().lower()
    if choice == 's':
        logging.info("Descargando diccionarios...")
        dictionaries = [
            "https://github.com/danielmiessler/SecLists/raw/master/Passwords/Common-Credentials/10-million-password-list-top-10000.txt",
            "https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt",
        ]
        for url in dictionaries:
            filename = url.split('/')[-1]
            if os.path.exists(filename):
                logging.info(f"El archivo {filename} ya existe. Saltando descarga.")
            else:
                logging.info(f"Descargando {filename}...")
                stdout, stderr, returncode = run_command(["wget", url, "-O", filename])
                if returncode != 0:
                    logging.error(f"Error: {stderr}")
                else:
                    logging.info(f"Descarga completada: {stdout}")

def create_lock_file():
    lock_file_path = os.path.join(os.getenv('HOME'), '.wifite_installed')
    with open(lock_file_path, 'w') as f:
        f.write("Wifite instalado")

def verify_integrity():
    # Verificar integridad del script
    hash_script = hashlib.sha256(open(__file__, "rb").read()).hexdigest()
    mac = get_mac_address()
    
    hash_file_path = os.path.join(os.getenv('HOME'), '.wifite_hash')
    if os.path.exists(hash_file_path):
        with open(hash_file_path, 'r') as f:
            stored_hash, stored_mac = f.read().strip().split(',')
        if hash_script != stored_hash or mac != stored_mac:
            logging.error("Error: El script ya se ha ejecutado en otro dispositivo")
            exit(1)
    else:
        # Crear archivo de hash con el hash actual y la MAC
        with open(hash_file_path, 'w') as f:
            f.write(f"{hash_script},{mac}")
        logging.info("Archivo de hash creado.")

def solicit_confirmacion():
    logging.info("¿Estás seguro de que deseas ejecutar este script?")
    respuesta = input("Sí (s) / No (n): ")
    if respuesta.lower() != "s":
        logging.info("Operación cancelada")
        exit(0)

def proteger_script():
    logging.info("Este script está protegido. No se puede copiar o modificar")
    logging.info("¿Deseas continuar? (s/n)")
    respuesta = input()
    if respuesta.lower() != "s":
        logging.info("Operación cancelada")
        exit(0)

def main():
    verify_integrity()
    solicit_confirmacion()
    proteger_script()

    lock_file_path = os.path.join(os.getenv('HOME'), '.wifite_installed')
    if os.path.exists(lock_file_path):
        logging.info("El instalador ya ha sido ejecutado. Saliendo...")
        return

    mac = get_mac_address()
    if not mac:
        logging.error("No se pudo obtener la dirección MAC. Saliendo...")
        return

    logging.info("Bienvenido al instalador de Wifite para Termux")
    check_internet_connection()
    install_dependencies()
    clone_wifite()
    enable_monitor_mode()
    download_dictionaries()
    logging.info("Instalación completada. Puedes ejecutar Wifite con 'python wifite2/wifite.py'")

    # Crear archivo de bloqueo
    create_lock_file()

    # Temporizador para eliminar el instalador
    logging.info("El instalador se eliminará en 3 segundos...")
    time.sleep(3)

    # Eliminar el script del instalador
    try:
        os.remove(__file__)
        logging.info("Instalador eliminado.")
    except Exception as e:
        logging.error(f"Error al eliminar el instalador: {e}")

if __name__ == "__main__":
    main()
