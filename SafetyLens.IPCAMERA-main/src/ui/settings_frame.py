import tkinter as tk
from tkinter import ttk

class SettingsFrame(ttk.LabelFrame):
    def __init__(self, parent, config, on_settings_change):
        super().__init__(parent, text="Configurações do Sistema", style="Custom.TLabelframe")
        self.config = config
        self.on_settings_change = on_settings_change
        
        # Configuração de expansão do frame
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.setup_ui()

    def setup_ui(self):
        # Notebook para organizar as configurações em abas
        self.settings_notebook = ttk.Notebook(self)
        self.settings_notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Criar as três abas principais com ícones
        self.image_tab = ttk.Frame(self.settings_notebook)
        self.detection_tab = ttk.Frame(self.settings_notebook)
        self.alerts_tab = ttk.Frame(self.settings_notebook)

        self.settings_notebook.add(self.image_tab, text="🎥 Imagem")
        self.settings_notebook.add(self.detection_tab, text="🔍 Detecção")
        self.settings_notebook.add(self.alerts_tab, text="⚠️ Alertas")

        # Configurar cada aba
        self.setup_image_tab()
        self.setup_detection_tab()
        self.setup_alerts_tab()

    def create_slider_frame(self, parent, text, min_val, max_val, command, initial_value, unit=""):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", padx=5, pady=(10, 5))
        
        # Container para o texto e valor
        label_container = ttk.Frame(frame)
        label_container.pack(fill="x")
        
        # Label com ícone
        label = ttk.Label(label_container, text=text, font=("Segoe UI", 10))
        label.pack(side="left")
        
        # Label para o valor
        value_label = ttk.Label(label_container, width=8, font=("Segoe UI", 10))
        value_label.pack(side="right")
        
        # Slider com estilo personalizado
        scale = ttk.Scale(frame, from_=min_val, to=max_val, orient="horizontal")
        scale.set(initial_value)
        scale.pack(fill="x", pady=(5, 0))
        
        # Atualiza o valor inicial
        value_text = f"{initial_value}{unit}"
        value_label.config(text=value_text)
        
        # Configura o callback
        def on_scale_change(val):
            try:
                value = float(val)
                value_text = f"{value:.1f}{unit}" if isinstance(value, float) else f"{int(value)}{unit}"
                value_label.config(text=value_text)
                command(val)
            except ValueError:
                pass
                
        scale.config(command=on_scale_change)
        return scale

    def setup_image_tab(self):
        # Grupo de ajustes de imagem com borda
        adjustments_frame = ttk.LabelFrame(self.image_tab, text="Ajustes de Imagem", padding=10)
        adjustments_frame.pack(fill="x", padx=5, pady=5, ipady=5)

        # Carregar valores salvos do config
        saved_settings = self.config.config['camera']['default_settings']

        # Brilho
        self.brightness_scale = self.create_slider_frame(
            adjustments_frame, "🔆 Brilho", 0, 200,
            lambda v: self._update_setting('brightness', v),
            saved_settings['brightness'], "%"
        )

        # Contraste
        self.contrast_scale = self.create_slider_frame(
            adjustments_frame, "📊 Contraste", 0, 200,
            lambda v: self._update_setting('contrast', v),
            saved_settings['contrast'], "%"
        )

        # Nitidez
        self.sharpness_scale = self.create_slider_frame(
            adjustments_frame, "🔪 Nitidez", 0, 10,
            lambda v: self._update_setting('sharpness', v),
            saved_settings['sharpness']
        )

        # Escala de cinza com estilo moderno
        grayscale_frame = ttk.Frame(adjustments_frame)
        grayscale_frame.pack(fill="x", padx=5, pady=10)
        self.grayscale_var = tk.BooleanVar(value=saved_settings['grayscale'])
        self.grayscale_check = ttk.Checkbutton(
            grayscale_frame,
            text="🎨 Escala de Cinza",
            variable=self.grayscale_var,
            command=lambda: self._update_setting('grayscale', self.grayscale_var.get())
        )
        self.grayscale_check.pack(side="left")

    def setup_detection_tab(self):
        # Frame principal de detecção
        detection_frame = ttk.LabelFrame(self.detection_tab, text="Parâmetros de Detecção", padding=10)
        detection_frame.pack(fill="x", padx=5, pady=5)

        # Confiança mínima
        self.confidence_scale = self.create_slider_frame(
            detection_frame, "📈 Confiança Mínima", 0.0, 1.0,
            lambda v: self._update_setting('min_confidence', v),
            self.config.config['detection']['min_confidence']
        )

        # Status da detecção
        status_frame = ttk.LabelFrame(self.detection_tab, text="Status do Sistema", padding=10)
        status_frame.pack(fill="x", padx=5, pady=5)
        
        self.detection_indicator = ttk.Label(
            status_frame, 
            text="✅ Sistema Ativo",
            font=("Segoe UI", 10)
        )
        self.detection_indicator.pack(fill="x", padx=5, pady=5)

    def setup_alerts_tab(self):
        # Frame principal de alertas
        alerts_frame = ttk.LabelFrame(self.alerts_tab, text="Configurações de Alertas", padding=10)
        alerts_frame.pack(fill="x", padx=5, pady=5)

        # Frequência do alerta - lendo diretamente da seção alerts
        self.alert_freq_scale = self.create_slider_frame(
            alerts_frame, "🔊 Frequência", 100, 2000,
            lambda v: self._update_setting('alert_frequency', v),
            self.config.config['alerts']['frequency'], " Hz"
        )

        # Duração do alerta - lendo diretamente da seção alerts
        self.alert_duration_scale = self.create_slider_frame(
            alerts_frame, "⏱️ Duração", 100, 1000,
            lambda v: self._update_setting('alert_duration', v),
            self.config.config['alerts']['duration'], " ms"
        )

        # Tempo de delay - lendo diretamente da seção alerts
        self.delay_scale = self.create_slider_frame(
            alerts_frame, "⏲️ Intervalo", 0, 30,
            lambda v: self._update_setting('delay_time', v),
            self.config.config['alerts']['delay_time'], " s"
        )

    def _update_setting(self, setting_name, value):
        try:
            if setting_name in ['brightness', 'contrast', 'sharpness', 'alert_frequency', 'alert_duration', 'delay_time']:
                value = int(float(value))
            elif setting_name == 'min_confidence':
                value = float(value)
            
            self.on_settings_change(**{setting_name: value})
        except Exception as e:
            print(f"Erro ao atualizar configuração {setting_name}: {e}")

    def get_settings(self):
        return {
            'brightness': self.brightness_scale.get(),
            'contrast': self.contrast_scale.get(),
            'sharpness': self.sharpness_scale.get(),
            'grayscale': self.grayscale_var.get(),
            'min_confidence': self.confidence_scale.get(),
            'alert_frequency': self.alert_freq_scale.get(),
            'alert_duration': self.alert_duration_scale.get(),
            'delay_time': self.delay_scale.get()
        }

    def update_detection_status(self, status="Normal"):
        icon = "✅" if status == "Normal" else "⚠️"
        self.detection_indicator.config(text=f"{icon} {status}")