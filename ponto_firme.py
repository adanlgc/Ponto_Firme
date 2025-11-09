import pygame
import win32api
import win32con
import win32gui
import numpy as np
import pyautogui
import time
from numpy.linalg import inv

# ===============================
# CLASSE FILTRO DE KALMAN
# ===============================
class KalmanFilter:
    def __init__(self):
        self.X = np.zeros((4, 1))
        self.P = np.eye(4)
        self.F = np.array([[1, 0, 1, 0],
                           [0, 1, 0, 1],
                           [0, 0, 1, 0],
                           [0, 0, 0, 1]])
        self.H = np.array([[1, 0, 0, 0],
                           [0, 1, 0, 0]])
        self.Q = np.eye(4) * 0.001
        self.R = np.eye(2) * 10

    def predict(self):
        self.X = self.F @ self.X
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.X

    def update(self, Z):
        K = self.P @ self.H.T @ inv(self.H @ self.P @ self.H.T + self.R)
        self.X = self.X + K @ (Z - self.H @ self.X)
        self.P = (np.eye(4) - K @ self.H) @ self.P
        return self.X


# ===============================
# INTERFACE E CONFIGURAÇÕES
# ===============================
pygame.init()
pygame.font.init()

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()

# Cores
fuchsia = (255, 0, 128)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 150, 255)
YELLOW = (255, 255, 0)
UI_BG_COLOR = (30, 30, 30)
BTN_ON_COLOR = (0, 150, 0)
BTN_OFF_COLOR = (150, 0, 0)
BTN_TRACE_ON = (0, 80, 200)
BTN_TRACE_OFF = (100, 100, 100)

pygame.display.set_caption("Cursor com Filtro de Kalman + Trace + Clicker")

# Painel UI
UI_WIDTH = 240
UI_HEIGHT = 130
ui_panel_rect = pygame.Rect(WIDTH - UI_WIDTH, 0, UI_WIDTH, UI_HEIGHT)
ui_button_rect = pygame.Rect(WIDTH - UI_WIDTH + 20, 20, UI_WIDTH - 40, 40)
ui_trace_rect = pygame.Rect(WIDTH - UI_WIDTH + 20, 75, UI_WIDTH - 40, 40)
ui_font = pygame.font.SysFont('Arial', 20, bold=True)

# Janela transparente
hwnd = pygame.display.get_wm_info()["window"]
win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                       win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                       | win32con.WS_EX_LAYERED)

# Estado inicial
is_filter_active = True
trace_enabled = False
last_left_state = 0
last_middle_state = 0
ALPHA_LEVEL = 70

win32gui.SetLayeredWindowAttributes(hwnd, 0, ALPHA_LEVEL, win32con.LWA_ALPHA)
win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                      win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

pygame.display.flip()
clock = pygame.time.Clock()
kalman = KalmanFilter()
pygame.mouse.set_visible(True)

# Listas para armazenar o trace
trace_filtered = []
trace_real = []
click_positions = []

running = True
print("Filtro ativo (Modo Fantasma).")
print("Use o BOTÃO DO MEIO do mouse para clicar no Windows.")
print("Clique esquerdo na UI para Ligar/Desligar ou ativar o Trace.")
print("ESC para sair.\n")


