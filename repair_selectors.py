"""
🔧 GEMINI SELECTOR REPAIR TOOL - GUI VERSION
=============================================
Interfaz gráfica para inspeccionar y reparar los selectores de Gemini.
"""

import os
import re
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# Configuración
MAIN_SCRIPT = os.path.join(os.path.dirname(__file__), "gemini_translator.py")
PROFILE_PATH = os.path.join(os.environ['USERPROFILE'], '.gemini_translator_profile')


class RepairToolGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🔧 Gemini Tool - Reparar y Traducir")
        self.root.geometry("750x750")
        self.root.configure(bg='#1a1a2e')
        
        self.driver = None
        self.selectors = {}
        self.running = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configura la interfaz gráfica."""
        # Estilo
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', font=('Segoe UI', 11), padding=10)
        style.configure('TLabel', font=('Segoe UI', 11), background='#1a1a2e', foreground='white')
        style.configure('Header.TLabel', font=('Segoe UI', 16, 'bold'), background='#1a1a2e', foreground='#00d9ff')
        style.configure('Status.TLabel', font=('Segoe UI', 12), background='#16213e', foreground='#00ff88', padding=10)
        
        # Frame principal
        main_frame = tk.Frame(self.root, bg='#1a1a2e', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        title = ttk.Label(main_frame, text="🔧 Gemini Selector Repair Tool", style='Header.TLabel')
        title.pack(pady=(0, 10))
        
        subtitle = ttk.Label(main_frame, text="Inspecciona y repara automáticamente los selectores de Gemini", style='TLabel')
        subtitle.pack(pady=(0, 20))
        
        # Estado actual
        status_frame = tk.Frame(main_frame, bg='#16213e', padx=15, pady=15)
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        status_label = tk.Label(status_frame, text="ESTADO:", font=('Segoe UI', 10, 'bold'), 
                               bg='#16213e', fg='#888')
        status_label.pack(anchor='w')
        
        self.status_var = tk.StringVar(value="⏸️ Esperando inicio...")
        self.status_display = tk.Label(status_frame, textvariable=self.status_var, 
                                       font=('Segoe UI', 14, 'bold'), bg='#16213e', fg='#00ff88',
                                       wraplength=600, justify='left')
        self.status_display.pack(anchor='w', pady=(5, 0))
        
        # Barra de progreso
        self.progress = ttk.Progressbar(main_frame, mode='determinate', length=660)
        self.progress.pack(fill=tk.X, pady=(0, 15))
        
        # Log de actividad
        log_label = tk.Label(main_frame, text="📋 LOG DE ACTIVIDAD:", font=('Segoe UI', 10, 'bold'),
                            bg='#1a1a2e', fg='#888')
        log_label.pack(anchor='w')
        
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, font=('Consolas', 10),
                                                   bg='#0f0f23', fg='#00ff88', insertbackground='white',
                                                   wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(5, 15))
        
        # Configurar tags para colores
        self.log_text.tag_config('success', foreground='#00ff88')
        self.log_text.tag_config('error', foreground='#ff4757')
        self.log_text.tag_config('warning', foreground='#ffa502')
        self.log_text.tag_config('info', foreground='#00d9ff')
        self.log_text.tag_config('header', foreground='#ffffff', font=('Consolas', 10, 'bold'))
        
        # Frame de botones - Fila 1 (Reparación)
        btn_frame1 = tk.Frame(main_frame, bg='#1a1a2e')
        btn_frame1.pack(fill=tk.X, pady=(0, 10))
        
        repair_label = tk.Label(btn_frame1, text="🔧 REPARACIÓN:", font=('Segoe UI', 9, 'bold'),
                               bg='#1a1a2e', fg='#888')
        repair_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.start_btn = tk.Button(btn_frame1, text="� Inspeccionar", font=('Segoe UI', 11, 'bold'),
                                   bg='#00d9ff', fg='#1a1a2e', padx=15, pady=8,
                                   command=self.start_inspection, cursor='hand2')
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.repair_btn = tk.Button(btn_frame1, text="🔧 Aplicar", font=('Segoe UI', 11, 'bold'),
                                    bg='#00ff88', fg='#1a1a2e', padx=15, pady=8,
                                    command=self.apply_repair, state=tk.DISABLED, cursor='hand2')
        self.repair_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Frame de botones - Fila 2 (Automatización)
        btn_frame2 = tk.Frame(main_frame, bg='#1a1a2e')
        btn_frame2.pack(fill=tk.X, pady=(0, 10))
        
        auto_label = tk.Label(btn_frame2, text="🍌 TRADUCCIÓN:", font=('Segoe UI', 9, 'bold'),
                             bg='#1a1a2e', fg='#888')
        auto_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.run_btn = tk.Button(btn_frame2, text="▶️ Ejecutar Traductor", font=('Segoe UI', 11, 'bold'),
                                 bg='#ffa502', fg='#1a1a2e', padx=15, pady=8,
                                 command=self.run_translator, cursor='hand2')
        self.run_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = tk.Button(btn_frame2, text="⏹️ Detener", font=('Segoe UI', 11),
                                  bg='#ff6b6b', fg='white', padx=15, pady=8,
                                  command=self.stop_translator, state=tk.DISABLED, cursor='hand2')
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Botón cerrar
        btn_frame3 = tk.Frame(main_frame, bg='#1a1a2e')
        btn_frame3.pack(fill=tk.X)
        
        self.close_btn = tk.Button(btn_frame3, text="❌ Cerrar Aplicación", font=('Segoe UI', 11),
                                   bg='#ff4757', fg='white', padx=15, pady=8,
                                   command=self.close_app, cursor='hand2')
        self.close_btn.pack(side=tk.RIGHT)
        
        # Variable para el proceso del traductor
        self.translator_process = None
    
    def log(self, message, tag='info'):
        """Añade un mensaje al log."""
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.root.update()
    
    def set_status(self, status, color='#00ff88'):
        """Actualiza el estado mostrado."""
        self.status_var.set(status)
        self.status_display.config(fg=color)
        self.root.update()
    
    def set_progress(self, value):
        """Actualiza la barra de progreso."""
        self.progress['value'] = value
        self.root.update()
    
    def start_inspection(self):
        """Inicia la inspección en un hilo separado."""
        if self.running:
            return
        
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.repair_btn.config(state=tk.DISABLED)
        self.log_text.delete(1.0, tk.END)
        
        thread = threading.Thread(target=self.run_inspection)
        thread.daemon = True
        thread.start()
    
    def run_inspection(self):
        """Ejecuta la inspección de Gemini."""
        try:
            # Paso 1: Iniciar Chrome
            self.set_status("🚀 Iniciando Chrome...")
            self.set_progress(10)
            self.log("=" * 50, 'header')
            self.log("🔧 INICIANDO INSPECCIÓN DE GEMINI", 'header')
            self.log("=" * 50, 'header')
            self.log("")
            self.log("🚀 Iniciando navegador Chrome...", 'info')
            
            options = Options()
            options.add_argument(f"--user-data-dir={PROFILE_PATH}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.log("   ✅ Chrome iniciado correctamente", 'success')
            
            # Paso 2: Navegar a Gemini
            self.set_status("🌐 Navegando a Gemini...")
            self.set_progress(20)
            self.log("\n🌐 Navegando a gemini.google.com/app...", 'info')
            self.driver.get("https://gemini.google.com/app")
            time.sleep(5)
            self.log("   ✅ Página cargada", 'success')
            
            # Cerrar popups
            try:
                close_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Entendido') or contains(text(), 'Got it')]")
                for btn in close_btns:
                    if btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", btn)
                        self.log("   ℹ️ Popup cerrado", 'info')
                        time.sleep(0.5)
            except:
                pass
            
            # Paso 3: Buscar selectores
            self.set_status("🔍 Inspeccionando interfaz...")
            self.set_progress(30)
            self.log("\n" + "=" * 50, 'header')
            self.log("🔍 INSPECCIONANDO SELECTORES", 'header')
            self.log("=" * 50, 'header')
            
            self.selectors = {}
            
            # Buscar botón Herramientas
            self.set_status("🔍 Buscando botón 'Herramientas'...")
            self.set_progress(40)
            self.log("\n📌 Buscando botón 'Herramientas'...", 'info')
            
            tools_candidates = self.driver.execute_script("""
                const buttons = Array.from(document.querySelectorAll('button'));
                return buttons.map(b => ({
                    text: b.innerText?.trim() || '',
                    ariaLabel: b.getAttribute('aria-label') || '',
                    visible: b.offsetWidth > 0 && b.offsetHeight > 0
                })).filter(b => 
                    b.visible && (
                        b.text.toLowerCase().includes('herramienta') ||
                        b.ariaLabel.toLowerCase().includes('herramienta') ||
                        b.ariaLabel.toLowerCase().includes('tool')
                    )
                );
            """)
            
            if tools_candidates:
                best = tools_candidates[0]
                self.selectors['tools_button'] = best
                self.log(f"   ✅ Encontrado: aria-label='{best['ariaLabel']}'", 'success')
                self.log(f"      Texto: '{best['text']}'", 'info')
                
                # Hacer clic para ver menú
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, f"button[aria-label='{best['ariaLabel']}']")
                    self.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(1)
                except:
                    pass
            else:
                self.log("   ❌ No encontrado", 'error')
            
            # Buscar Crear imágenes
            self.set_status("🔍 Buscando 'Crear imágenes'...")
            self.set_progress(55)
            self.log("\n📌 Buscando opción 'Crear imágenes'...", 'info')
            
            crear_candidates = self.driver.execute_script("""
                const elements = Array.from(document.querySelectorAll('button, div[role="menuitem"], li'));
                return elements.map(e => ({
                    text: e.innerText?.trim() || '',
                    ariaLabel: e.getAttribute('aria-label') || '',
                    tagName: e.tagName,
                    visible: e.offsetWidth > 0 && e.offsetHeight > 0
                })).filter(e => 
                    e.visible && (
                        e.text.toLowerCase().includes('crear imagen') ||
                        e.ariaLabel.toLowerCase().includes('crear imagen')
                    )
                );
            """)
            
            if crear_candidates:
                best = crear_candidates[0]
                self.selectors['crear_imagenes'] = best
                self.log(f"   ✅ Encontrado: text='{best['text']}'", 'success')
            else:
                self.log("   ❌ No encontrado en menú abierto", 'warning')
            
            # Buscar botón upload
            self.set_status("🔍 Buscando botón de subida...")
            self.set_progress(70)
            self.log("\n📌 Buscando botón de subida...", 'info')
            
            upload_candidates = self.driver.execute_script("""
                const buttons = Array.from(document.querySelectorAll('button'));
                return buttons.map(b => ({
                    ariaLabel: b.getAttribute('aria-label') || '',
                    visible: b.offsetWidth > 0 && b.offsetHeight > 0
                })).filter(b => 
                    b.visible && (
                        b.ariaLabel.toLowerCase().includes('subida') ||
                        b.ariaLabel.toLowerCase().includes('upload') ||
                        b.ariaLabel.toLowerCase().includes('adjuntar')
                    )
                );
            """)
            
            if upload_candidates:
                self.selectors['upload_button'] = upload_candidates[0]
                self.log(f"   ✅ Encontrado: aria-label='{upload_candidates[0]['ariaLabel']}'", 'success')
            else:
                self.log("   ⚠️ No encontrado directamente", 'warning')
            
            # Buscar botón enviar
            self.set_status("🔍 Buscando botón enviar...")
            self.set_progress(85)
            self.log("\n📌 Buscando botón enviar...", 'info')
            
            send_candidates = self.driver.execute_script("""
                const buttons = Array.from(document.querySelectorAll('button'));
                return buttons.map(b => ({
                    ariaLabel: b.getAttribute('aria-label') || '',
                    visible: b.offsetWidth > 0 && b.offsetHeight > 0
                })).filter(b => 
                    b.visible && (
                        b.ariaLabel.toLowerCase().includes('enviar') ||
                        b.ariaLabel.toLowerCase().includes('send')
                    )
                );
            """)
            
            if send_candidates:
                self.selectors['send_button'] = send_candidates[0]
                self.log(f"   ✅ Encontrado: aria-label='{send_candidates[0]['ariaLabel']}'", 'success')
            else:
                self.log("   ⚠️ No encontrado", 'warning')
            
            # Guardar reporte
            self.set_status("💾 Guardando reporte...")
            self.set_progress(95)
            report_path = os.path.join(os.path.dirname(__file__), "selectors_report.json")
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(self.selectors, f, indent=2, ensure_ascii=False)
            self.log(f"\n💾 Reporte guardado: selectors_report.json", 'info')
            
            # Completado
            self.set_progress(100)
            self.set_status("✅ Inspección completada", '#00ff88')
            self.log("\n" + "=" * 50, 'header')
            self.log("✅ INSPECCIÓN COMPLETADA", 'success')
            self.log("=" * 50, 'header')
            self.log("\nSelectores encontrados:", 'info')
            self.log(json.dumps(self.selectors, indent=2, ensure_ascii=False), 'info')
            
            # Habilitar botón de reparación
            self.repair_btn.config(state=tk.NORMAL)
            
        except Exception as e:
            self.set_status(f"❌ Error: {str(e)[:50]}...", '#ff4757')
            self.log(f"\n❌ ERROR: {e}", 'error')
        finally:
            self.running = False
            self.start_btn.config(state=tk.NORMAL)
    
    def apply_repair(self):
        """Aplica los cambios al script principal."""
        if not self.selectors:
            messagebox.showwarning("Aviso", "Primero ejecuta la inspección")
            return
        
        self.set_status("🔧 Aplicando reparación...")
        self.log("\n" + "=" * 50, 'header')
        self.log("🔧 APLICANDO REPARACIÓN", 'header')
        self.log("=" * 50, 'header')
        
        if not os.path.exists(MAIN_SCRIPT):
            self.log(f"\n❌ No se encontró: {MAIN_SCRIPT}", 'error')
            return
        
        # Crear backup
        backup_path = MAIN_SCRIPT + ".backup"
        with open(MAIN_SCRIPT, 'r', encoding='utf-8') as f:
            original = f.read()
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original)
        self.log(f"\n📦 Backup creado: gemini_translator.py.backup", 'success')
        
        content = original
        changes = 0
        
        # Actualizar Herramientas
        if 'tools_button' in self.selectors:
            new_label = self.selectors['tools_button'].get('ariaLabel', '')
            if new_label:
                old = "button[aria-label='Herramientas']"
                new = f"button[aria-label='{new_label}']"
                if old in content and old != new:
                    content = content.replace(old, new)
                    changes += 1
                    self.log(f"   ✅ Actualizado: Herramientas → {new_label}", 'success')
        
        # Actualizar Enviar
        if 'send_button' in self.selectors:
            new_label = self.selectors['send_button'].get('ariaLabel', '')
            if new_label and 'Enviar mensaje' != new_label:
                content = content.replace('Enviar mensaje', new_label)
                changes += 1
                self.log(f"   ✅ Actualizado: Enviar → {new_label}", 'success')
        
        if changes > 0:
            with open(MAIN_SCRIPT, 'w', encoding='utf-8') as f:
                f.write(content)
            self.log(f"\n✅ Script actualizado con {changes} cambio(s)", 'success')
            self.set_status(f"✅ Reparación aplicada ({changes} cambios)", '#00ff88')
            messagebox.showinfo("Éxito", f"Script actualizado con {changes} cambio(s)")
        else:
            self.log("\n ℹ️ No se necesitaron cambios", 'info')
            self.set_status("ℹ️ No se necesitaron cambios", '#00d9ff')
            messagebox.showinfo("Info", "Los selectores ya están actualizados")
    
    def run_translator(self):
        """Ejecuta el script de traducción en un proceso separado."""
        if self.translator_process and self.translator_process.poll() is None:
            messagebox.showwarning("Aviso", "El traductor ya está en ejecución")
            return
        
        self.log_text.delete(1.0, tk.END)
        self.log("=" * 50, 'header')
        self.log("🍌 INICIANDO GEMINI NANO BANANA TRANSLATOR", 'header')
        self.log("=" * 50, 'header')
        self.log("")
        
        self.set_status("🍌 Ejecutando traductor...", '#ffa502')
        self.set_progress(0)
        self.run_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # Ejecutar en hilo separado
        thread = threading.Thread(target=self._run_translator_thread)
        thread.daemon = True
        thread.start()
    
    def _run_translator_thread(self):
        """Hilo que ejecuta el proceso del traductor."""
        import subprocess
        import sys
        
        try:
            self.log("🚀 Iniciando proceso...", 'info')
            
            # En Windows, abrir en una ventana nueva visible
            if sys.platform == 'win32':
                # Usar CREATE_NEW_CONSOLE para que el usuario pueda ver e interactuar
                self.translator_process = subprocess.Popen(
                    [sys.executable, "-u", MAIN_SCRIPT],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    cwd=os.path.dirname(MAIN_SCRIPT)
                )
                self.log("📺 Se abrió una ventana de consola separada", 'info')
                self.log("👉 Presiona Enter en esa ventana para iniciar", 'warning')
                self.log("", 'info')
                self.log("⏳ Esperando a que el proceso termine...", 'info')
                
                # Esperar a que termine
                self.translator_process.wait()
                
            else:
                # En otros sistemas, ejecutar normalmente
                self.translator_process = subprocess.Popen(
                    [sys.executable, "-u", MAIN_SCRIPT],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    cwd=os.path.dirname(MAIN_SCRIPT)
                )
                
                # Enviar Enter automático
                time.sleep(2)
                try:
                    self.translator_process.stdin.write("\n")
                    self.translator_process.stdin.flush()
                except:
                    pass
                
                # Leer output
                for line in iter(self.translator_process.stdout.readline, ''):
                    if line:
                        self.log(line.strip(), 'info')
                    if self.translator_process.poll() is not None:
                        break
            
            # Proceso terminado
            self.log("\n" + "=" * 50, 'header')
            self.log("✅ PROCESO COMPLETADO", 'success')
            self.log("=" * 50, 'header')
            self.set_status("✅ Traducción completada", '#00ff88')
            self.set_progress(100)
            
        except Exception as e:
            self.log(f"\n❌ Error: {e}", 'error')
            self.set_status(f"❌ Error: {str(e)[:30]}...", '#ff4757')
        finally:
            self.run_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.translator_process = None
    
    def stop_translator(self):
        """Detiene el proceso del traductor."""
        if self.translator_process:
            try:
                self.translator_process.terminate()
                self.translator_process.kill()
                self.log("\n⏹️ Proceso detenido por el usuario", 'warning')
                self.set_status("⏹️ Detenido", '#ff6b6b')
            except:
                pass
            finally:
                self.translator_process = None
                self.run_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
    
    def close_app(self):
        """Cierra la aplicación."""
        # Detener traductor si está corriendo
        if self.translator_process:
            try:
                self.translator_process.terminate()
            except:
                pass
        
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = RepairToolGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.close_app)
    root.mainloop()


if __name__ == "__main__":
    main()
