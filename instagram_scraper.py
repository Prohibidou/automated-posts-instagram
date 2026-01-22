"""
📸 INSTAGRAM POST SCRAPER
==========================
Recorre los posts de un perfil de Instagram, identifica el tipo
(Reel, Carrusel, Imagen única) y guarda capturas de pantalla.
"""

import os
import sys
import re
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# Configuración - Usar el mismo perfil que gemini_translator (ya tiene sesión)
PROFILE_PATH = os.path.join(os.environ['USERPROFILE'], '.gemini_translator_profile')
OUTPUT_DIR = os.path.join(os.environ['USERPROFILE'], 'Desktop', 'instagram_posts')
CARRUSELES_DIR = os.path.join(OUTPUT_DIR, 'carruseles')
IMAGENES_DIR = os.path.join(OUTPUT_DIR, 'imagenes')


class InstagramScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("📸 Instagram Post Scraper")
        self.root.geometry("750x600")
        self.root.configure(bg='#1a1a2e')
        
        self.driver = None
        self.running = False
        self.stop_requested = False
        
        self.setup_ui()
        self.create_directories()
    
    def create_directories(self):
        """Crea las carpetas de salida."""
        os.makedirs(CARRUSELES_DIR, exist_ok=True)
        os.makedirs(IMAGENES_DIR, exist_ok=True)
    
    def setup_ui(self):
        """Configura la interfaz gráfica."""
        main_frame = tk.Frame(self.root, bg='#1a1a2e', padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        tk.Label(main_frame, text="📸 Instagram Post Scraper", 
                font=('Segoe UI', 18, 'bold'), bg='#1a1a2e', fg='#E1306C').pack(pady=(0, 15))
        
        # URL Input
        url_frame = tk.Frame(main_frame, bg='#1a1a2e')
        url_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(url_frame, text="URL del perfil:", font=('Segoe UI', 11),
                bg='#1a1a2e', fg='white').pack(side=tk.LEFT)
        
        self.url_entry = tk.Entry(url_frame, font=('Segoe UI', 11), width=50,
                                  bg='#16213e', fg='white', insertbackground='white')
        self.url_entry.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        self.url_entry.insert(0, "https://www.instagram.com/")
        
        # Status
        status_frame = tk.Frame(main_frame, bg='#16213e', padx=15, pady=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_var = tk.StringVar(value="⏸️ Esperando...")
        self.status_label = tk.Label(status_frame, textvariable=self.status_var,
                                     font=('Segoe UI', 12, 'bold'), bg='#16213e', fg='#00ff88')
        self.status_label.pack()
        
        # Contadores
        counter_frame = tk.Frame(main_frame, bg='#1a1a2e')
        counter_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.posts_var = tk.StringVar(value="Posts: 0")
        tk.Label(counter_frame, textvariable=self.posts_var, font=('Segoe UI', 10),
                bg='#1a1a2e', fg='#888').pack(side=tk.LEFT, padx=(0, 20))
        
        self.carruseles_var = tk.StringVar(value="Carruseles: 0")
        tk.Label(counter_frame, textvariable=self.carruseles_var, font=('Segoe UI', 10),
                bg='#1a1a2e', fg='#888').pack(side=tk.LEFT, padx=(0, 20))
        
        self.imagenes_var = tk.StringVar(value="Imágenes: 0")
        tk.Label(counter_frame, textvariable=self.imagenes_var, font=('Segoe UI', 10),
                bg='#1a1a2e', fg='#888').pack(side=tk.LEFT, padx=(0, 20))
        
        self.reels_var = tk.StringVar(value="Reels (saltados): 0")
        tk.Label(counter_frame, textvariable=self.reels_var, font=('Segoe UI', 10),
                bg='#1a1a2e', fg='#888').pack(side=tk.LEFT)
        
        # Botones
        btn_frame = tk.Frame(main_frame, bg='#1a1a2e')
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_btn = tk.Button(btn_frame, text="▶️ Iniciar", 
                                   font=('Segoe UI', 12, 'bold'),
                                   bg='#00d9ff', fg='#1a1a2e', padx=20, pady=8,
                                   command=self.start_scraping, cursor='hand2')
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = tk.Button(btn_frame, text="🛑 BASTA", 
                                  font=('Segoe UI', 14, 'bold'),
                                  bg='#ff4757', fg='white', padx=30, pady=8,
                                  command=self.stop_scraping, state=tk.DISABLED, cursor='hand2')
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.open_folder_btn = tk.Button(btn_frame, text="📁 Abrir Carpeta", 
                                         font=('Segoe UI', 11),
                                         bg='#ffa502', fg='#1a1a2e', padx=15, pady=8,
                                         command=self.open_output_folder, cursor='hand2')
        self.open_folder_btn.pack(side=tk.RIGHT)
        
        # Log
        tk.Label(main_frame, text="📋 LOG:", font=('Segoe UI', 10, 'bold'),
                bg='#1a1a2e', fg='#888').pack(anchor='w')
        
        self.log_text = scrolledtext.ScrolledText(main_frame, height=18, font=('Consolas', 9),
                                                   bg='#0f0f23', fg='#00ff88', wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        self.log_text.tag_config('success', foreground='#00ff88')
        self.log_text.tag_config('error', foreground='#ff4757')
        self.log_text.tag_config('warning', foreground='#ffa502')
        self.log_text.tag_config('info', foreground='#00d9ff')
        self.log_text.tag_config('header', foreground='#E1306C', font=('Consolas', 9, 'bold'))
        
        # Cerrar
        tk.Button(main_frame, text="❌ Cerrar", font=('Segoe UI', 11),
                 bg='#ff4757', fg='white', padx=15, pady=6,
                 command=self.close_app, cursor='hand2').pack(side=tk.RIGHT)
        
        # Contadores internos
        self.count_posts = 0
        self.count_carruseles = 0
        self.count_imagenes = 0
        self.count_reels = 0
    
    def log(self, msg, tag='info'):
        self.log_text.insert(tk.END, msg + "\n", tag)
        self.log_text.see(tk.END)
        self.root.update()
    
    def set_status(self, status, color='#00ff88'):
        self.status_var.set(status)
        self.status_label.config(fg=color)
        self.root.update()
    
    def update_counters(self):
        self.posts_var.set(f"Posts: {self.count_posts}")
        self.carruseles_var.set(f"Carruseles: {self.count_carruseles}")
        self.imagenes_var.set(f"Imágenes: {self.count_imagenes}")
        self.reels_var.set(f"Reels (saltados): {self.count_reels}")
        self.root.update()
    
    def open_output_folder(self):
        os.startfile(OUTPUT_DIR)
    
    def start_scraping(self):
        if self.running:
            return
        
        url = self.url_entry.get().strip()
        if not url or 'instagram.com' not in url:
            messagebox.showerror("Error", "Ingresa una URL válida de Instagram")
            return
        
        self.running = True
        self.stop_requested = False
        self.count_posts = 0
        self.count_carruseles = 0
        self.count_imagenes = 0
        self.count_reels = 0
        self.update_counters()
        
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        
        thread = threading.Thread(target=self._scrape, args=(url,))
        thread.daemon = True
        thread.start()
    
    def stop_scraping(self):
        self.stop_requested = True
        self.log("\n🛑 Deteniendo... espera a que termine el post actual", 'warning')
        self.set_status("🛑 Deteniendo...", '#ff4757')
    
    def _scrape(self, profile_url):
        try:
            self.log("=" * 50, 'header')
            self.log("📸 INSTAGRAM POST SCRAPER", 'header')
            self.log("=" * 50, 'header')
            self.log("")
            
            # Iniciar Chrome
            self.set_status("🚀 Iniciando Chrome...", '#00d9ff')
            self.log("🚀 Iniciando Chrome...", 'info')
            
            options = Options()
            options.add_argument(f"--user-data-dir={PROFILE_PATH}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.maximize_window()
            self.log("   ✅ Chrome iniciado", 'success')
            
            # Navegar al perfil
            self.set_status("🌐 Navegando al perfil...", '#00d9ff')
            self.log(f"\n🌐 Navegando a: {profile_url}", 'info')
            self.driver.get(profile_url)
            time.sleep(5)
            
            # Cerrar popups de cookies o login
            self.log("   🔄 Cerrando popups...", 'info')
            try:
                # Cerrar banner de cookies
                cookie_btns = self.driver.find_elements(By.XPATH, 
                    "//button[contains(text(), 'Permitir') or contains(text(), 'Allow') or contains(text(), 'Accept') or contains(text(), 'Aceptar')]")
                for btn in cookie_btns:
                    if btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.5)
                
                # Cerrar popup de login si aparece
                close_btns = self.driver.find_elements(By.CSS_SELECTOR, 
                    "button[aria-label='Cerrar'], button[aria-label='Close'], svg[aria-label='Cerrar']")
                for btn in close_btns:
                    try:
                        if btn.is_displayed():
                            self.driver.execute_script("arguments[0].click();", btn)
                            time.sleep(0.5)
                    except:
                        pass
            except:
                pass
            
            # Verificar si necesita login
            if "login" in self.driver.current_url.lower() or "accounts" in self.driver.current_url.lower():
                self.log("⚠️ Necesitas iniciar sesión en Instagram", 'warning')
                self.log("👉 Inicia sesión manualmente en el navegador", 'warning')
                self.log("👉 Luego vuelve al perfil y presiona Iniciar de nuevo", 'warning')
                return
            
            # Scroll para cargar contenido
            self.log("   🔄 Scrolleando para cargar posts...", 'info')
            self.driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Buscar el primer post
            self.log("\n🔍 Buscando posts...", 'info')
            
            # Intentar múltiples selectores para encontrar posts
            posts = []
            
            # Estrategia 1: Links con href /p/ o /reel/
            selectors_to_try = [
                "a[href*='/p/']",
                "a[href*='/reel/']",
                "div._ac7v a",  # Grid container links
                "div._aabd a",  # Alternative grid
                "main a[href*='/p/']",
                "section main a[href*='/p/']"
            ]
            
            for selector in selectors_to_try:
                try:
                    posts = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if posts:
                        self.log(f"   ℹ️ Usando selector: {selector}", 'info')
                        break
                except:
                    continue
            
            # Estrategia 2: JavaScript para buscar todos los links de posts
            if not posts:
                self.log("   🔍 Usando JavaScript para buscar posts...", 'info')
                posts = self.driver.execute_script("""
                    return Array.from(document.querySelectorAll('a')).filter(a => 
                        a.href && (a.href.includes('/p/') || a.href.includes('/reel/'))
                    );
                """)
            
            # Debug: mostrar cuántos links hay en total
            if not posts:
                total_links = self.driver.execute_script("return document.querySelectorAll('a').length;")
                self.log(f"   🔍 Debug: {total_links} links totales en la página", 'warning')
                
                # Mostrar algunos hrefs para debug
                sample_hrefs = self.driver.execute_script("""
                    return Array.from(document.querySelectorAll('a')).slice(0, 10).map(a => a.href);
                """)
                for href in sample_hrefs[:5]:
                    self.log(f"      - {href[:60]}...", 'info')
                
                # Guardar screenshot para debug
                debug_path = os.path.join(OUTPUT_DIR, "debug_screenshot.png")
                self.driver.save_screenshot(debug_path)
                self.log(f"   📸 Screenshot guardado: {debug_path}", 'warning')
            
            if not posts:
                self.log("❌ No se encontraron posts", 'error')
                self.log("   Verifica que la cuenta tenga posts públicos", 'warning')
                self.log("   Revisa el screenshot en Desktop/instagram_posts/", 'warning')
                return
            
            self.log(f"   ✅ Encontrados {len(posts)} posts", 'success')
            
            # Hacer clic en el primer post
            self.log("\n📷 Abriendo primer post...", 'info')
            try:
                self.driver.execute_script("arguments[0].click();", posts[0])
            except:
                posts[0].click()
            time.sleep(2)
            
            # Procesar posts
            while not self.stop_requested:
                self.count_posts += 1
                self.update_counters()
                
                # Obtener URL actual del post
                current_url = self.driver.current_url
                post_id = self._extract_post_id(current_url)
                
                self.set_status(f"📷 Procesando: {post_id}", '#ffa502')
                self.log(f"\n{'='*40}", 'header')
                self.log(f"📷 Post #{self.count_posts}: {post_id}", 'header')
                
                # Detectar tipo de post
                post_type = self._detect_post_type()
                
                if post_type == "reel":
                    self.log("   📹 Tipo: REEL (saltando)", 'warning')
                    self.count_reels += 1
                    
                elif post_type == "carousel":
                    self.log("   📚 Tipo: CARRUSEL", 'success')
                    self.count_carruseles += 1
                    self._save_carousel(post_id)
                    
                else:  # single image
                    self.log("   🖼️ Tipo: IMAGEN ÚNICA", 'success')
                    self.count_imagenes += 1
                    self._save_single_image(post_id)
                
                self.update_counters()
                
                # Ir al siguiente post
                if not self._go_to_next_post():
                    self.log("\n✅ No hay más posts o se llegó al final", 'success')
                    break
                
                time.sleep(1.5)
            
            # Resumen
            self.log("\n" + "=" * 50, 'header')
            self.log("📊 RESUMEN", 'header')
            self.log("=" * 50, 'header')
            self.log(f"   Posts procesados: {self.count_posts}", 'info')
            self.log(f"   Carruseles guardados: {self.count_carruseles}", 'success')
            self.log(f"   Imágenes guardadas: {self.count_imagenes}", 'success')
            self.log(f"   Reels saltados: {self.count_reels}", 'warning')
            self.log(f"\n📁 Guardado en: {OUTPUT_DIR}", 'info')
            
            self.set_status("✅ Completado", '#00ff88')
            
        except Exception as e:
            self.log(f"\n❌ Error: {e}", 'error')
            self.set_status("❌ Error", '#ff4757')
        finally:
            self.running = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
    
    def _extract_post_id(self, url):
        """Extrae el ID del post de la URL."""
        match = re.search(r'/(?:p|reel)/([A-Za-z0-9_-]+)', url)
        return match.group(1) if match else f"post_{int(time.time())}"
    
    def _detect_post_type(self):
        """Detecta si es Reel, Carrusel o Imagen única."""
        try:
            # Verificar si es Reel por URL
            if "/reel/" in self.driver.current_url:
                return "reel"
            
            # Verificar si es Reel por elemento de video
            videos = self.driver.find_elements(By.CSS_SELECTOR, "article video")
            if videos:
                return "reel"
            
            # Verificar si es Carrusel (tiene botón de siguiente)
            next_btns = self.driver.find_elements(By.CSS_SELECTOR, 
                "button[aria-label*='Siguiente'], button[aria-label*='Next'], div._aamj button")
            
            # También verificar indicadores de puntos
            dots = self.driver.find_elements(By.CSS_SELECTOR, "div._acnb, div._aalg")
            
            if next_btns or len(dots) > 1:
                return "carousel"
            
            return "single"
            
        except:
            return "single"
    
    def _save_carousel(self, post_id):
        """Guarda todas las imágenes del carrusel."""
        folder = os.path.join(CARRUSELES_DIR, post_id)
        os.makedirs(folder, exist_ok=True)
        
        img_count = 0
        max_images = 10  # Límite de seguridad
        
        while img_count < max_images:
            img_count += 1
            
            # Tomar screenshot del contenedor de imagen
            self._take_post_screenshot(folder, img_count)
            self.log(f"      💾 Imagen {img_count} guardada", 'success')
            
            # Intentar ir a la siguiente imagen del carrusel
            try:
                next_btn = self.driver.find_element(By.CSS_SELECTOR, 
                    "button[aria-label*='Siguiente'], button[aria-label*='Next']")
                self.driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(0.8)
            except NoSuchElementException:
                break  # No hay más imágenes
        
        self.log(f"   📁 Guardado en: {folder}", 'info')
    
    def _save_single_image(self, post_id):
        """Guarda la imagen única."""
        folder = os.path.join(IMAGENES_DIR, post_id)
        os.makedirs(folder, exist_ok=True)
        
        self._take_post_screenshot(folder, 1)
        self.log(f"   💾 Imagen guardada en: {folder}", 'success')
    
    def _take_post_screenshot(self, folder, index):
        """Toma screenshot del área del post."""
        try:
            # Buscar el contenedor de la imagen/contenido
            media = self.driver.find_element(By.CSS_SELECTOR, 
                "article div._aagv img, article div._aatk img, article img[style*='object-fit']")
            
            # Scroll para asegurar visibilidad
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", media)
            time.sleep(0.3)
            
            # Screenshot del elemento
            filepath = os.path.join(folder, f"{index}.png")
            media.screenshot(filepath)
            
        except:
            # Fallback: screenshot de toda la ventana
            filepath = os.path.join(folder, f"{index}.png")
            self.driver.save_screenshot(filepath)
    
    def _go_to_next_post(self):
        """Navega al siguiente post."""
        try:
            # Buscar botón de siguiente post (flecha derecha)
            next_post_btn = self.driver.find_element(By.CSS_SELECTOR, 
                "button[aria-label*='Siguiente'], a[aria-label*='Siguiente'], button svg[aria-label*='Siguiente']")
            
            # Subir un nivel si encontramos el SVG
            parent = next_post_btn
            for _ in range(3):
                if parent.tag_name == "button":
                    break
                parent = parent.find_element(By.XPATH, "..")
            
            self.driver.execute_script("arguments[0].click();", parent)
            time.sleep(1)
            return True
            
        except NoSuchElementException:
            # Intentar con tecla de flecha derecha
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ARROW_RIGHT)
                time.sleep(1)
                
                # Verificar si cambió la URL
                new_url = self.driver.current_url
                return "/p/" in new_url or "/reel/" in new_url
            except:
                return False
    
    def close_app(self):
        self.stop_requested = True
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = InstagramScraperGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.close_app)
    root.mainloop()


if __name__ == "__main__":
    main()
