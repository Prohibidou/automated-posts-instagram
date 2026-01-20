import os
import sys
import time
import glob
import shutil
import requests
import pyautogui
import pyperclip
from pathlib import Path
from datetime import datetime

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Webdriver Manager imports
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

# Configuración
DESKTOP_PATH = os.path.join(os.environ['USERPROFILE'], 'Desktop')  # Para guardar resultados
IMAGES_PATH = os.path.join(os.environ['USERPROFILE'], 'OneDrive', 'Imágenes')  # Para buscar imágenes
TEMP_IMAGES_PATH = r"C:\temp\gemini_images"  # Ruta sin caracteres especiales para upload
IMAGE_EXTENSIONS = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.webp']
PROMPT = "traduce el texto de la imagen, a español"
GEMINI_URL = "https://gemini.google.com/"

def copy_to_safe_path(image_path):
    """Copia la imagen a una ruta sin caracteres especiales y retorna la nueva ruta."""
    # Crear carpeta temporal si no existe
    os.makedirs(TEMP_IMAGES_PATH, exist_ok=True)
    
    # Generar nombre de archivo sin caracteres especiales
    original_name = os.path.basename(image_path)
    # Reemplazar caracteres problemáticos
    safe_name = original_name.encode('ascii', 'ignore').decode('ascii')
    if not safe_name:
        safe_name = f"image_{int(time.time())}.png"
    
    # Copiar archivo
    safe_path = os.path.join(TEMP_IMAGES_PATH, safe_name)
    shutil.copy2(image_path, safe_path)
    
    return safe_path

def get_desktop_images():
    """Obtiene todas las imágenes de la carpeta Imágenes (incluyendo subcarpetas)."""
    images = []
    for ext in IMAGE_EXTENSIONS:
        # Buscar en la carpeta principal
        images.extend(glob.glob(os.path.join(IMAGES_PATH, ext)))
        # Buscar en subcarpetas
        images.extend(glob.glob(os.path.join(IMAGES_PATH, '**', ext), recursive=True))
    # Eliminar duplicados
    images = list(set(images))
    return images

import subprocess

def copy_image_to_clipboard(image_path):
    """Copia la imagen al portapapeles usando PowerShell (funciona como copiar archivo en Explorer)."""
    try:
        # Comando PowerShell para copiar archivo al clipboard
        cmd = f"Set-Clipboard -Path '{image_path}'"
        subprocess.run(["powershell", "-Command", cmd], shell=True, check=True)
        return True
    except Exception as e:
        print(f"⚠️ Error copiando al portapapeles: {e}")
        return False

# ... (imports)

def setup_chrome_driver():
    chrome_options = Options()
    
    # Usar un perfil separado para evitar conflictos y bloqueos de automatización
    profile_path = os.path.join(os.environ['USERPROFILE'], '.gemini_translator_profile')
    if not os.path.exists(profile_path):
        os.makedirs(profile_path)
    print(f"   📂 Usando perfil dedicado: {profile_path}")
    
    chrome_options.add_argument(f"--user-data-dir={profile_path}")
    
    # Flags estándar para automatización estable
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Configurar descargas al escritorio
    prefs = {
        "download.default_directory": DESKTOP_PATH,
        "download.prompt_for_download": False,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Usar webdriver-manager
    service = ChromeService(ChromeDriverManager().install())
    
    print("   🔧 Creando driver de Chrome...")
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("   ✅ Chrome iniciado correctamente.")
        return driver
    except Exception as e:
        print(f"\n❌ Error iniciando Chrome: {e}")
        sys.exit(1)

def wait_and_click(driver, by, value, timeout=30):
    """Espera un elemento y hace clic en él."""
    element = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, value))
    )
    time.sleep(0.5)
    element.click()
    return element

def wait_for_element(driver, by, value, timeout=30):
    """Espera a que un elemento esté presente."""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )

from selenium.webdriver.common.action_chains import ActionChains

