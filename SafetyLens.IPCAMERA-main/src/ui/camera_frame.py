import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
from src.core.config import Config

class CameraFrame(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Visualização da Câmera", style="Custom.TLabelframe")
        # Carrega a configuração para obter a resolução real
        self.config = Config()
        self.real_width, self.real_height = self.config.camera_resolution
        
        # Configura o grid para expansão
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.setup_ui()
        self._last_size = None
        self._last_frame = None
        
        self.bind('<Configure>', self._on_resize)

    def setup_ui(self):
        # Container principal para a câmera
        self.camera_container = ttk.Frame(self)
        self.camera_container.grid(row=0, column=0, sticky="nsew")
        
        # Configura o grid do container para permitir expansão total
        self.camera_container.grid_rowconfigure(0, weight=1)
        self.camera_container.grid_columnconfigure(0, weight=1)

        # Frame preto para mostrar a imagem da câmera
        self.camera_frame = ttk.Frame(self.camera_container, style="Camera.TFrame")
        self.camera_frame.grid(row=0, column=0, sticky="nsew")
        
        # Label para exibir a imagem da câmera
        self.camera_label = tk.Label(self.camera_frame, bg='black', bd=0, highlightthickness=0)
        self.camera_label.place(relx=0.5, rely=0.5, anchor="center")

        # Barra de status da câmera (parte inferior)
        self.status_bar = ttk.Frame(self)
        self.status_bar.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        self.status_bar.grid_columnconfigure(1, weight=1)

        # Status da câmera (esquerda)
        self.camera_status = ttk.Label(
            self.status_bar,
            text="📹 Câmera HD Ativa",
            font=("Segoe UI", 10)
        )
        self.camera_status.grid(row=0, column=0, sticky="w", padx=5)

        # Resolução (direita)
        self.resolution_label = ttk.Label(
            self.status_bar,
            text=f"{self.real_width}x{self.real_height}",
            font=("Segoe UI", 10)
        )
        self.resolution_label.grid(row=0, column=2, sticky="e", padx=5)

    def update_frame(self, frame):
        """Atualiza o frame da câmera na interface com redimensionamento responsivo"""
        if frame is not None:
            self._last_frame = frame.copy()
            self._update_display()

    def _update_display(self):
        """Atualiza a exibição do frame com o tamanho atual do container"""
        if self._last_frame is None:
            return

        try:
            # Obtém o tamanho atual do container
            container_width = self.camera_frame.winfo_width()
            container_height = self.camera_frame.winfo_height()

            if container_width > 1 and container_height > 1:
                # Obtém as dimensões da imagem original
                img_height, img_width = self._last_frame.shape[:2]
                
                # Calcula a escala mantendo a proporção
                scale_width = container_width / img_width
                scale_height = container_height / img_height
                scale = min(scale_width, scale_height) * 0.98  # 98% do espaço para margem
                
                # Calcula as novas dimensões
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)

                # Redimensiona o frame
                resized_frame = cv2.resize(
                    self._last_frame, 
                    (new_width, new_height),
                    interpolation=cv2.INTER_LANCZOS4
                )
                
                # Converte para formato PIL e depois para PhotoImage
                image = Image.fromarray(resized_frame)
                photo = ImageTk.PhotoImage(image)
                
                # Atualiza a imagem no label
                self.camera_label.configure(image=photo)
                self.camera_label.image = photo  # Mantém uma referência
                
                # Atualiza o tamanho e posição do label
                self.camera_label.configure(width=new_width, height=new_height)
                
                # Atualiza status
                self.camera_status.configure(text="📹 Câmera HD Ativa")
                
            else:
                self.camera_status.configure(text="⚠️ Ajustando visualização...")
                
        except Exception as e:
            print(f"Erro ao atualizar frame: {e}")
            self.camera_status.configure(text="❌ Erro na Câmera")

    def _on_resize(self, event):
        """Manipula eventos de redimensionamento da janela"""
        if self._last_size != (event.width, event.height):
            self._last_size = (event.width, event.height)
            self._update_display()