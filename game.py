import pygame
import random
import math
import time
from pygame.locals import *

# --- Constants ---
WIDTH, HEIGHT = 800, 600
PLAY_ROWS = 200
BEDROCK_THICKNESS = 3
ROWS = PLAY_ROWS + BEDROCK_THICKNESS
COLS = 200
TILE_SIZE = 32
PIXEL_SIZE = 8

# Physics
GRAVITY = 1600
JUMP_POWER = -520
BASE_MAX_SPEED = 650
BASE_ACCELERATION = 2200
FRICTION = 1600
MINING_RANGE = 100
AIR_RESISTANCE = 0.9

# Weather
DAY_LENGTH = 120  # Seconds
NIGHT_LENGTH = 60
FULL_CYCLE = DAY_LENGTH + NIGHT_LENGTH

# Block definitions
BLOCK_TYPES = {
    'dirt':       {'color': (101, 67, 33),   'hardness': 2},
    'stone':      {'color': (100, 100, 100), 'hardness': 3},
    'wood':       {'color': (139, 69, 19),   'hardness': 2},
    'leaves':     {'color': (34, 139, 34),   'hardness': 1},
    'diamond_ore':{'color': (0, 255, 255),   'hardness': 5},
    'gold_ore':   {'color': (255, 215, 0),   'hardness': 4},
    'iron_ore':   {'color': (211, 211, 211), 'hardness': 3},
    'coal':       {'color': (50, 50, 50),    'hardness': 2},
    'amethyst':   {'color': (153, 102, 204), 'hardness': 4},
    'ruby':       {'color': (224, 17, 95),   'hardness': 4},
    'magnesium':  {'color': (200, 200, 200), 'hardness': 3},
    'zinc':       {'color': (230, 230, 230), 'hardness': 3},
    'copper':     {'color': (184, 115, 51),  'hardness': 3},
    'tungsten':   {'color': (128, 128, 128), 'hardness': 5},
    'water':      {'color': (0, 0, 255),     'hardness': 0},
    'bedrock':    {'color': (0, 0, 0),       'hardness': 9999}
}

BLOCK_XP = {
    'dirt': 1,
    'stone': 2,
    'wood': 3,
    'leaves': 1,
    'diamond_ore': 50,
    'gold_ore': 25,
    'iron_ore': 15,
    'coal': 5,
    'amethyst': 20,
    'ruby': 20,
    'magnesium': 10,
    'zinc': 10,
    'copper': 10,
    'tungsten': 30,
    'water': 0,
    'bedrock': 0
}

# Player & UI colors
PLAYER_COLORS = {
    'hurt': (255, 0, 0),
    'walk1': (0, 255, 0),
    'walk2': (0, 128, 0),
    'idle': (0, 0, 255)
}

HEALTH_BAR_COLOR = (255, 0, 0)
STAMINA_BAR_COLOR = (0, 255, 0)
INVENTORY_SELECTED = (255, 255, 255)
INVENTORY_BG = (100, 100, 100)
DEFAULT_INVENTORY_SLOTS = 5

# --- Utility Functions ---
def lerp_color(color1, color2, t):
    return tuple(int(c1 * (1 - t) + c2 * t) for c1, c2 in zip(color1, color2))

def perlin_noise(width, seed=None):
    if seed is not None:
        random.seed(seed)
    p = list(range(width))
    random.shuffle(p)
    p += p
    return p

def noise(x, p):
    xi = int(x) % 256
    xf = x - int(x)
    u = fade(xf)
    a = p[xi]
    b = p[xi+1]
    return lerp(u, grad(a, xf), grad(b, xf-1))

def fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)

def lerp(t, a, b):
    return a + t * (b - a)

def grad(hash, x):
    h = hash & 15
    grad = 1 + (h & 7)
    if h & 8:
        grad = -grad
    return grad * x

# ---Tree Class--
class TreeGenerator:
    @staticmethod
    def generate_tree(world, x, ground_y):
        tree_height = random.randint(5, 9)
        trunk_width = random.choice([1, 1, 1, 2])  # 25% chance for wide trunk
        
        # Generate trunk
        for y in range(ground_y - tree_height, ground_y):
            for dx in range(trunk_width):
                if 0 <= x + dx < COLS:
                    world[y][x + dx] = {'type': 'wood', 'texture': None}
        
        # Generate canopy
        canopy_center = ground_y - tree_height
        canopy_radius = random.randint(3, 5)
        for dy in range(-canopy_radius, canopy_radius + 1):
            for dx in range(-canopy_radius, canopy_radius + 1):
                if dx*dx + dy*dy <= canopy_radius**2:
                    cy = canopy_center + dy
                    cx = x + dx + (trunk_width-1)/2
                    if 0 <= cx < COLS and 0 <= cy < ROWS and world[cy][cx] is None:
                        world[cy][cx] = {'type': 'leaves', 'texture': None}
                        
