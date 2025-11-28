import sys
import os
import random
import math
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# --- KONFIGURÁCIÓ ÉS GLOBÁLIS VÁLTOZÓK ---
DEFAULT_WORLD_FILE = "world_save.json"

# Kép fájlnevek
IMG_SOAP = "png-clipart-soap-soap-thumbnail-removebg-preview.png"
IMG_STICKMAN = "st_large_507x507-pad_600x600_f8f8f8-removebg-preview.png"
IMG_BG = "hatter.jpg"

# Típusok erősorrendje
STRONG_AGAINST = {
    "levego": "fold",
    "fold": "tuz",
    "tuz": "viz",
    "viz": "levego"
}
WEAK_AGAINST = {
    "levego": "tuz",
    "tuz": "levego",
    "fold": "viz",
    "viz": "fold"
}

# Vicces beszólások a Koboldtól (ÚJ FEATURE)
KOBOLD_QUOTES_ATTACK = [
    "A macskám nagyobbat üt ennél!",
    "Hű, ez fájt... volna, ha érdekelne!",
    "Ezt hívod te támadásnak?!",
    "Bumm! A közepébe! Vagy mellé...",
    "Most kellene izgulnom?",
    "Hozzon már valaki egy sört!",
    "Ez a meccs lassabb, mint a csigafutam!",
    "Na végre, vér!",
    "A nagymamám erősebb, pedig ő már nem is él!",
    "Piff-puff, dirr-durr, mi van itt kérem?"
]

KOBOLD_QUOTES_PLAY = [
    "Már megint ez a lap? Uncsi.",
    "Hűha, előkerült a 'nagyágyú'... ja nem.",
    "Ettől most be kéne tojni?",
    "Szép kártya. Kár, hogy béna vagy.",
    "Na, ki jött a buliba?",
    "Én a helyedben nem ezt raktam volna...",
    "Végre valami akció!",
    "Ez a lap bűzlik, mint a lábam."
]

# GUI Színek és Stílusok
TYPE_COLORS = {
    "tuz": "#e74c3c",  # Piros
    "viz": "#3498db",  # Kék
    "fold": "#27ae60",  # Zöld
    "levego": "#f1c40f",  # Sárga/Arany
    "default": "#95a5a6"  # Szürke
}
BG_COLOR = "#2c3e50"  # Sötétkék háttér
CARD_BG = "#34495e"  # Kártya háttér
TEXT_COLOR = "#ecf0f1"  # Világos szöveg


def normalize_text(text):
    """Ekezetek eltavolitasa es kisbetusites."""
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ö': 'o', 'ő': 'o',
        'ú': 'u', 'ü': 'u', 'ű': 'u', 'Á': 'A', 'É': 'E', 'Í': 'I',
        'Ó': 'O', 'Ö': 'O', 'Ú': 'U', 'Ü': 'U', 'Ű': 'U'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.lower().strip()


# --- ADATMODELL OSZTÁLYOK ---

class Card:
    def __init__(self, name, dmg, hp, type_name):
        self.name = name
        self.base_dmg = int(dmg)
        self.max_hp = int(hp)
        self.current_hp = int(hp)
        self.type = normalize_text(type_name)
        self.original_type_str = type_name

    def to_dict(self):
        return {
            "name": self.name, "dmg": self.base_dmg,
            "hp": self.max_hp, "type": self.original_type_str
        }

    @staticmethod
    def from_dict(data):
        return Card(data["name"], data["dmg"], data["hp"], data["type"])

    def __str__(self):
        return f"[{self.original_type_str.upper()}] {self.name} (DMG: {self.base_dmg} | HP: {self.max_hp})"


class Dungeon:
    def __init__(self, type_id, name, cards, leader=None, reward_type=None):
        self.type_id = type_id
        self.name = name
        self.cards = cards
        self.leader = leader
        self.reward_type = reward_type

    def get_full_enemy_list(self):
        enemies = [Card(c.name, c.base_dmg, c.max_hp, c.original_type_str) for c in self.cards]
        if self.leader:
            enemies.append(
                Card(self.leader.name, self.leader.base_dmg, self.leader.max_hp, self.leader.original_type_str))
        return enemies

    def to_dict(self):
        return {
            "type_id": self.type_id, "name": self.name,
            "cards": [c.name for c in self.cards],
            "leader": self.leader.name if self.leader else None,
            "reward_type": self.reward_type
        }