def navigate_to_image_tool(driver):
    """Navega a Gemini App y selecciona la herramienta 'Crear imagen'."""
    print("🌐 Abriendo Gemini App...")
    driver.get("https://gemini.google.com/app")
    time.sleep(5)
    
    # Cerrar popups iniciales
    try:
        close_btns = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Cerrar') or contains(@aria-label, 'Close') or contains(text(), 'Entendido') or contains(text(), 'Got it')]")
        for btn in close_btns:
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.5)
    except: pass
    
    # Seleccionar herramienta "Crear imágenes"
    print("🎨 Activando herramienta 'Crear imágenes'...")
    tool_selected = False
    
    try:
        # Método 1: Buscar botón "Herramientas" por aria-label (varios idiomas)
        tools_btn = None
        selectors = [
            "button[aria-label='🍌 Crear imagen, botón, toca para usar la herramienta']",
            "button[aria-label='Tools']",
            "button[aria-label*='erramienta']",  # Parcial
            "button[aria-label*='ool']"  # Parcial
        ]
        
        for sel in selectors:
            try:
                tools_btn = driver.find_element(By.CSS_SELECTOR, sel)
                if tools_btn.is_displayed():
                    break
                tools_btn = None
            except:
                continue
        
        # Método 2: Buscar por texto del botón
        if not tools_btn:
            all_buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in all_buttons:
                try:
                    text = (btn.text or "").lower()
                    aria = (btn.get_attribute("aria-label") or "").lower()
                    if "herramienta" in text or "herramienta" in aria or "tools" in aria:
                        if btn.is_displayed():
                            tools_btn = btn
                            break
                except:
                    continue
        
        if tools_btn:
            driver.execute_script("arguments[0].click();", tools_btn)
            print("   ✅ Menú Herramientas abierto")
            time.sleep(1)
            
            # Buscar "Crear imágenes" en el menú desplegable
            menu_items = driver.find_elements(By.CSS_SELECTOR, "button, div[role='menuitem'], li")
            for item in menu_items:
                try:
                    text = (item.text or "").strip().lower()
                    if "crear imagen" in text:
                        driver.execute_script("arguments[0].click();", item)
                        print("   ✅ Herramienta 'Crear imágenes' activada!")
                        tool_selected = True
                        time.sleep(1)
                        break
                except:
                    continue
        else:
            print("   ⚠️ Botón Herramientas no encontrado")
            
    except Exception as e:
        print(f"   ⚠️ Error: {e}")
    
    # Fallback: Buscar botón de acceso rápido (pantalla inicial)
    if not tool_selected:
        try:
            quick_btns = driver.find_elements(By.XPATH, 
                "//*[contains(text(), 'Crear imagen') or contains(@aria-label, 'Crear imagen')]")
            for btn in quick_btns:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    print("   ✅ Acceso rápido 'Crear imagen' usado!")
                    tool_selected = True
                    break
        except:
            pass
    
    if not tool_selected:
        print("   ⚠️ No se pudo activar 'Crear imágenes'.")
        print("   👉 Selecciona manualmente: Herramientas > Crear imágenes")
    
    print("✅ Gemini listo para recibir imágenes.")
    return True
            
def bring_chrome_to_front(driver):
    """Trae la ventana de Chrome al frente usando Windows API."""
    try:
        import ctypes
        # Obtener el handle de la ventana actual de Selenium
        driver.switch_to.window(driver.current_window_handle)
        
        # Usar Alt+Tab trick para forzar foco
        pyautogui.keyDown('alt')
        time.sleep(0.1)
        pyautogui.press('tab')
        time.sleep(0.1)
        pyautogui.keyUp('alt')
        time.sleep(0.3)
        
        # Click en el centro de la ventana para asegurar foco
        pyautogui.click(x=960, y=400)
        time.sleep(0.2)
        
        print("   🔝 Ventana de Chrome al frente.")
        return True
    except Exception as e:
        print(f"   ⚠️ Error al traer ventana al frente: {e}")
        return False

