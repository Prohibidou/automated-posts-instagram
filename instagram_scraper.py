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
import json
import hashlib
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
        self.posts_data = []  # Lista para guardar links y metadata
        
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
            
            # Esperar a que el grid de posts aparezca
            self.log("   ⏳ Esperando a que el contenido cargue...", 'info')
            time.sleep(5)
            
            # Verificar si es cuenta privada
            is_private = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Esta cuenta es privada') or contains(text(), 'This Account is Private')]")
            if is_private:
                self.log("❌ La cuenta es PRIVADA. No se pueden ver los posts.", 'error')
                return

            # Buscar el primer post
            self.log("\n🔍 Buscando posts...", 'info')
            
            # Intentar múltiples selectores para encontrar posts
            posts = []
            
            # Estrategia 1: Links con href /p/ o /reel/ (Instagram usa estos formatos)
            selectors_to_try = [
                "a[href*='/p/']",
                "a[href*='/reel/']",
                "div._aabd a",  # Selector común para thumbnails
                "div._ac7v a",  # Grid container links
                "main article a",
                "a img" # Buscar links que tengan una imagen dentro
            ]
            
            for selector in selectors_to_try:
                try:
                    all_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    # Filtrar solo los que parecen ser de posts
                    valid_posts = [e for e in all_elements if e.get_attribute('href') and ('/p/' in e.get_attribute('href') or '/reel/' in e.get_attribute('href'))]
                    if valid_posts:
                        posts = valid_posts
                        self.log(f"   ✅ Encontrados {len(posts)} posts con selector: {selector}", 'success')
                        break
                except:
                    continue
            
            # Estrategia 2: JavaScript para buscar todos los links de posts (como último recurso)
            if not posts:
                self.log("   🔍 Usando JavaScript profundo para buscar posts...", 'info')
                posts = self.driver.execute_script("""
                    return Array.from(document.querySelectorAll('a')).filter(a => 
                        a.href && (a.href.includes('/p/') || a.href.includes('/reel/'))
                    ).map(a => a); // El mapa es para asegurar que Selenium reciba los elementos
                """)
            
            # Debug intensivo si falla
            if not posts:
                self.log("⚠️ No se detectaron posts. Iniciando diagnóstico...", 'warning')
                
                # 1. ¿Cuántos links hay?
                total_links = self.driver.execute_script("return document.querySelectorAll('a').length;")
                self.log(f"   📊 Resumen: {total_links} links totales en la página", 'info')
                
                # 2. ¿Hay algún article?
                articles = self.driver.find_elements(By.TAG_NAME, "article")
                self.log(f"   📊 Resumen: {len(articles)} elementos <article> encontrados", 'info')
                
                # 3. Guardar HTML para análisis (opcional, pesado)
                # 4. Screenshot de la zona central
                debug_path = os.path.join(OUTPUT_DIR, "error_grid.png")
                self.driver.save_screenshot(debug_path)
                self.log(f"   📸 Pantallazo de error guardado: {debug_path}", 'warning')
                self.log("   👉 Revisa si en el navegador ves el grid de fotos o una página en blanco/login", 'info')
            
            if not posts:
                self.log("\n❌ NO SE ENCONTRARON POSTS", 'error')
                self.log("   Posibles razones:", 'info')
                self.log("   1. Instagram te está pidiendo un CAPTCHA", 'info')
                self.log("   2. La sesión se cerró y ves la pantalla de login", 'info')
                self.log("   3. Instagram bloqueó las peticiones automáticas temporalmente", 'info')
                return
            
            self.log(f"   🚀 Iniciando desde el primer post encontrado...", 'success')
            
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
                
                # Crear datos del post
                post_data = {
                    "id": post_id,
                    "url": current_url,
                    "type": post_type,
                    "scraped_at": datetime.now().isoformat(),
                    "images": []
                }
                
                if post_type == "reel":
                    self.log("   📹 Tipo: REEL (saltando)", 'warning')
                    self.count_reels += 1
                    post_data["skipped"] = True
                    
                elif post_type == "carousel":
                    self.log("   📚 Tipo: CARRUSEL", 'success')
                    self.count_carruseles += 1
                    images = self._save_carousel(post_id)
                    post_data["images"] = images
                    
                else:  # single image
                    self.log("   🖼️ Tipo: IMAGEN ÚNICA", 'success')
                    self.count_imagenes += 1
                    images = self._save_single_image(post_id)
                    post_data["images"] = images
                
                # Guardar datos del post
                self.posts_data.append(post_data)
                self._save_posts_json()
                
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
        """Guarda todas las imágenes del carrusel evitando duplicados."""
        folder = os.path.join(CARRUSELES_DIR, post_id)
        os.makedirs(folder, exist_ok=True)
        
        saved_images = []  # Lista de URLs guardadas
        seen_hashes = set()  # Hashes de imágenes ya vistas para evitar duplicados
        img_count = 0
        max_images = 15  # Límite de seguridad
        consecutive_duplicates = 0
        
        while img_count < max_images:
            # Obtener la URL de la imagen actual
            img_url = self._get_current_image_url()
            
            if img_url:
                # Crear hash de la URL para detectar duplicados
                url_hash = hashlib.md5(img_url.encode()).hexdigest()[:16]
                
                if url_hash not in seen_hashes:
                    seen_hashes.add(url_hash)
                    consecutive_duplicates = 0
                    img_count += 1
                    
                    # Tomar screenshot del contenedor de imagen
                    filepath = self._take_post_screenshot(folder, img_count)
                    saved_images.append({
                        "index": img_count,
                        "url": img_url,
                        "file": filepath
                    })
                    self.log(f"      💾 Imagen {img_count} guardada", 'success')
                else:
                    consecutive_duplicates += 1
                    self.log(f"      ⏭️ Imagen duplicada detectada ({consecutive_duplicates})", 'warning')
                    if consecutive_duplicates >= 2:
                        # Si vimos 2 duplicados seguidos, probablemente ya terminamos
                        break
            else:
                # Si no encontramos imagen, intentamos continuar
                img_count += 1
                filepath = self._take_post_screenshot(folder, img_count)
                self.log(f"      💾 Imagen {img_count} guardada (sin URL)", 'warning')
            
            # Intentar ir a la siguiente imagen del carrusel
            # IMPORTANTE: Buscar el botón DENTRO del article (carrusel), no el de navegación entre posts
            if not self._click_carousel_next():
                break  # No hay más imágenes
            
            time.sleep(1.2)  # Esperar a que cargue la siguiente imagen
        
        self.log(f"   📁 Guardado en: {folder}", 'info')
        return saved_images
    
    def _click_carousel_next(self):
        """Hace clic en el botón 'Siguiente' del carrusel (no el de posts)."""
        try:
            # Buscar específicamente dentro del article (contenedor del post modal)
            # El botón del carrusel está DENTRO del contenedor de la imagen
            carousel_selectors = [
                # Selector específico para el botón de siguiente en carrusel (dentro de la lista de imágenes)
                "article div._aahi button[aria-label*='Siguiente']",
                "article div._aahi button[aria-label*='Next']",
                # Botón dentro del contenedor de imágenes del carrusel
                "article ul button[aria-label*='Siguiente']",
                "article ul button[aria-label*='Next']",
                # Selector más genérico pero dentro del article
                "article div[role='presentation'] button[aria-label*='Siguiente']",
                "article div[role='presentation'] button[aria-label*='Next']",
                # Botón que está al lado derecho de la imagen (posición relativa)
                "article div._aagw button[aria-label*='Siguiente']",
                "article div._aagw button[aria-label*='Next']",
            ]
            
            for selector in carousel_selectors:
                try:
                    btns = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for btn in btns:
                        if btn.is_displayed() and btn.is_enabled():
                            # Verificar que no sea el botón de navegación entre posts
                            # El botón del carrusel suele estar más cerca de la imagen
                            self.driver.execute_script("arguments[0].click();", btn)
                            return True
                except:
                    continue
            
            # Método alternativo: buscar por la estructura del DOM
            # El botón del carrusel tiene un SVG con el chevron hacia la derecha
            try:
                next_btn = self.driver.execute_script("""
                    // Buscar dentro del article el botón de siguiente del carrusel
                    var article = document.querySelector('article');
                    if (!article) return null;
                    
                    // Buscar todos los botones con Siguiente/Next
                    var buttons = article.querySelectorAll('button[aria-label*="Siguiente"], button[aria-label*="Next"]');
                    
                    for (var btn of buttons) {
                        // El botón del carrusel está dentro del contenedor de la imagen
                        // y tiene un ancestro con la clase _aahi o similar
                        var parent = btn.closest('div._aahi, div._aagw, ul');
                        if (parent && btn.offsetParent !== null) {
                            return btn;
                        }
                    }
                    
                    // Si no encontramos con la estructura específica, buscar el que esté visible
                    for (var btn of buttons) {
                        if (btn.offsetParent !== null) {
                            return btn;
                        }
                    }
                    
                    return null;
                """)
                
                if next_btn:
                    self.driver.execute_script("arguments[0].click();", next_btn)
                    return True
            except:
                pass
            
            return False
            
        except Exception as e:
            self.log(f"      ⚠️ Error al navegar: {e}", 'warning')
            return False
    
    def _save_single_image(self, post_id):
        """Guarda la imagen única."""
        folder = os.path.join(IMAGENES_DIR, post_id)
        os.makedirs(folder, exist_ok=True)
        
        img_url = self._get_current_image_url()
        filepath = self._take_post_screenshot(folder, 1)
        self.log(f"   💾 Imagen guardada en: {folder}", 'success')
        
        return [{
            "index": 1,
            "url": img_url,
            "file": filepath
        }]
    
    def _get_current_image_url(self):
        """Obtiene la URL de la imagen actualmente visible en el post."""
        try:
            # Intentar múltiples selectores para encontrar la imagen
            selectors = [
                "article div._aagv img",
                "article div._aatk img", 
                "article img[style*='object-fit']",
                "article div[role='button'] img",
                "article ul li[style*='translateX'] img",  # Imagen activa en carrusel
            ]
            
            for selector in selectors:
                try:
                    imgs = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for img in imgs:
                        src = img.get_attribute('src')
                        if src and 'instagram' in src and not 'data:' in src:
                            return src
                except:
                    continue
            
            # Fallback: buscar cualquier imagen grande en el artículo
            imgs = self.driver.find_elements(By.CSS_SELECTOR, "article img")
            for img in imgs:
                src = img.get_attribute('src')
                if src and 'instagram' in src and 'scontent' in src:
                    return src
                    
        except Exception as e:
            pass
        
        return None
    
    def _take_post_screenshot(self, folder, index):
        """Toma screenshot del área del post."""
        filepath = os.path.join(folder, f"{index}.png")
        try:
            # Buscar el contenedor de la imagen/contenido
            media = self.driver.find_element(By.CSS_SELECTOR, 
                "article div._aagv img, article div._aatk img, article img[style*='object-fit']")
            
            # Scroll para asegurar visibilidad
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", media)
            time.sleep(0.3)
            
            # Screenshot del elemento
            media.screenshot(filepath)
            
        except:
            # Fallback: screenshot de toda la ventana
            self.driver.save_screenshot(filepath)
        
        return filepath
    
    def _save_posts_json(self):
        """Guarda todos los links y datos de los posts en un archivo JSON."""
        json_path = os.path.join(OUTPUT_DIR, "posts_data.json")
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "scraped_at": datetime.now().isoformat(),
                    "total_posts": len(self.posts_data),
                    "posts": self.posts_data
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"   ⚠️ Error guardando JSON: {e}", 'warning')
    
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