class GameState:
    def __init__(self):
        self.world_cards = {}
        self.dungeons = []
        self.player_collection = []
        self.player_deck = []
        self.difficulty = 0

    def save_to_file(self, filename):
        data = {
            "world_cards": [c.to_dict() for c in self.world_cards.values()],
            "dungeons": [d.to_dict() for d in self.dungeons],
            "player_collection": [c.name for c in self.player_collection],
            "player_deck": [c.name for c in self.player_deck],
            "difficulty": self.difficulty
        }
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Hiba a mentesnel: {e}")

    def load_from_file(self, filename):
        if not os.path.exists(filename): return False
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.world_cards = {}
            for c_data in data["world_cards"]:
                card = Card.from_dict(c_data)
                self.world_cards[card.name] = card

            self.dungeons = []
            for d_data in data["dungeons"]:
                d_cards = [self.world_cards[name] for name in d_data["cards"] if name in self.world_cards]
                leader = self.world_cards.get(d_data["leader"]) if d_data["leader"] else None
                self.dungeons.append(Dungeon(d_data["type_id"], d_data["name"], d_cards, leader, d_data["reward_type"]))

            self.player_collection = [self.world_cards[name] for name in data["player_collection"] if
                                      name in self.world_cards]
            self.player_deck = [self.world_cards[name] for name in data["player_deck"] if name in self.world_cards]
            self.difficulty = data.get("difficulty", 0)
            return True
        except Exception as e:
            print(f"Hiba a betoltesnel: {e}")
            return False

    def create_default_world(self):
        cards_data = [
            ("Arin", 2, 5, "fold"), ("Liora", 2, 4, "levego"), ("Nerun", 3, 3, "tuz"),
            ("Selia", 2, 6, "viz"), ("Torak", 3, 4, "fold"), ("Emera", 2, 5, "levego"),
            ("Vorn", 2, 7, "viz"), ("Kael", 3, 5, "tuz"), ("Myra", 2, 6, "fold"),
            ("Thalen", 3, 5, "levego"), ("Isara", 2, 6, "viz")
        ]
        for name, d, h, t in cards_data:
            self.world_cards[name] = Card(name, d, h, t)

        self.world_cards["Lord Torak"] = Card("Lord Torak", 6, 4, "fold")
        self.world_cards["Priestess Selia"] = Card("Priestess Selia", 2, 12, "viz")

        self.dungeons.append(Dungeon("egyszeru", "Barlangi Portya", [self.world_cards["Nerun"]], None, "sebzes"))

        osisz_cards = [self.world_cards[n] for n in ["Arin", "Emera", "Selia"]]
        self.dungeons.append(Dungeon("kis", "Osi Szentely", osisz_cards, self.world_cards["Lord Torak"], "eletero"))

        melyseg_cards = [self.world_cards[n] for n in ["Liora", "Arin", "Selia", "Nerun", "Torak"]]
        self.dungeons.append(
            Dungeon("nagy", "A melyseg kiralynoje", melyseg_cards, self.world_cards["Priestess Selia"], None))

        start_coll = ["Arin", "Liora", "Selia", "Nerun", "Torak", "Emera", "Kael", "Myra", "Thalen", "Isara"]
        self.player_collection = [self.world_cards[n] for n in start_coll if n in self.world_cards]


# --- HARC LOGIKA ---

class BattleEngine:
    def __init__(self, player_deck, dungeon, difficulty_level, logger_func, is_game_mode=False):
        self.player_deck = [Card(c.name, c.base_dmg, c.max_hp, c.original_type_str) for c in player_deck]
        self.enemy_deck = dungeon.get_full_enemy_list()
        self.dungeon = dungeon
        self.difficulty = difficulty_level
        self.log = logger_func
        self.is_game_mode = is_game_mode

        self.turn = 1
        self.battle_over = False
        self.winner = None

        self.p_idx = 0
        self.e_idx = 0

        self.p_card_played = False
        self.e_card_played = False
        self.next_actor = "enemy"

        # TÖRÖLVE: IDŐJÁRÁS LOGIKA (weather)

    # TÖRÖLVE: get_weather_bonus függvény

    def calculate_damage(self, attacker, defender, is_dungeon_atk):
        atk_t = normalize_text(attacker.type)
        def_t = normalize_text(defender.type)

        base_dmg = attacker.base_dmg

        # TÖRÖLVE: Időjárás bónusz hozzáadása

        modifier = 1.0
        if STRONG_AGAINST.get(atk_t) == def_t:
            modifier = 2.0
        elif WEAK_AGAINST.get(atk_t) == def_t:
            modifier = 0.5

        current_dmg = math.floor(base_dmg * modifier)

        if self.is_game_mode and self.difficulty > 0:
            n = self.difficulty
            rnd = random.random()

            if is_dungeon_atk:
                current_dmg = round(current_dmg * (1 + (rnd * n / 10)))
            else:
                current_dmg = round(current_dmg * (1 - (rnd * n / 20)))

        return int(current_dmg)

    def step(self):
        if self.battle_over: return

        if self.p_idx >= len(self.player_deck):
            self.end_battle("enemy")
            return
        if self.e_idx >= len(self.enemy_deck):
            self.end_battle("player")
            return

        p_card = self.player_deck[self.p_idx]
        e_card = self.enemy_deck[self.e_idx]

        if not self.e_card_played:
            self.log("play", self.turn, "kazamata", e_card, None, 0)
            self.e_card_played = True
            return

        if not self.p_card_played:
            self.log("play", self.turn, "jatekos", p_card, None, 0)
            self.p_card_played = True
            return

        attacker_owner = self.next_actor
        attacker = e_card if attacker_owner == "enemy" else p_card
        defender = p_card if attacker_owner == "enemy" else e_card
        is_dungeon_atk = (attacker_owner == "enemy")

        final_dmg = self.calculate_damage(attacker, defender, is_dungeon_atk)

        defender.current_hp -= final_dmg
        self.log("attack", self.turn, attacker_owner, attacker, defender, final_dmg)

        if defender.current_hp <= 0:
            if not is_dungeon_atk and attacker.current_hp > 0:
                attacker.current_hp = min(attacker.max_hp, attacker.current_hp + 1)

            if attacker_owner == "enemy":
                self.p_idx += 1
                self.p_card_played = False
                self.next_actor = "enemy"
            else:
                self.e_idx += 1
                self.e_card_played = False
                self.next_actor = "enemy"
            self.turn += 1
        else:
            self.next_actor = "player" if self.next_actor == "enemy" else "enemy"
            if attacker_owner == "player":
                self.turn += 1

    def end_battle(self, winner_code):
        self.battle_over = True
        self.winner = winner_code