def upload_image_and_translate(driver, image_path):
    """Sube una imagen y envía el prompt de traducción."""
    image_name = os.path.basename(image_path)
    print(f"\n📷 Procesando: {image_name}")
    
    # Copiar imagen a ruta segura (sin caracteres especiales)
    print("📋 Copiando imagen a ruta segura...")
    safe_image_path = copy_to_safe_path(image_path)
    print(f"   ✅ Imagen copiada a: {safe_image_path}")
    
    print("📤 Subiendo imagen...")
    
    uploaded = False
    
    try:
        time.sleep(2)
        
        # ESTRATEGIA 1: Buscar input file que ya existe (name='Filedata' u otro)
        print("   🔍 Buscando input file existente...")
        
        # Usar JavaScript para encontrar y habilitar el input file
        uploaded = driver.execute_script("""
            const inputs = document.querySelectorAll('input[type="file"]');
            if (inputs.length > 0) {
                const input = inputs[0];
                input.style.display = 'block';
                input.style.visibility = 'visible';
                input.style.opacity = '1';
                input.style.position = 'fixed';
                input.style.top = '0';
                input.style.left = '0';
                input.style.width = '100px';
                input.style.height = '100px';
                input.style.zIndex = '999999';
                return true;
            }
            return false;
        """)
        
        if uploaded:
            print("   ✅ Input file encontrado, enviando archivo...")
            time.sleep(0.5)
            file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            file_input.send_keys(safe_image_path)
            print("   ✅ Archivo enviado!")
            time.sleep(3)
        else:
            # ESTRATEGIA 2: Abrir el menú y usar pyautogui para el diálogo
            print("   🔍 No hay input file, abriendo menú de subida...")
            
            # Hacer clic en el botón de menú
            try:
                menu_btn = driver.find_element(By.CSS_SELECTOR, 
                    "button[aria-label*='menú de subida'], button[aria-label*='upload menu']")
                driver.execute_script("arguments[0].click();", menu_btn)
                time.sleep(1)
                
                # Hacer clic en "Subir archivos"
                upload_btn = driver.find_element(By.CSS_SELECTOR, 
                    "button[aria-label*='Subir archivos'], button[aria-label*='Upload files']")
                driver.execute_script("arguments[0].click();", upload_btn)
                time.sleep(1.5)
                
                # Buscar de nuevo el input file (podría aparecer ahora)
                file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                if file_inputs:
                    for fi in file_inputs:
                        try:
                            driver.execute_script("arguments[0].style.display = 'block';", fi)
                            fi.send_keys(safe_image_path)
                            print("   ✅ Archivo enviado via input!")
                            uploaded = True
                            time.sleep(3)
                            break
                        except:
                            continue
                
                # Si aun no funciona, probablemente abrió diálogo del sistema
                if not uploaded:
                    print("   ⌨️ Usando diálogo del sistema...")
                    time.sleep(1)
                    import pyperclip
                    pyperclip.copy(safe_image_path)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.5)
                    pyautogui.press('enter')
                    time.sleep(3)
                    uploaded = True
                    
            except Exception as e:
                print(f"   ⚠️ Error con menú: {e}")
                
    except Exception as e:
        print(f"   ⚠️ Error: {e}")
    
    if not uploaded:
        print("\n❌ No se pudo subir automáticamente.")
        print(f"📁 Imagen: {safe_image_path}")
        print("👉 Sube la imagen manualmente y presiona Enter...")
        input()
    
    time.sleep(2)

        
    search_prompt = "traduce el texto de la imagen, a español"
    
    print(f"✏️ Escribiendo prompt: '{search_prompt}'")
    time.sleep(2)  # Esperar a que la imagen se procese
    
    # Usar JavaScript para establecer el texto (evita problemas de encoding y Trusted Types)
    try:
        sent = driver.execute_script("""
            // Buscar el textbox
            const textbox = document.querySelector('div[role="textbox"]');
            if (textbox) {
                textbox.innerText = arguments[0];
                textbox.dispatchEvent(new Event('input', { bubbles: true }));
                
                // Esperar un momento y hacer clic en enviar
                setTimeout(() => {
                    const sendBtn = document.querySelector('button[aria-label="Enviar mensaje"], button[aria-label="Send message"]');
                    if (sendBtn) sendBtn.click();
                }, 500);
                return true;
            }
            return false;
        """, search_prompt)
        
        if sent:
            print("   ✅ Prompt enviado via JavaScript!")
        else:
            raise Exception("Textbox not found")
            
    except Exception as e:
        print(f"   ⚠️ Error con JS: {e}")
        # Fallback: usar pyautogui
        try:
            pyperclip.copy(search_prompt)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)
            pyautogui.press('enter')
            print("   ✅ Prompt enviado via pyautogui!")
        except:
            print("👉 Escribe el prompt manualmente y presiona Enter...")
            input()
    
    time.sleep(1)
    
    # Esperar la respuesta
    print("⏳ Esperando respuesta de Gemini...")
    # Esperar a que aparezca una nueva imagen o texto de respuesta
    # Método simple: esperar tiempo fijo + chequeo de carga
    time.sleep(30)  # Esperar más tiempo para generación de imagen
    
    return save_result_image(driver, image_name)