# ---name-
class WorldNameInput:
    def __init__(self):
        self.font = pygame.font.Font(None, 40)
        self.world_name = ""
        self.seed = ""
        self.active_field = "name"
        self.cursor_visible = True
        self.cursor_timer = 0
        
    def draw(self, screen):
        screen.fill((30, 30, 30))
        title = self.font.render("Create New World", True, (255, 255, 255))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
        
        # World name input
        name_text = self.font.render("World Name: " + self.world_name + ("|" if self.cursor_visible and self.active_field == "name" else ""), 
                                    True, (255, 255, 255))
        screen.blit(name_text, (WIDTH//2 - 300, 150))
        
        # Seed input
        seed_text = self.font.render("Seed: " + self.seed + ("|" if self.cursor_visible and self.active_field == "seed" else ""), 
                                   True, (255, 255, 255))
        screen.blit(seed_text, (WIDTH//2 - 300, 220))
        
        # Instructions
        instr = self.font.render("Press TAB to switch fields, ENTER to confirm", True, (200, 200, 200))
        screen.blit(instr, (WIDTH//2 - instr.get_width()//2, 300))
        
    def handle_input(self, event):
        if event.type == KEYDOWN:
            if event.key == K_TAB:
                self.active_field = "seed" if self.active_field == "name" else "name"
            elif event.key == K_BACKSPACE:
                if self.active_field == "name":
                    self.world_name = self.world_name[:-1]
                else:
                    self.seed = self.seed[:-1]
            elif event.key == K_RETURN:
                if self.world_name.strip() != "":
                    return True
            else:
                text = event.unicode
                if text.isprintable():
                    if self.active_field == "name" and len(self.world_name) < 20:
                        self.world_name += text
                    elif self.active_field == "seed" and len(self.seed) < 20:
                        self.seed += text
        return False

                        
# --- Weather Class ----
class WeatherSystem:
    def __init__(self):
        self.time = 0
        self.clouds = [self.create_cloud() for _ in range(10)]
        self.stars = []
        
    def create_cloud(self):
        return {
            'x': random.uniform(-WIDTH, WIDTH*2),
            'y': random.uniform(50, 150),
            'speed': random.uniform(0.5, 2.0),
            'size': random.randint(30, 80)
        }
    
    def update(self, dt):
        self.time = (self.time + dt) % FULL_CYCLE
        
        # Update clouds
        for cloud in self.clouds:
            cloud['x'] += cloud['speed'] * dt * 60
            if cloud['x'] > WIDTH + 200:
                cloud.update(self.create_cloud())
                cloud['x'] = -200
    
    def draw(self, screen):
        # Draw day/night cycle
        if self.is_day():
            sky_color = self.calculate_sky_color()
            screen.fill(sky_color)
            
            # Draw sun
            sun_pos = self.time / DAY_LENGTH
            sun_x = WIDTH * sun_pos
            sun_y = HEIGHT//4 * (1 + math.sin(sun_pos * math.pi))
            pygame.draw.circle(screen, (255, 255, 100), (int(sun_x), int(sun_y)), 40)
            
            # Draw clouds
            for cloud in self.clouds:
                alpha = min(255, int(150 + 100 * math.sin(cloud['x']/100)))
                cloud_surf = pygame.Surface((cloud['size'], cloud['size']//2), pygame.SRCALPHA)
                pygame.draw.ellipse(cloud_surf, (255, 255, 255, alpha), cloud_surf.get_rect())
                screen.blit(cloud_surf, (cloud['x'], cloud['y']))
        else:
            # Draw stars
            if len(self.stars) < 100:
                self.stars.append((
                    random.randint(0, WIDTH),
                    random.randint(0, HEIGHT//2),
                    random.uniform(0.5, 1.5)
                ))
            for star in self.stars:
                brightness = min(255, int(200 * abs(math.sin(self.time * 2))))
                pygame.draw.circle(screen, (brightness, brightness, brightness)), 
                ((int(star[0]), int(star[1])), int(star[2]))
    
    def is_day(self):
        return self.time < DAY_LENGTH
    
    def calculate_sky_color(self):
        day_color = (135, 206, 235)
        night_color = (25, 25, 112)
        blend = abs((self.time % (DAY_LENGTH/2)) - DAY_LENGTH/4) / (DAY_LENGTH/4)
        return tuple(int(day * (1-blend) + night * blend) for day, night in zip(day_color, night_color))


class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = TILE_SIZE
        self.height = TILE_SIZE
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.selected_slot = 0
        self.inventory = {0: ("Pickaxe", 1)}
        self.health = 100
        self.max_health = 100
        self.stamina = 100
        self.max_stamina = 100
        self.level = 1
        self.experience = 0
        self.mining_progress = 0
        self.mining_target = (0, 0)
        self.hurt_timer = 0
        self.animation_frame = 0
        self.direction = 1
        self.inventory_slots = DEFAULT_INVENTORY_SLOTS
        self.air_time = 0
        self.coyote_time = 0.15
        self.jump_buffer_time = 0
        self.movement_multiplier = 1.0
        self.double_jump_unlocked =False
        self.triple_jump_unlocked =False
        
    def update(self, world, delta_time):
        keys = pygame.key.get_pressed()
        
        # Horizontal movement with air control
        target_speed = 0
        if keys[K_LEFT] or keys[K_a]:
            target_speed = -BASE_MAX_SPEED
        if keys[K_RIGHT] or keys[K_d]:
            target_speed = BASE_MAX_SPEED
            
        # Smooth acceleration
        self.vel_x += (target_speed - self.vel_x) * (BASE_ACCELERATION if self.on_ground else BASE_ACCELERATION/3) * delta_time
        
        # Apply friction
        if not any([keys[K_LEFT], keys[K_RIGHT], keys[K_a], keys[K_d]]):
            if self.on_ground:
                self.vel_x *= 1 - FRICTION * delta_time
            else:
                self.vel_x *= AIR_RESISTANCE
        
        # Jump buffering and coyote time
        if self.on_ground:
            self.coyote_time = 0.15
        else:
            self.coyote_time -= delta_time
            
        if keys[K_SPACE] or keys[K_w]:
            self.jump_buffer_time = 0.1
        else:
            self.jump_buffer_time -= delta_time
            
        if self.jump_buffer_time > 0 and self.coyote_time > 0:
            self.vel_y = JUMP_POWER
            self.on_ground = False
            self.coyote_time = 0
            self.jump_buffer_time = 0

    def update(self, world, delta_time):
        keys = pygame.key.get_pressed()
        acceleration = BASE_ACCELERATION * self.movement_multiplier
        max_speed = BASE_MAX_SPEED * self.movement_multiplier

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x -= acceleration * delta_time
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x += acceleration * delta_time
        else:
            if self.vel_x > 0:
                self.vel_x = max(0, self.vel_x - FRICTION * delta_time)
            elif self.vel_x < 0:
                self.vel_x = min(0, self.vel_x + FRICTION * delta_time)
        self.vel_x = max(-max_speed, min(max_speed, self.vel_x))

        new_x = self.x + self.vel_x * delta_time
        top = self.y
        bottom = self.y + self.height
        if self.vel_x < 0:
            col = int(new_x // TILE_SIZE)
            for row in range(int(top // TILE_SIZE), int(bottom // TILE_SIZE) + 1):
                if 0 <= row < ROWS and 0 <= col < COLS and world[row][col] is not None:
                    new_x = (col + 1) * TILE_SIZE
                    self.vel_x = 0
                    break
        elif self.vel_x > 0:
            col = int((new_x + self.width) // TILE_SIZE)
            for row in range(int(top // TILE_SIZE), int(bottom // TILE_SIZE) + 1):
                if 0 <= row < ROWS and col < COLS and world[row][col] is not None:
                    new_x = col * TILE_SIZE - self.width
                    self.vel_x = 0
                    break
        self.x = new_x

        if not self.on_ground:
            self.vel_y += GRAVITY * delta_time
        new_y = self.y + self.vel_y * delta_time
        bottom = new_y + self.height
        bottom_row = int(bottom // TILE_SIZE)
        left_col = int(self.x // TILE_SIZE)
        right_col = int((self.x + self.width - 1) // TILE_SIZE)
        collided = False
        for col in range(left_col, right_col + 1):
            if bottom_row < ROWS and world[bottom_row][col] is not None:
                collided = True
                new_y = bottom_row * TILE_SIZE - self.height
                self.vel_y = 0
                self.on_ground = True
                break
        if not collided:
            self.on_ground = False
        self.y = new_y

        if self.on_ground:
            self.jumps_remaining = 1 + (1 if self.double_jump_unlocked else 0) + (1 if self.triple_jump_unlocked else 0)

        self.resolve_collisions(world)

    def is_colliding(self, world):
        rect = pygame.Rect(self.x, self.y, self.width, self.height)
        for row in range(int(self.y // TILE_SIZE), int((self.y+self.height) // TILE_SIZE)+1):
            for col in range(int(self.x // TILE_SIZE), int((self.x+self.width) // TILE_SIZE)+1):
                if 0 <= row < ROWS and 0 <= col < COLS and world[row][col] is not None:
                    block_rect = pygame.Rect(col*TILE_SIZE, row*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if rect.colliderect(block_rect):
                        return True
        return False

    def resolve_collisions(self, world):
        iterations = 0
        while self.is_colliding(world) and iterations < 10:
            orig_x, orig_y = self.x, self.y
            moved = False
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                self.x = orig_x + dx
                self.y = orig_y + dy
                if not self.is_colliding(world):
                    moved = True
                    break
            if not moved:
                self.x, self.y = orig_x, orig_y
                break
            iterations += 1

    def mine_block(self, world, grid_pos):
        col, row = grid_pos
        if 0 <= row < ROWS and 0 <= col < COLS:
            block = world[row][col]
            if block is None or block['type'] == 'bedrock':
                return
            bonus = (1 + 0.05 * (self.level - 1)) * self.pickaxe_multiplier
            hardness = BLOCK_TYPES[block['type']]['hardness'] * 20
            self.mining_progress += bonus
            if self.mining_progress >= hardness:
                block_type = block['type']
                xp_gain = BLOCK_XP.get(block_type, BLOCK_TYPES[block_type]['hardness'] * 10)
                self.experience += xp_gain
                while self.experience >= self.level * 100:
                    self.experience -= self.level * 100
                    self.level += 1
                if block_type in self.inventory:
                    name, count = self.inventory[block_type]
                    self.inventory[block_type] = (name, count + 1)
                else:
                    self.inventory[block_type] = (block_type, 1)
                world[row][col] = None
                self.mining_progress = 0
                cx = self.x + self.width / 2
                cy = self.y + self.height / 2
                if col * TILE_SIZE <= cx < (col + 1) * TILE_SIZE and row * TILE_SIZE <= cy < (row + 1) * TILE_SIZE:
                    self.x = col * TILE_SIZE
                    self.y = row * TILE_SIZE

class ParallaxLayer:
    def __init__(self, color, speed, points):
        self.color = color
        self.speed = speed
        self.points = points

# --- Parallax Layers ---
PARALLAX_LAYERS = [
    ParallaxLayer((90, 90, 120), 0.03, [(0, HEIGHT), (WIDTH, HEIGHT), (WIDTH, HEIGHT + 100), (0, HEIGHT + 100)]),
    ParallaxLayer((70, 70, 100), 0.1, [(0, HEIGHT // 2), (WIDTH, HEIGHT // 2), (WIDTH, HEIGHT), (0, HEIGHT)]),
    ParallaxLayer((50, 50, 70), 0.2, [(0, HEIGHT // 3), (WIDTH, HEIGHT // 3), (WIDTH, HEIGHT // 2), (0, HEIGHT // 2)]),
]
# --- Game Class ---
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("NoiseTest 01")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.weather = WeatherSystem()
        self.input_handler = WorldNameInput()
        
        # Initialize debounce dictionary here
        self.debounce = {}
        
        # World generation parameters
        self.world_name = ""
        self.seed = ""
        self.get_world_info()
        
        self.texture_cache = {}
        self.block_surface_cache = {}
        self.noise_p = perlin_noise(256, self.seed if isinstance(self.seed, int) else hash(self.seed))
        self.world = self.generate_world()
        self.player = self.create_player()
        self.camera_x = 0
        self.camera_y = 0
        self.map_mode = False
        self.inventory_open = False
        self.minimap_scale = 0.01
        self.map_zoom = 0.5
        self.time_of_day = 0
        self.background_color = (135, 206, 235)
        self.last_time = time.time()
        self.minimap_surface = pygame.Surface((COLS * TILE_SIZE * self.minimap_scale, 
                                             ROWS * TILE_SIZE * self.minimap_scale))

    def get_world_info(self):
        # Replace old input with new system
        input_active = True
        clock = pygame.time.Clock()
        while input_active:
            self.input_handler.cursor_timer += clock.tick(60)/1000
            if self.input_handler.cursor_timer > 0.5:
                self.input_handler.cursor_visible = not self.input_handler.cursor_visible
                self.input_handler.cursor_timer = 0
                
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    exit()
                if self.input_handler.handle_input(event):
                    input_active = False
                    
            self.input_handler.draw(self.screen)
            pygame.display.flip()
        
        self.world_name = self.input_handler.world_name.strip()
        self.seed = self.input_handler.seed.strip() or str(random.randint(0, 10**6))
        
        while input_active:
            self.screen.fill((30, 30, 30))
            title = self.font.render("Create New World", True, (255, 255, 255))
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
            
            # World name input
            name_text = self.font.render("World Name: " + world_name, True, (255, 255, 255))
            self.screen.blit(name_text, (WIDTH//2 - 200, 150))
            
            # Seed input
            seed_text = self.font.render("Seed (optional): " + seed, True, (255, 255, 255))
            self.screen.blit(seed_text, (WIDTH//2 - 200, 200))
            
            # Instructions
            instr = self.font.render("Press Enter to start", True, (200, 200, 200))
            self.screen.blit(instr, (WIDTH//2 - instr.get_width()//2, 300))
            
            pygame.display.flip()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if world_name.strip() != "":
                            input_active = False
                            self.world_name = world_name.strip()
                            self.seed = hash(seed.strip()) % 1000000 if seed.strip() != "" else random.randint(0, 1000000)
                    elif event.key == pygame.K_BACKSPACE:
                        if current_input == "world_name":
                            world_name = world_name[:-1]
                        else:
                            seed = seed[:-1]
                    else:
                        char = event.unicode
                        if char:
                            if current_input == "world_name":
                                world_name += char
                            else:
                                seed += char
                    if event.key == pygame.K_TAB:
                        current_input = "seed" if current_input == "world_name" else "world_name"

        pygame.display.flip()

    def generate_world(self):
        world = [[None for _ in range(COLS)] for _ in range(ROWS)]
        stone_start = PLAY_ROWS * 2 // 3
        ground_levels = []

        for col in range(COLS):
            n = noise(col * 0.1, self.noise_p) * 0.5
            thickness = int(6 + n * 2)
            thickness = max(4, min(8, thickness))
            gl = stone_start - thickness
            gl = max(0, min(stone_start - 1, gl))
            ground_levels.append(gl)

            for row in range(gl, stone_start):
                world[row][col] = {'type': 'dirt', 'texture': self.generate_block_texture('dirt')}
            for row in range(stone_start, PLAY_ROWS):
                world[row][col] = {'type': 'stone', 'texture': self.generate_block_texture('stone')}

        for row in range(PLAY_ROWS, ROWS):
            for col in range(COLS):
                world[row][col] = {'type': 'bedrock', 'texture': self.generate_block_texture('bedrock')}

        for col in range(2, COLS - 2):
            if random.random() < 0.2:
                self.generate_tree(col, ground_levels[col], world)
        self.generate_ore_veins(world, stone_start)

        return world

    def generate_ore_veins(self, world, stone_start):
        ore_types = ["coal", "amethyst", "ruby", "magnesium", "zinc", "copper", "tungsten", "gold_ore", "diamond_ore", "iron_ore"]
        weights = [40, 2, 3, 15, 15, 20, 5, 8, 2, 10]
        num_veins = random.randint(10, 20)
        for _ in range(num_veins):
            ore_type = random.choices(ore_types, weights=weights, k=1)[0]
            length = random.randint(5, 20)
            start_col = random.randint(0, COLS - 1)
            start_row = random.randint(stone_start, PLAY_ROWS - 1)
            for _ in range(length):
                if 0 <= start_row < PLAY_ROWS and 0 <= start_col < COLS:
                    if world[start_row][start_col] is not None and world[start_row][start_col]['type'] == 'stone':
                        world[start_row][start_col] = {'type': ore_type, 'texture': self.generate_block_texture(ore_type)}
                dx, dy = random.choice([(1,0), (-1,0), (0,1), (0,-1), (1,1), (-1,-1), (1,-1), (-1,1)])
                start_col += dx
                start_row += dy

    def generate_tree(self, x, y, world):
        tree_height = random.randint(4, 7)
        for tree_y in range(max(0, y - tree_height), y):
            if world[tree_y][x] is None:
                world[tree_y][x] = {'type': 'wood', 'texture': self.generate_block_texture('wood')}
        leaf_radius = 2
        top_y = max(0, y - tree_height)
        for leaf_y in range(top_y - 1, top_y + 2):
            for leaf_x in range(x - leaf_radius, x + leaf_radius + 1):
                if 0 <= leaf_y < PLAY_ROWS and 0 <= leaf_x < COLS:
                    if world[leaf_y][leaf_x] is None and random.random() < 0.7:
                        world[leaf_y][leaf_x] = {'type': 'leaves', 'texture': self.generate_block_texture('leaves')}

    def generate_block_texture(self, block_type):
        if block_type in self.texture_cache:
            return self.texture_cache[block_type]
        base_color = BLOCK_TYPES.get(block_type, {'color': (0, 0, 0)})['color']
        tex = [
            [tuple(min(255, max(0, c + random.randint(-30, 30))) for c in base_color)
             for _ in range(PIXEL_SIZE)]
            for _ in range(PIXEL_SIZE)
        ]
        self.texture_cache[block_type] = tex
        return tex

    def create_player(self):
        mid_x = COLS // 2
        spawn_y = None
        for y in range(PLAY_ROWS):
            if self.world[y][mid_x] is not None and self.world[y][mid_x]['type'] == 'dirt':
                spawn_y = y - 2
                break
        if spawn_y is None or spawn_y < 0:
            spawn_y = 0
        return Player(mid_x * TILE_SIZE, spawn_y * TILE_SIZE)

    def handle_input(self, delta_time):
        keys = pygame.key.get_pressed()
        current_time = time.time()

        if keys[pygame.K_m] and current_time - self.debounce.get('m', 0) > 0.2:
            self.map_mode = not self.map_mode
            self.debounce['m'] = current_time

        if keys[pygame.K_e] and current_time - self.debounce.get('e', 0) > 0.2:
            self.inventory_open = not self.inventory_open
            self.debounce['e'] = current_time

        if keys[pygame.K_SPACE] or keys[pygame.K_w]:
            if self.player.on_ground:
                self.player.vel_y = JUMP_POWER
                self.player.on_ground = False
                self.player.jumps_remaining -= 1
            elif self.player.jumps_remaining > 0:
                self.player.vel_y = JUMP_POWER
                self.player.jumps_remaining -= 1

        if keys[pygame.K_r] and current_time - self.debounce.get('r', 0) > 0.2:
            self.world = self.generate_world()
            self.debounce['r'] = current_time

        for event in pygame.event.get([pygame.MOUSEBUTTONDOWN]):
            if event.button == 1:
                mouse_pos = pygame.mouse.get_pos()
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0]:
            mouse_pos = pygame.mouse.get_pos()
            grid_x = int((mouse_pos[0] + self.camera_x) // TILE_SIZE)
            grid_y = int((mouse_pos[1] + self.camera_y) // TILE_SIZE)
            player_center = (self.player.x + self.player.width // 2,
                             self.player.y + self.player.height // 2)
            block_center = (grid_x * TILE_SIZE + TILE_SIZE // 2,
                            grid_y * TILE_SIZE + TILE_SIZE // 2)
            if math.hypot(player_center[0] - block_center[0], player_center[1] - block_center[1]) < MINING_RANGE:
                self.player.mine_block(self.world, (grid_x, grid_y))
                self.player.mining_target = (grid_x, grid_y)

        for event in pygame.event.get([pygame.MOUSEWHEEL]):
            if self.map_mode:
                self.map_zoom += event.y * 0.05
                self.map_zoom = max(0.05, min(self.map_zoom, 1.0))

    def update_time(self, delta_time):
        self.time_of_day = (self.time_of_day + 5 * delta_time) % 100
        day_color = (135, 206, 235)
        night_color = (25, 25, 112)
        blend_factor = abs(50 - self.time_of_day) / 50
        self.background_color = lerp_color(day_color, night_color, blend_factor)

    def update_camera(self, delta_time):
        target_x = self.player.x - WIDTH / 2 + self.player.width / 2
        target_y = self.player.y - HEIGHT / 2 + self.player.height / 2
        smoothing = 5
        self.camera_x += (target_x - self.camera_x) * smoothing * delta_time
        self.camera_y += (target_y - self.camera_y) * smoothing * delta_time
        self.camera_x = max(0, min(self.camera_x, COLS * TILE_SIZE - WIDTH))
        self.camera_y = max(0, min(self.camera_y, ROWS * TILE_SIZE - HEIGHT))

    def get_block_surface(self, block):
        key = block['type']
        if key in self.block_surface_cache:
            return self.block_surface_cache[key]
        surface = pygame.Surface((TILE_SIZE, TILE_SIZE))
        pixel_size = TILE_SIZE // PIXEL_SIZE
        if key == 'bedrock':
            surface.fill((0, 0, 0))
            pygame.draw.rect(surface, (128, 0, 128), surface.get_rect(), 2)
        else:
            for i, row in enumerate(block['texture']):
                for j, color in enumerate(row):
                    pygame.draw.rect(surface, color, (j * pixel_size, i * pixel_size, pixel_size, pixel_size))
        self.block_surface_cache[key] = surface
        return surface

    def draw_minimap(self):
        self.minimap_surface.fill((0, 0, 0))
        sample_rate = 4
        mini_tile = max(1, int(TILE_SIZE * self.minimap_scale))
        for row in range(0, ROWS, sample_rate):
            for col in range(0, COLS, sample_rate):
                block = self.world[row][col]
                if block:
                    color = BLOCK_TYPES.get(block['type'], {}).get('color', (0, 0, 0))
                    pygame.draw.rect(self.minimap_surface, color, 
                                     (col * TILE_SIZE * self.minimap_scale,
                                      row * TILE_SIZE * self.minimap_scale,
                                      mini_tile, mini_tile))
        player_mini_x = self.player.x * self.minimap_scale
        player_mini_y = self.player.y * self.minimap_scale
        pygame.draw.rect(self.minimap_surface, (255, 255, 255), (player_mini_x, player_mini_y, mini_tile, mini_tile))
        self.screen.blit(self.minimap_surface, (WIDTH - self.minimap_surface.get_width() - 10, 10))

    def draw_map(self):
        map_width = int(COLS * TILE_SIZE * self.map_zoom)
        map_height = int(ROWS * TILE_SIZE * self.map_zoom)
        map_surface = pygame.Surface((map_width, map_height))
        for row in range(ROWS):
            for col in range(COLS):
                block = self.world[row][col]
                if block:
                    if block['type'] == 'bedrock':
                        color = (0, 0, 0)
                        pygame.draw.rect(map_surface, color,
                                         (col * TILE_SIZE * self.map_zoom,
                                          row * TILE_SIZE * self.map_zoom,
                                          TILE_SIZE * self.map_zoom,
                                          TILE_SIZE * self.map_zoom))
                        pygame.draw.rect(map_surface, (128, 0, 128),
                                         (col * TILE_SIZE * self.map_zoom,
                                          row * TILE_SIZE * self.map_zoom,
                                          TILE_SIZE * self.map_zoom,
                                          TILE_SIZE * self.map_zoom), 2)
                    else:
                        color = BLOCK_TYPES.get(block['type'], {}).get('color', (0, 0, 0))
                        pygame.draw.rect(map_surface, color,
                                         (col * TILE_SIZE * self.map_zoom,
                                          row * TILE_SIZE * self.map_zoom,
                                          TILE_SIZE * self.map_zoom,
                                          TILE_SIZE * self.map_zoom))
        player_rect = pygame.Rect(self.player.x * self.map_zoom, self.player.y * self.map_zoom,
                                  self.player.width * self.map_zoom, self.player.height * self.map_zoom)
        pygame.draw.rect(map_surface, (255, 255, 255), player_rect)
        map_rect = map_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.screen.blit(map_surface, map_rect.topleft)
        instruct = self.font.render("Map Mode - Mouse Wheel to Zoom, Press M to Exit", True, (255, 255, 255))
        self.screen.blit(instruct, (WIDTH // 2 - instruct.get_width() // 2, 20))

    def draw_inventory_overlay(self):
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        title = self.font.render("Inventory", True, (255, 255, 255))
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 40))
        start_y = 100
        for key, item in self.player.inventory.items():
            text = self.font.render(f"{item[0]}: {item[1]}", True, (255, 255, 255))
            self.screen.blit(text, (WIDTH//2 - text.get_width()//2, start_y))
            start_y += 30
        exit_text = self.font.render("Press E to Close Inventory", True, (255, 255, 255))
        self.screen.blit(exit_text, (WIDTH//2 - exit_text.get_width()//2, HEIGHT - 60))

    def draw(self):
        if self.map_mode:
            self.screen.fill((0, 0, 0))
            self.draw_map()
        else:
            self.screen.fill(self.background_color)
            for layer in PARALLAX_LAYERS:
                offset = -(self.camera_x * layer.speed) % (WIDTH * 2)
                points1 = [(x - offset, y) for x, y in layer.points]
                points2 = [(x - offset + WIDTH, y) for x, y in layer.points]
                pygame.draw.polygon(self.screen, layer.color, points1)
                pygame.draw.polygon(self.screen, layer.color, points2)
            start_row = max(0, int(self.camera_y // TILE_SIZE))
            end_row = min(ROWS, int((self.camera_y + HEIGHT) // TILE_SIZE + 1))
            start_col = max(0, int(self.camera_x // TILE_SIZE))
            end_col = min(COLS, int((self.camera_x + WIDTH) // TILE_SIZE + 1))
            for row in range(start_row, end_row):
                for col in range(start_col, end_col):
                    block = self.world[row][col]
                    if block:
                        screen_x = col * TILE_SIZE - int(self.camera_x)
                        screen_y = row * TILE_SIZE - int(self.camera_y)
                        texture_surface = self.get_block_surface(block)
                        self.screen.blit(texture_surface, (screen_x, screen_y))
                        if (col, row) == self.player.mining_target:
                            hardness = BLOCK_TYPES[block['type']]['hardness'] * 20
                            progress = self.player.mining_progress / hardness
                            bar_width = TILE_SIZE * progress
                            bar_height = 5
                            bar_x = screen_x
                            bar_y = screen_y - bar_height - 2
                            pygame.draw.rect(self.screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height))
            if self.player.hurt_timer > 0:
                player_color = PLAYER_COLORS['hurt']
            elif abs(self.player.vel_x) > 0.1:
                player_color = PLAYER_COLORS['walk1'] if self.player.animation_frame == 0 else PLAYER_COLORS['walk2']
            else:
                player_color = PLAYER_COLORS['idle']
            pygame.draw.rect(self.screen, player_color,
                             (self.player.x - int(self.camera_x),
                              self.player.y - int(self.camera_y),
                              self.player.width,
                              self.player.height))
            self.draw_ui()
            self.draw_minimap()
            if self.inventory_open:
                self.draw_inventory_overlay()

    def draw_ui(self):
        health_width = 200
        pygame.draw.rect(self.screen, (0, 0, 0), (10, 10, health_width + 4, 24))
        pygame.draw.rect(self.screen, HEALTH_BAR_COLOR,
                         (12, 12, health_width * (self.player.health / self.player.max_health), 20))
        stamina_width = 200
        pygame.draw.rect(self.screen, (0, 0, 0), (10, 40, stamina_width + 4, 24))
        pygame.draw.rect(self.screen, STAMINA_BAR_COLOR,
                         (12, 42, stamina_width * (self.player.stamina / self.player.max_stamina), 20))
        level_surface = self.font.render(f"Level {self.player.level}", True, (255, 255, 255))
        exp_surface = self.font.render(f"XP: {self.player.experience}/{self.player.level * 100}", True, (255, 255, 255))
        self.screen.blit(level_surface, (10, 70))
        self.screen.blit(exp_surface, (10, 95))
        for i in range(self.player.inventory_slots):
            slot_x = 10 + i * 60
            slot_y = HEIGHT - 70
            color = INVENTORY_SELECTED if i == self.player.selected_slot else INVENTORY_BG
            pygame.draw.rect(self.screen, color, (slot_x, slot_y, 50, 50))
            if i in self.player.inventory:
                item = self.player.inventory[i]
                text = self.font.render(f"{item[0]}:{item[1]}", True, (255, 255, 255))
                self.screen.blit(text, (slot_x + 5, slot_y + 15))

    def run(self):
        running = True
        while running:
            current_time = time.time()
            delta_time = current_time - self.last_time
            self.last_time = current_time
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_f:
                        pygame.display.toggle_fullscreen()
                if event.type == pygame.MOUSEWHEEL and self.map_mode:
                    self.map_zoom += event.y * 0.05
                    self.map_zoom = max(0.05, min(self.map_zoom, 1.0))
            self.handle_input(delta_time)
            if not self.map_mode:
                self.player.update(self.world, delta_time)
                self.update_time(delta_time)
                self.update_camera(delta_time)
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    try:
        game = Game()
        game.run()
    except Exception as e:
        print(f"Failed to start game: {str(e)}")
        pygame.quit()