# --- MINIGAME (FÜRDÉS) ---

class BathMinigame:
    def __init__(self, root, on_finish_callback):
        self.root = root
        self.on_finish = on_finish_callback
        self.width, self.height = 800, 600
        self.player_speed, self.soap_speed = 12, 5
        self.spawn_rate = 1500
        self.load_assets()
        self.setup_ui()
        self.running = True
        self.score = 0
        self.soaps = []
        self.pressed_keys = {'a': False, 'd': False}
        self.canvas.bind('<KeyPress>', self.on_key_press)
        self.canvas.bind('<KeyRelease>', self.on_key_release)
        self.canvas.focus_set()
        self.game_loop()
        self.spawner()

    def load_assets(self):
        self.img_soap = None
        self.img_stickman = None
        self.img_bg = None

        try:
            raw_stick = tk.PhotoImage(file=IMG_STICKMAN)
            self.img_stickman = raw_stick.subsample(6, 6)
        except:
            pass
        try:
            raw_soap = tk.PhotoImage(file=IMG_SOAP)
            self.img_soap = raw_soap.subsample(8, 8)
        except:
            pass
        try:
            self.img_bg = tk.PhotoImage(file='hatter.png')
        except:
            pass

    def setup_ui(self):
        for widget in self.root.winfo_children(): widget.destroy()
        self.canvas = tk.Canvas(self.root, width=self.width, height=self.height, bg="#87CEEB")
        self.canvas.pack()

        if self.img_bg:
            self.canvas.create_image(0, 0, image=self.img_bg, anchor="nw")

        start_x, start_y = self.width // 2, self.height - 80
        if self.img_stickman:
            self.player = self.canvas.create_image(start_x, start_y, image=self.img_stickman, anchor="center")
        else:
            self.player = self.canvas.create_rectangle(start_x - 20, start_y - 40, start_x + 20, start_y + 40,
                                                       fill="black")
        self.txt_score = self.canvas.create_text(20, 20, text="Szappanok: 0 / 20", anchor="nw", font=("Segoe UI", 16),
                                                 fill="white")

    def on_key_press(self, event):
        if event.keysym.lower() in self.pressed_keys: self.pressed_keys[event.keysym.lower()] = True

    def on_key_release(self, event):
        if event.keysym.lower() in self.pressed_keys: self.pressed_keys[event.keysym.lower()] = False

    def spawner(self):
        if not self.running: return
        x = random.randint(30, self.width - 30)
        s_id = self.canvas.create_image(x, -50, image=self.img_soap,
                                        anchor="center") if self.img_soap else self.canvas.create_oval(x - 15, -60,
                                                                                                       x + 15, -40,
                                                                                                       fill="pink")
        self.soaps.append({"id": s_id, "speed": random.randint(3, 7)})
        self.root.after(max(500, self.spawn_rate - (self.score * 50)), self.spawner)

    def check_collision(self, s_item):
        p, s = self.canvas.bbox(self.player), self.canvas.bbox(s_item["id"])
        if not p or not s: return False
        return not (p[2] < s[0] or p[0] > s[2] or p[3] < s[1] or p[1] > s[3])

    def game_loop(self):
        if not self.running: return
        dx = 0
        if self.pressed_keys['a']: dx -= self.player_speed
        if self.pressed_keys['d']: dx += self.player_speed
        self.canvas.move(self.player, dx, 0)

        to_remove = []
        for soap in self.soaps:
            self.canvas.move(soap["id"], 0, soap["speed"])
            s_bbox = self.canvas.bbox(soap["id"])
            if self.check_collision(soap):
                self.score += 1
                self.canvas.itemconfig(self.txt_score, text=f"Szappanok: {self.score} / 20")
                self.canvas.delete(soap["id"])
                to_remove.append(soap)
                if self.score >= 20:
                    self.running = False
                    messagebox.showinfo("Siker", "Tiszta vagy!")
                    self.on_finish()
                    return
            elif s_bbox and s_bbox[1] > self.height:
                self.running = False
                messagebox.showerror("Vége", "Leesett a szappan!")
                self.on_finish()
                return
        for r in to_remove: self.soaps.remove(r)
        self.root.after(20, self.game_loop)