def save_result_image(driver, original_name):
    """Guarda la imagen resultante de la traducción."""
    print("💾 Buscando imagen para guardar...")
    
    try:
        # Esperar un poco más para que la imagen se renderice
        time.sleep(3)
        
        # Buscar imágenes en la respuesta de Gemini
        # Las imágenes generadas pueden tener varios formatos de src
        images = driver.find_elements(By.CSS_SELECTOR, "img, canvas")
        
        # Filtrar imágenes que podrían ser la respuesta generada
        result_images = []
        for img in images:
            try:
                src = img.get_attribute("src") or ""
                alt = img.get_attribute("alt") or ""
                class_name = img.get_attribute("class") or ""
                
                # Incluir imágenes blob, data, o de respuesta
                if ("blob:" in src or "data:image" in src or 
                    "generated" in src.lower() or "generated" in alt.lower() or
                    "response" in class_name.lower() or
                    img.tag_name == "canvas"):
                    result_images.append(img)
                # También buscar imágenes grandes que no sean iconos
                elif src and img.size.get('width', 0) > 200:
                    result_images.append(img)
            except:
                continue
        
        if result_images:
            # Intentar descargar la última imagen (probablemente la respuesta)
            img = result_images[-1]
            src = img.get_attribute("src")
            
            # Generar nombre para guardar
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = os.path.splitext(original_name)[0]
            save_name = f"traduccion_{base_name}_{timestamp}.png"
            save_path = os.path.join(DESKTOP_PATH, save_name)
            
            # Intentar hacer clic derecho y guardar, o usar JavaScript
            try:
                # Intentar descargar usando requests si es una URL accesible
                if src.startswith("http"):
                    response = requests.get(src)
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    print(f"✅ Imagen guardada: {save_name}")
                    return save_path
                elif src.startswith("data:"):
                    # Decodificar base64
                    import base64
                    data = src.split(",")[1]
                    with open(save_path, 'wb') as f:
                        f.write(base64.b64decode(data))
                    print(f"✅ Imagen guardada: {save_name}")
                    return save_path
                else:
                    # Intentar hacer screenshot del elemento
                    img.screenshot(save_path)
                    print(f"✅ Captura de imagen guardada: {save_name}")
                    return save_path
            except Exception as e:
                print(f"⚠️ No se pudo guardar automáticamente: {e}")
                print("📝 Por favor, guarda la imagen manualmente haciendo clic derecho > Guardar imagen")
                input("Presiona Enter cuando hayas guardado la imagen...")
                return None
        else:
            print("⚠️ No se encontró imagen de respuesta")
            print("📝 Si hay una imagen, guárdala manualmente")
            input("Presiona Enter para continuar...")
            return None
            
    except Exception as e:
        print(f"❌ Error guardando imagen: {e}")
        return None