# ===============================
# LOOP PRINCIPAL
# ===============================
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    if win32api.GetKeyState(win32con.VK_ESCAPE) < 0:
        running = False
        print("Tecla ESC pressionada. Encerrando...")

    # --- Atualiza Kalman ---
    mouse_pos = win32api.GetCursorPos()
    Z = np.array([[mouse_pos[0]], [mouse_pos[1]]])
    kalman.predict()
    filtered = kalman.update(Z)
    fx, fy = int(filtered[0, 0]), int(filtered[1, 0])

    # --- Verifica cliques ---
    current_left_state = win32api.GetKeyState(win32con.VK_LBUTTON)
    current_middle_state = win32api.GetKeyState(win32con.VK_MBUTTON)

    # ========== BOTÃO ESQUERDO: alterna UI ==========
    if current_left_state < 0 and last_left_state >= 0:
        if ui_button_rect.collidepoint((fx, fy)):
            is_filter_active = not is_filter_active
            if is_filter_active:
                print("Filtro LIGADO (Modo Fantasma).")
                win32gui.SetLayeredWindowAttributes(hwnd, 0, ALPHA_LEVEL, win32con.LWA_ALPHA)
            else:
                print("Filtro DESLIGADO (Transparente).")
                win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*fuchsia), 0, win32con.LWA_COLORKEY)

        elif ui_trace_rect.collidepoint((fx, fy)):
            trace_enabled = not trace_enabled
            print(f"Trace {'ATIVADO' if trace_enabled else 'DESLIGADO'}.")

    # ========== BOTÃO DO MEIO: click real no Windows ==========
    if current_middle_state < 0 and last_middle_state >= 0:
        filtered_pos = (int(kalman.X[0, 0]), int(kalman.X[1, 0]))
        fx_raw = int(kalman.X[0, 0])
        fy_raw = int(kalman.X[1, 0])
        
        fx = max(0, min(fx_raw, WIDTH - 1))
        fy = max(0, min(fy_raw, HEIGHT - 1))
        print(f"[CLICKER] Iniciando clique real em ({fx}, {fy})...")

        # Feedback visual — cursor maior e vermelho
        click_feedback_time = time.time() + 0.3

        pyautogui.moveTo(fx, fy, _pause=False)
        screen = pygame.display.set_mode((0, 0), pygame.HIDDEN)
        time.sleep(0.1)
        pyautogui.click(fx, fy, _pause=False)
        time.sleep(0.5)
        screen = pygame.display.set_mode((0, 0), pygame.SHOWN)
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        screen.fill(fuchsia)
        click_positions.append(filtered_pos)
        time.sleep(0.25)
        print("[CLICKER] Janela Pygame restaurada.\n")

    last_left_state = current_left_state
    last_middle_state = current_middle_state

    # --- Atualiza traces ---
    if trace_enabled:
        trace_filtered.append((fx, fy))
        trace_real.append(mouse_pos)

        if len(trace_filtered) > 1000:
            trace_filtered.pop(0)
            trace_real.pop(0)

    # --- Desenha ---
    screen.fill(BLACK if is_filter_active else fuchsia)

    if is_filter_active:
        # Desenha rastro se ativo
        if trace_enabled and len(trace_filtered) > 1:
            pygame.draw.lines(screen, BLUE, False, trace_filtered, 3)
            pygame.draw.lines(screen, YELLOW, False, trace_real, 2)

        # Se acabou de clicar com botão do meio, destaca o cursor
        if 'click_feedback_time' in locals() and time.time() < click_feedback_time:
            pygame.draw.circle(screen, RED, (fx, fy), 10)
        else:
            pygame.draw.circle(screen, WHITE, (fx, fy), 6)
            pygame.draw.circle(screen, RED, (fx, fy), 2)

    # --- UI ---
    pygame.draw.rect(screen, UI_BG_COLOR, ui_panel_rect)

    # Botão filtro
    btn_color = BTN_OFF_COLOR if is_filter_active else BTN_ON_COLOR
    btn_text = "DESLIGAR" if is_filter_active else "LIGAR"
    pygame.draw.rect(screen, btn_color, ui_button_rect)
    text_surf = ui_font.render(btn_text, True, WHITE)
    text_rect = text_surf.get_rect(center=ui_button_rect.center)
    screen.blit(text_surf, text_rect)

    # Botão trace
    trace_color = BTN_TRACE_ON if trace_enabled else BTN_TRACE_OFF
    trace_text = "TRACE: ON" if trace_enabled else "TRACE: OFF"
    pygame.draw.rect(screen, trace_color, ui_trace_rect)
    text_surf = ui_font.render(trace_text, True, WHITE)
    text_rect = text_surf.get_rect(center=ui_trace_rect.center)
    screen.blit(text_surf, text_rect)

    pygame.display.flip()
    clock.tick(60)

pygame.font.quit()
pygame.quit()