# --- GUI IMPLEMENTÁCIÓ ---

class App:
    def __init__(self, root, cli_args):
        self.root = root
        self.root.title("Damareen - II. Forduló")
        self.root.geometry("1100x750")
        self.root.configure(bg=BG_COLOR)

        # Stílus konfiguráció
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background=BG_COLOR)
        self.style.configure("TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", background=BG_COLOR, foreground="#f39c12", font=("Cinzel", 36, "bold"))
        self.style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)

        self.game_state = GameState()
        if not self.game_state.load_from_file(DEFAULT_WORLD_FILE):
            self.game_state.create_default_world()
        self.setup_main_menu()

    def clear_window(self):
        for widget in self.root.winfo_children(): widget.destroy()

    def setup_main_menu(self):
        self.clear_window()
        frame = ttk.Frame(self.root)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(frame, text="DAMAREEN", style="Title.TLabel").pack(pady=30)

        diff_frame = ttk.LabelFrame(frame, text=" Játék Beállítások ", padding=15)
        diff_frame.pack(pady=20, fill="x")

        row1 = ttk.Frame(diff_frame)
        row1.pack(fill="x", pady=5)
        ttk.Label(row1, text="Nehézségi Szint (0-10):").pack(side="left", padx=5)
        self.diff_var = tk.IntVar(value=self.game_state.difficulty)
        tk.Spinbox(row1, from_=0, to=10, textvariable=self.diff_var, width=5, font=("Segoe UI", 12)).pack(side="right")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Kaland Indítása", command=self.start_game_ui, width=20).pack(pady=5)
        ttk.Button(btn_frame, text="Játék Mentése", command=lambda: self.game_state.save_to_file(DEFAULT_WORLD_FILE),
                   width=20).pack(pady=5)
        ttk.Button(btn_frame, text="Játék Betöltése", command=self.load_game, width=20).pack(pady=5)

        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=15)
        ttk.Button(frame, text="🛁 FÜRDÉS MINIGAME 🛁", command=lambda: BathMinigame(self.root, self.setup_main_menu),
                   width=25).pack(pady=5)
        ttk.Button(frame, text="Kilépés", command=self.root.quit, width=20).pack(pady=15)

    def load_game(self):
        f = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if f and self.game_state.load_from_file(f):
            self.diff_var.set(self.game_state.difficulty)
            messagebox.showinfo("Infó", "Játék sikeresen betöltve!")

    def start_game_ui(self):
        self.game_state.difficulty = self.diff_var.get()
        self.setup_hub()

    def setup_hub(self):
        self.clear_window()

        header = ttk.Frame(self.root, padding=10)
        header.pack(fill="x")
        ttk.Button(header, text="⬅ Vissza a Menübe", command=self.setup_main_menu).pack(side="left")
        ttk.Label(header, text="Kártya Hub", style="Header.TLabel").pack(side="left", padx=20)

        content = ttk.Frame(self.root, padding=10)
        content.pack(expand=True, fill="both")

        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.columnconfigure(2, weight=1)
        content.rowconfigure(0, weight=1)

        lf_coll = ttk.LabelFrame(content, text=" Gyűjteményed ", padding=10)
        lf_coll.grid(row=0, column=0, sticky="nsew", padx=5)

        self.coll_list = tk.Listbox(lf_coll, bg="#34495e", fg="white", font=("Consolas", 10),
                                    selectbackground="#e67e22")
        self.coll_list.pack(fill="both", expand=True)
        self.coll_list.bind('<Double-1>', self.add_to_deck)
        ttk.Label(lf_coll, text="(Dupla klikk: Hozzáadás)", font=("Segoe UI", 8)).pack(anchor="e")

        lf_deck = ttk.LabelFrame(content, text=" Aktív Pakli ", padding=10)
        lf_deck.grid(row=0, column=1, sticky="nsew", padx=5)

        self.deck_list = tk.Listbox(lf_deck, bg="#2c3e50", fg="#2ecc71", font=("Consolas", 10),
                                    selectbackground="#c0392b")
        self.deck_list.pack(fill="both", expand=True)
        self.deck_list.bind('<Double-1>', self.remove_from_deck)
        self.lbl_deck_info = ttk.Label(lf_deck, text="0 lap", font=("Segoe UI", 8))
        self.lbl_deck_info.pack(anchor="e")

        lf_dung = ttk.LabelFrame(content, text=" Kazamaták ", padding=10)
        lf_dung.grid(row=0, column=2, sticky="nsew", padx=5)

        self.dungeon_list = tk.Listbox(lf_dung, bg="#2c3e50", fg="#f1c40f", font=("Segoe UI", 11),
                                       selectbackground="#8e44ad")
        self.dungeon_list.pack(fill="both", expand=True)
        for d in self.game_state.dungeons:
            rew = f"Jutalom: {d.reward_type}" if d.reward_type else "Jutalom: Új lap"
            self.dungeon_list.insert(tk.END, f"{d.name} ({d.type_id}) - {rew}")

        action_bar = ttk.Frame(self.root, padding=20)
        action_bar.pack(fill="x")
        ttk.Button(action_bar, text="⚔ HARC INDÍTÁSA ⚔", command=self.start_battle, width=30).pack()

        self.refresh_lists()

    def refresh_lists(self):
        self.coll_list.delete(0, tk.END)
        self.deck_list.delete(0, tk.END)

        for c in self.game_state.player_collection:
            icon = "🔥" if c.type == "tuz" else "💧" if c.type == "viz" else "🌿" if c.type == "fold" else "💨"
            self.coll_list.insert(tk.END, f"{icon} {c.name} ({c.base_dmg}/{c.max_hp})")

        for c in self.game_state.player_deck:
            icon = "🔥" if c.type == "tuz" else "💧" if c.type == "viz" else "🌿" if c.type == "fold" else "💨"
            self.deck_list.insert(tk.END, f"{icon} {c.name} ({c.base_dmg}/{c.max_hp})")

        limit = math.ceil(len(self.game_state.player_collection) / 2)
        curr = len(self.game_state.player_deck)
        self.lbl_deck_info.config(text=f"Pakli mérete: {curr} / {limit}")

    def add_to_deck(self, e):
        sel = self.coll_list.curselection()
        if not sel: return
        limit = math.ceil(len(self.game_state.player_collection) / 2)
        if len(self.game_state.player_deck) >= limit:
            messagebox.showwarning("Tele a pakli", f"Maximum {limit} kártyát vihetsz magaddal!")
            return
        self.game_state.player_deck.append(self.game_state.player_collection[sel[0]])
        self.refresh_lists()

    def remove_from_deck(self, e):
        sel = self.deck_list.curselection()
        if sel:
            del self.game_state.player_deck[sel[0]]
            self.refresh_lists()

    def start_battle(self):
        if not self.game_state.player_deck: return messagebox.showerror("Hiba", "Üres paklival nem indulhatsz csatába!")
        sel = self.dungeon_list.curselection()
        if not sel: return messagebox.showerror("Hiba", "Válassz kazamatát!")
        dungeon = self.game_state.dungeons[sel[0]]

        if dungeon.type_id == "nagy":
            has_new = False
            for c in self.game_state.world_cards.values():
                if c.type in ["tuz", "viz", "fold", "levego"] and not any(
                        pc.name == c.name for pc in self.game_state.player_collection):
                    has_new = True;
                    break
            if not has_new: return messagebox.showinfo("Mester",
                                                       "Már mindent megtanultál, amit ettől a kazamatától lehet!")

        self.setup_battle_ui(dungeon)

    # --- ÚJ HARC FELÜLET ELEMEI ---

    def create_card_widget(self, parent, card, is_active=True):
        if not card: return ttk.Frame(parent)

        type_color = TYPE_COLORS.get(normalize_text(card.type), TYPE_COLORS["default"])
        border_color = "#f39c12" if is_active else "#7f8c8d"

        card_frame = tk.Frame(parent, bg=border_color, padx=3, pady=3)

        inner = tk.Frame(card_frame, bg=CARD_BG, width=180, height=250)
        inner.pack_propagate(False)
        inner.pack()

        tk.Label(inner, text=card.type.upper(), bg=type_color, fg="white", font=("Segoe UI", 10, "bold")).pack(fill="x")

        icon = "🔥" if card.type == "tuz" else "💧" if card.type == "viz" else "🌿" if card.type == "fold" else "💨"
        tk.Label(inner, text=icon, bg=CARD_BG, fg=type_color, font=("Segoe UI", 40)).pack(pady=20)

        tk.Label(inner, text=card.name, bg=CARD_BG, fg="white", font=("Cinzel", 12, "bold"), wraplength=160).pack()

        stats_frame = tk.Frame(inner, bg=CARD_BG)
        stats_frame.pack(side="bottom", fill="x", pady=5)

        tk.Label(stats_frame, text=f"⚔ {card.base_dmg}", bg=CARD_BG, fg="#e74c3c", font=("Segoe UI", 12, "bold")).pack(
            side="left", padx=15)
        tk.Label(stats_frame, text=f"❤ {card.current_hp}/{card.max_hp}", bg=CARD_BG, fg="#2ecc71",
                 font=("Segoe UI", 12, "bold")).pack(side="right", padx=15)

        return card_frame

    def setup_battle_ui(self, dungeon):
        self.clear_window()

        self.battle_engine = BattleEngine(self.game_state.player_deck, dungeon, self.game_state.difficulty,
                                          self.log_battle, is_game_mode=True)

        # 1. Felső Sáv: Infó és A KOBOLD (ÚJ)
        top_frame = tk.Frame(self.root, bg="#2c3e50")
        top_frame.pack(fill="x", pady=10)

        tk.Label(top_frame, text=f"Helyszín: {dungeon.name}", font=("Cinzel", 20, "bold"), bg="#2c3e50",
                 fg="white").pack()

        # A RÉSZEG KOBOLD KOMMENTÁTOR HELYE
        self.lbl_kobold = tk.Label(top_frame, text="Kobold: 'Hukk! Kezdődjön a mészárlás!'",
                                   font=("Segoe UI", 14, "italic"), bg="#2c3e50", fg="#00ff00")
        self.lbl_kobold.pack(pady=5)

        # 2. Középső Aréna: Ellenség vs Játékos
        self.arena_frame = tk.Frame(self.root, bg=BG_COLOR)
        self.arena_frame.pack(expand=True, fill="both", padx=20)

        self.arena_frame.columnconfigure(0, weight=1)  # Enemy
        self.arena_frame.columnconfigure(1, weight=0)  # VS
        self.arena_frame.columnconfigure(2, weight=1)  # Player

        self.enemy_slot = tk.Frame(self.arena_frame, bg=BG_COLOR)
        self.enemy_slot.grid(row=0, column=0)

        tk.Label(self.arena_frame, text="VS", font=("Cinzel", 30, "bold"), bg=BG_COLOR, fg="#e74c3c").grid(row=0,
                                                                                                           column=1,
                                                                                                           padx=20)

        self.player_slot = tk.Frame(self.arena_frame, bg=BG_COLOR)
        self.player_slot.grid(row=0, column=2)

        # 3. Alsó Sáv: Log és Gombok
        bottom_frame = ttk.Frame(self.root, padding=10)
        bottom_frame.pack(fill="x", side="bottom")

        log_frame = ttk.LabelFrame(bottom_frame, text=" Harci Napló ")
        log_frame.pack(fill="x", pady=5)
        self.log_text = tk.Text(log_frame, height=6, bg="#222", fg="#ecf0f1", font=("Consolas", 9))
        self.log_text.pack(fill="x")

        self.btn_next = ttk.Button(bottom_frame, text="KÖVETKEZŐ KÖR >>", command=self.next_turn)
        self.btn_next.pack(fill="x", pady=5, ipady=5)

        self.update_ui()

    def log_battle(self, action, turn, owner, card, target, dmg):
        owner_str = "KAZAMATA" if owner == "kazamata" else "TE"

        msg = f"[{turn}. Kör] {owner_str}: {card.name}"
        kobold_text = ""

        if action == "attack":
            msg += f" megtámadja {target.name}-t. Sebzés: {dmg}"
            # KOBOLD REAGÁL A TÁMADÁSRA
            kobold_text = random.choice(KOBOLD_QUOTES_ATTACK)
        elif action == "play":
            msg += " harcba lép."
            # KOBOLD REAGÁL A KIJÁTSZÁSRA
            kobold_text = random.choice(KOBOLD_QUOTES_PLAY)

        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

        # Frissítjük a Kobold szövegét
        if self.lbl_kobold:
            self.lbl_kobold.config(text=f"Kobold: '{kobold_text}'")

    def update_ui(self):
        for w in self.enemy_slot.winfo_children(): w.destroy()
        for w in self.player_slot.winfo_children(): w.destroy()

        be = self.battle_engine

        if be.e_idx < len(be.enemy_deck):
            ec = be.enemy_deck[be.e_idx]
            cw = self.create_card_widget(self.enemy_slot, ec)
            cw.pack()
            pb = ttk.Progressbar(self.enemy_slot, length=180, maximum=ec.max_hp, value=ec.current_hp)
            pb.pack(pady=5)
            tk.Label(self.enemy_slot, text="ELLENSÉG", bg=BG_COLOR, fg="#e74c3c", font=("Segoe UI", 10, "bold")).pack()
        else:
            tk.Label(self.enemy_slot, text="☠ LEGYŐZVE ☠", font=("Segoe UI", 16, "bold"), bg=BG_COLOR,
                     fg="#7f8c8d").pack()

        if be.p_idx < len(be.player_deck):
            pc = be.player_deck[be.p_idx]
            cw = self.create_card_widget(self.player_slot, pc)
            cw.pack()
            pb = ttk.Progressbar(self.player_slot, length=180, maximum=pc.max_hp, value=pc.current_hp)
            pb.pack(pady=5)
            tk.Label(self.player_slot, text="TE", bg=BG_COLOR, fg="#3498db", font=("Segoe UI", 10, "bold")).pack()
        else:
            tk.Label(self.player_slot, text="☠ KIESTÉL ☠", font=("Segoe UI", 16, "bold"), bg=BG_COLOR,
                     fg="#7f8c8d").pack()

    def next_turn(self):
        if self.battle_engine.battle_over:
            if self.battle_engine.winner == "player":
                self.apply_reward()
                messagebox.showinfo("Győzelem", "Gratulálok! Diadalmaskodtál a kazamatában!")
            else:
                messagebox.showinfo("Vereség", "Sajnos alulmaradtál. Próbáld újra!")
            self.setup_hub()
            return

        self.battle_engine.step()
        self.update_ui()
        if self.battle_engine.battle_over:
            self.btn_next.config(text="HARC VÉGE - Vissza a térképre")
            self.lbl_kobold.config(text="Kobold: 'Na, vége a mókának. Ki fizet?'")

    def apply_reward(self):
        be = self.battle_engine
        if not be.player_deck: return
        last_card_name = be.player_deck[min(be.p_idx, len(be.player_deck) - 1)].name
        orig = next((c for c in self.game_state.player_collection if c.name == last_card_name), None)
        if not orig: return

        dt = be.dungeon.type_id
        rt = be.dungeon.reward_type

        if dt in ["egyszeru", "kis"]:
            if rt == "sebzes":
                orig.base_dmg += 1
            elif rt == "eletero":
                orig.max_hp += 2;
                orig.current_hp = orig.max_hp
        elif dt == "nagy":
            for c in self.game_state.world_cards.values():
                if c.type in ["tuz", "viz", "fold", "levego"] and not any(
                        pc.name == c.name for pc in self.game_state.player_collection):
                    self.game_state.player_collection.append(Card(c.name, c.base_dmg, c.max_hp, c.original_type_str))
                    break