def clear_conversation(driver):
    """Limpia la conversación para la siguiente imagen."""
    try:
        # Buscar botón de nueva conversación
        new_chat_selectors = [
            "//button[contains(@aria-label, 'Nueva')]",
            "//button[contains(@aria-label, 'New')]",
            "//*[contains(text(), 'Nueva conversación')]",
            "//*[contains(text(), 'New chat')]",
        ]
        
        for selector in new_chat_selectors:
            try:
                btn = driver.find_element(By.XPATH, selector)
                btn.click()
                time.sleep(2)
                return True
            except:
                continue
        
        # Si no encuentra, refrescar la página
        driver.refresh()
        time.sleep(3)
        return True
        
    except Exception as e:
        print(f"⚠️ Error limpiando conversación: {e}")
        driver.refresh()
        time.sleep(3)
        return True

def main():
    """Función principal del script."""
    print("=" * 60)
    print("🍌 GEMINI NANO BANANA - Traductor de Imágenes")
    print("=" * 60)
    
    # Obtener imágenes del escritorio
    images = get_desktop_images()
    
    if not images:
        print("❌ No se encontraron imágenes en la carpeta Imágenes.")
        print(f"📁 Ruta de Imágenes: {IMAGES_PATH}")
        print("Por favor, coloca las imágenes que deseas traducir en esa carpeta.")
        return
    
    print(f"\n📷 Se encontraron {len(images)} imagen(es):")
    for img in images:
        print(f"   - {os.path.basename(img)}")
    
    print("\n⚠️ IMPORTANTE: Se usará un PERFIL DEDICADO.")
    print("   1. Se abrirá una ventana de Chrome nueva.")
    print("   2. Si es la primera vez, INICIA SESIÓN en Google manualmente.")
    print("   3. Si no encuentra el agente, selecciónalo tú mismo.")
    input("\nPresiona Enter para iniciar...")
    
    # Configurar el driver
    print("\n🚀 Iniciando Chrome...")
    try:
        driver = setup_chrome_driver()
    except Exception as e:
        print(f"❌ Error iniciando Chrome: {e}")
        print("\n💡 Posibles soluciones:")
        print("   1. Asegúrate de que Chrome esté cerrado completamente")
        print("   2. Instala ChromeDriver: pip install webdriver-manager")
        print("   3. Verifica que Chrome esté instalado")
        return
    
    try:
        # Navegar a la Herramienta de Imagen
        if not navigate_to_image_tool(driver):
            print("❌ No se pudo configurar la herramienta")
            return
        
        # Procesar cada imagen
        results = []
        for i, image_path in enumerate(images, 1):
            print(f"\n{'=' * 40}")
            print(f"📷 Imagen {i}/{len(images)}")
            print(f"{'=' * 40}")
            
            result = upload_image_and_translate(driver, image_path)
            results.append({
                'original': image_path,
                'result': result
            })
            
            # Limpiar para la siguiente imagen
            if i < len(images):
                print("\n🔄 Preparando para la siguiente imagen...")
                clear_conversation(driver)
                time.sleep(2)
        
        # Resumen final
        print("\n" + "=" * 60)
        print("📊 RESUMEN")
        print("=" * 60)
        
        successful = sum(1 for r in results if r['result'])
        print(f"✅ Procesadas exitosamente: {successful}/{len(images)}")
        
        for r in results:
            status = "✅" if r['result'] else "❌"
            print(f"   {status} {os.path.basename(r['original'])}")
            if r['result']:
                print(f"      → {os.path.basename(r['result'])}")
        
        print("\n🎉 ¡Proceso completado!")
        input("\nPresiona Enter para cerrar el navegador...")
        
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()
        print("👋 Navegador cerrado.")

if __name__ == "__main__":
    main()