# --- TESZT MÓD (I. FORDULÓ LOGIKA - VÁLTOZATLAN) ---

def run_test_mode(input_arg):
    if os.path.isfile(input_arg):
        input_path = input_arg
        input_dir = os.path.dirname(input_path)
    else:
        input_dir = input_arg
        input_path = os.path.join(input_dir, "in.txt")

    if not os.path.exists(input_path): return

    game = GameState()
    known_leaders = set()

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Hiba a fajl olvasasakor: {e}")
        return

    for line in lines:
        line = line.strip()
        if not line or line.startswith("//"): continue

        parts = [p.strip() for p in line.split(';')]
        if not parts: continue
        cmd = parts[0]

        if cmd == "uj kartya":
            if len(parts) >= 5:
                game.world_cards[parts[1]] = Card(parts[1], parts[2], parts[3], parts[4])

        elif cmd == "uj vezer":
            if len(parts) >= 4 and parts[2] in game.world_cards:
                base = game.world_cards[parts[2]]
                dmg, hp = base.base_dmg, base.max_hp
                if "sebzes" in parts[3]:
                    dmg *= 2
                elif "eletero" in parts[3]:
                    hp *= 2
                game.world_cards[parts[1]] = Card(parts[1], dmg, hp, base.original_type_str)
                known_leaders.add(parts[1])

        elif cmd == "uj kazamata":
            if len(parts) >= 4:
                cards = []
                card_names = parts[3].split(',')
                for x in card_names:
                    x = x.strip()
                    if x in game.world_cards:
                        cards.append(game.world_cards[x])

                leader = None
                reward = None

                if parts[1] == "egyszeru":
                    if len(parts) > 4: reward = parts[4]
                elif parts[1] == "kis":
                    if len(parts) > 4 and parts[4] in game.world_cards: leader = game.world_cards[parts[4]]
                    if len(parts) > 5: reward = parts[5]
                elif parts[1] == "nagy":
                    if len(parts) > 4 and parts[4] in game.world_cards: leader = game.world_cards[parts[4]]

                game.dungeons.append(Dungeon(parts[1], parts[2], cards, leader, reward))

        elif cmd == "uj jatekos":
            game.player_collection = []

        elif cmd == "felvetel gyujtemenybe":
            if len(parts) >= 2 and parts[1] in game.world_cards:
                b = game.world_cards[parts[1]]
                game.player_collection.append(Card(b.name, b.base_dmg, b.max_hp, b.original_type_str))

        elif cmd == "uj pakli":
            if len(parts) >= 2:
                game.player_deck = []
                deck_names = [x.strip() for x in parts[1].split(',')]
                for n in deck_names:
                    found = next((c for c in game.player_collection if c.name == n), None)
                    if found: game.player_deck.append(found)

        elif cmd == "harc":
            if len(parts) >= 3:
                d_name, out_file = parts[1], parts[2]
                dungeon = next((d for d in game.dungeons if d.name == d_name), None)
                if not dungeon: continue

                logs = [f"harc kezdodik; {dungeon.name}"]

                def fl(action, turn, owner, c, t, d):
                    if action == "play":
                        logs.append(
                            f"{turn}.kor; {owner};kijatszik; {c.name};{c.base_dmg};{c.max_hp}; {c.original_type_str}")
                    elif action == "attack":
                        logs.append(f"{turn}.kor; {owner};tamad; {c.name}; {d}; {t.name}; {max(0, t.current_hp)}")

                # FONTOS: is_game_mode=False!
                eng = BattleEngine(game.player_deck, dungeon, 0, fl, is_game_mode=False)
                while not eng.battle_over:
                    eng.step()

                if eng.winner == "player":
                    idx = min(eng.p_idx, len(eng.player_deck) - 1)
                    if idx < 0: idx = 0

                    if eng.player_deck:
                        lc = eng.player_deck[idx]
                        orig = next((c for c in game.player_collection if c.name == lc.name), None)
                        res = ""
                        if dungeon.type_id != "nagy":
                            if dungeon.reward_type == "sebzes":
                                if orig: orig.base_dmg += 1
                            elif dungeon.reward_type == "eletero":
                                if orig:
                                    orig.max_hp += 2
                                    orig.current_hp = orig.max_hp
                            res = f"jatekos nyert; {dungeon.reward_type}; {lc.name}"
                        else:
                            new_c = None
                            for wc in game.world_cards.values():
                                if wc.type in ["tuz", "viz", "fold", "levego"] and not any(
                                        pc.name == wc.name for pc in game.player_collection):
                                    new_c = wc
                                    break
                            if new_c:
                                game.player_collection.append(
                                    Card(new_c.name, new_c.base_dmg, new_c.max_hp, new_c.original_type_str))
                                res = f"jatekos nyert; {new_c.name}"
                            else:
                                res = "jatekos nyert; nincs uj kartya"
                        logs.append(res)
                    else:
                        logs.append("jatekos nyert; hiba")
                else:
                    logs.append("jatekos vesztett")

                try:
                    with open(os.path.join(input_dir, out_file), 'w', encoding='utf-8') as f:
                        f.write("\n".join(logs))
                except Exception as e:
                    print(f"Hiba mentesnel: {e}")

        elif cmd.startswith("export"):
            if len(parts) >= 2:
                out_file = parts[1]
                lines_out = []
                if "vilag" in cmd:
                    for c in game.world_cards.values():
                        p = "vezer" if c.name in known_leaders else "kartya"
                        lines_out.append(f"{p}; {c.name};{c.base_dmg};{c.max_hp};{c.original_type_str}")
                    for d in game.dungeons:
                        l = f"kazamata; {d.type_id}; {d.name}; " + ", ".join([c.name for c in d.cards])
                        if d.leader: l += f"; {d.leader.name}"
                        if d.reward_type: l += f"; {d.reward_type}"
                        lines_out.append(l)
                else:
                    for c in game.player_collection:
                        lines_out.append(f"gyujtemeny; {c.name}; {c.base_dmg};{c.max_hp};{c.original_type_str}")
                    for c in game.player_deck:
                        lines_out.append(f"pakli; {c.name}")

                try:
                    with open(os.path.join(input_dir, out_file), 'w', encoding='utf-8') as f:
                        f.write("\n".join(lines_out))
                except Exception as e:
                    print(f"Hiba exportnal: {e}")


# --- MAIN ENTRY POINT ---

if __name__ == "__main__":
    if "--ui" in sys.argv:
        root = tk.Tk()
        app = App(root, sys.argv)
        root.mainloop()
    elif len(sys.argv) > 1:
        run_test_mode(sys.argv[1])
    else:
        # Ha csak siman inditjak, induljon a GUI
        root = tk.Tk()
        app = App(root, sys.argv)
        root.mainloop()