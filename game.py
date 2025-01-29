import pygame
import random
import math
from collections import defaultdict

# Initialize Pygame
pygame.init()
pygame.font.init()

# Get the display info to set ideal size
display_info = pygame.display.Info()
WIDTH = min(1280, display_info.current_w - 100)  # Leave some margin for windowed mode
HEIGHT = min(720, display_info.current_h - 100)
TILE_SIZE = 32  # Larger tiles for better visibility
PIXEL_SIZE = 8
ROWS, COLS = 64, 128  # World size optimized for wider exploration
BACKGROUND_COLOR = (135, 206, 235)
GRAVITY = 0.5
JUMP_POWER = -10
MAX_FALL_SPEED = 12

# Colors
PLAYER_IDLE_COLOR = (0, 255, 0)  # Green for idle
PLAYER_WALK1_COLOR = (0, 0, 255)  # Blue for walk1
PLAYER_WALK2_COLOR = (255, 0, 0)  # Red for walk2
HEALTH_BAR_COLOR = (255, 0, 0)
INVENTORY_BG = (50, 50, 50)

# Parallax layers
class ParallaxLayer:
    def __init__(self, color, speed, height_range, roughness):
        self.color = color
        self.speed = speed
        self.height_range = height_range
        self.roughness = roughness
        self.points = self.generate_points()
        
    def generate_points(self):
        points = [(0, HEIGHT)]
        x = 0
        while x <= WIDTH * 2:  # Generate double width for seamless scrolling
            y = HEIGHT - random.randint(*self.height_range)
            points.append((x, y))
            x += self.roughness
        points.append((WIDTH * 2, HEIGHT))
        return points

PARALLAX_LAYERS = [
    ParallaxLayer((160, 200, 255), 0.1, (50, 150), 100),   # Farthest mountains
    ParallaxLayer((140, 180, 240), 0.2, (100, 200), 80),   # Far mountains
    ParallaxLayer((120, 160, 220), 0.3, (150, 250), 60),   # Mid mountains
    ParallaxLayer((100, 140, 200), 0.4, (200, 300), 40),   # Near mountains
]

# Block types
BLOCK_TYPES = {
    'dirt': {'color': (139, 69, 19), 'hardness': 1},
    'stone': {'color': (128, 128, 128), 'hardness': 2},
    'iron': {'color': (210, 210, 210), 'hardness': 3},
    'gold': {'color': (255, 215, 0), 'hardness': 3},
    'diamond': {'color': (185, 242, 255), 'hardness': 4},
    'sand': {'color': (194, 178, 128), 'hardness': 1},
    'unbreakable': {'color': (0, 0, 0), 'hardness': float('inf')},  # Unbreakable block
    'wood': {'color': (139, 69, 19)},  # Brown for wood
    'leaves': {'color': (34, 139, 34)}  # Forest Green for leaves
}

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vel_x = 0
        self.vel_y = 0
        self.health = 100
        self.max_health = 100
        self.inventory = defaultdict(int)
        self.selected_slot = 0
        self.on_ground = False
        self.mining_progress = 0
        self.mining_target = None
        self.mining_cooldown = 0
        self.direction = 1
        self.width = TILE_SIZE
        self.height = TILE_SIZE * 2  # 2 tiles tall
        self.current_animation = 'idle'
        self.animation_frame = 0

    def update(self, world):
        # Apply gravity
        self.vel_y = min(self.vel_y + GRAVITY, MAX_FALL_SPEED)
        
        # Update position with collision checks
        new_x = self.x + self.vel_x
        new_y = self.y + self.vel_y
        
        # Horizontal collision
        if not self.check_collision(new_x, self.y, world):
            self.x = new_x
        self.vel_x *= 0.8  # Friction
        
        # Vertical collision
        self.on_ground = False
        if not self.check_collision(self.x, new_y, world):
            self.y = new_y
        else:
            if self.vel_y > 0:
                self.on_ground = True
            self.vel_y = 0

        # Update animation
        if self.vel_x != 0:
            self.current_animation = 'walk'
        else:
            self.current_animation = 'idle'
        self.animation_frame = (self.animation_frame + 1) % 2  # Toggle between 0 and 1 for walk animation

    def check_collision(self, x, y, world):
        # Check all corners of the player
        points = [
            (x, y),  # Top-left
            (x + self.width - 1, y),  # Top-right
            (x, y + self.height - 1),  # Bottom-left
            (x + self.width - 1, y + self.height - 1)  # Bottom-right
        ]
        
        for px, py in points:
            grid_x = int(px // TILE_SIZE)
            grid_y = int(py // TILE_SIZE)
            if 0 <= grid_x < COLS and 0 <= grid_y < ROWS:
                if world[grid_y][grid_x] is not None:
                    return True
        return False

    def mine_block(self, world, pos):
        grid_x, grid_y = pos
        if (0 <= grid_x < COLS and 0 <= grid_y < ROWS and 
            world[grid_y][grid_x] is not None):
            block = world[grid_y][grid_x]
            if block['type'] == 'unbreakable':
                return False  # Can't mine unbreakable blocks
            if self.mining_target != pos:
                self.mining_progress = 0
                self.mining_target = pos
            
            self.mining_progress += 1
            if self.mining_progress >= BLOCK_TYPES[block['type']]['hardness'] * 20:
                world[grid_y][grid_x] = None
                self.inventory[block['type']] += 1
                self.mining_progress = 0
                self.mining_target = None
                return True
        return False

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Mining Adventure")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)
        self.world = self.generate_world()
        self.player = self.create_player()
        self.camera_x = 0
        self.camera_y = 0
        self.time_of_day = 0  # 0 to 100, where 0 is night and 100 is day
        self.background_color = BACKGROUND_COLOR

    def generate_world(self):
        world = [[None for _ in range(COLS)] for _ in range(ROWS)]
        
        # Create base terrain with smoother transitions
        base_heights = [ROWS // 2] * COLS
        
        # Generate terrain with more natural height variations
        for x in range(COLS):
            # Create smoother height variations
            if x > 0:
                base_heights[x] = base_heights[x-1] + random.randint(-2, 2)
                base_heights[x] = max(ROWS // 4, min(base_heights[x], ROWS * 3 // 4))

        # Generate terrain and add trees
        for x in range(COLS):
            height = base_heights[x]
            tree_chance = random.random()
            
            # Generate ground layers
            for y in range(ROWS):
                if y >= height:
                    if y == height:
                        # Surface layer
                        block_type = 'dirt'
                    elif y < height + 5:
                        # Shallow underground
                        block_type = 'dirt'
                    else:
                        # Deep underground
                        rand = random.random()
                        if rand < 0.01 and y < ROWS - 10:
                            block_type = 'diamond'
                        elif rand < 0.03 and y < ROWS - 5:
                            block_type = 'gold'
                        elif rand < 0.08 and y < ROWS - 5:
                            block_type = 'iron'
                        else:
                            block_type = 'stone'
                    
                    # Add tree if on surface and lucky
                    if y == height and tree_chance < 0.2:
                        # Generate tree
                        tree_height = random.randint(3, 6)
                        for tree_y in range(tree_height):
                            if y - tree_y >= 0:
                                world[y - tree_y][x] = {
                                    'type': 'wood',
                                    'texture': self.generate_block_texture('wood')
                                }
                        
                        # Add leaves
                        leaf_sizes = [1, 3, 5, 3, 1]
                        for leaf_y, leaf_width in enumerate(leaf_sizes):
                            leaf_start = max(0, x - leaf_width // 2)
                            leaf_end = min(COLS, x + leaf_width // 2 + 1)
                            for leaf_x in range(leaf_start, leaf_end):
                                if y - tree_height - leaf_y >= 0:
                                    world[y - tree_height - leaf_y][leaf_x] = {
                                        'type': 'leaves',
                                        'texture': self.generate_block_texture('leaves')
                                    }
                    
                    # Only add block if not already occupied by tree
                    if world[y][x] is None:
                        world[y][x] = {
                            'type': block_type,
                            'texture': self.generate_block_texture(block_type)
                        }
        
        # Add unbreakable layer at the bottom
        for x in range(COLS):
            world[ROWS - 1][x] = {'type': 'unbreakable', 'texture': self.generate_block_texture('unbreakable')}
        
        return world

    def generate_block_texture(self, block_type):
        base_color = BLOCK_TYPES[block_type]['color']
        texture = []
        for _ in range(PIXEL_SIZE):
            row = []
            for _ in range(PIXEL_SIZE):
                color = (
                    min(255, max(0, base_color[0] + random.randint(-20, 20))),
                    min(255, max(0, base_color[1] + random.randint(-20, 20))),
                    min(255, max(0, base_color[2] + random.randint(-20, 20)))
                )
                row.append(color)
            texture.append(row)
        return texture

    def create_player(self):
        # Find a suitable spawn point on a surface with a tree
        spawn_locations = []
        for x in range(COLS):
            for y in range(ROWS):
                # Check if this is a surface block with a tree
                if (self.world[y][x] is not None and 
                    self.world[y][x]['type'] == 'dirt' and 
                    y > 0 and 
                    self.world[y-1][x] is not None and 
                    self.world[y-1][x]['type'] == 'wood'):
                    spawn_locations.append((x, y))
        
        # If no tree locations, fall back to ground
        if not spawn_locations:
            mid_x = COLS // 2
            for y in range(ROWS):
                if self.world[y][mid_x] is not None:
                    return Player((mid_x * TILE_SIZE), (y - 2) * TILE_SIZE)
        
        # Choose a random tree-top location
        spawn_x, spawn_y = random.choice(spawn_locations)
        return Player(spawn_x * TILE_SIZE, (spawn_y - 1) * TILE_SIZE)

    def handle_input(self):
        keys = pygame.key.get_pressed()
        
        # Movement
        if keys[pygame.K_LEFT]:
            self.player.vel_x = -6
        elif keys[pygame.K_RIGHT]:
            self.player.vel_x = 6
            
        # Jumping
        if keys[pygame.K_SPACE] and self.player.on_ground:
            self.player.vel_y = JUMP_POWER
            
        # Mining
        if pygame.mouse.get_pressed()[0]:
            mouse_pos = pygame.mouse.get_pos()
            grid_x = int((mouse_pos[0] + self.camera_x) // TILE_SIZE)
            grid_y = int((mouse_pos[1] + self.camera_y) // TILE_SIZE)
            
            # Check mining range
            player_center = (self.player.x + self.player.width // 2,
                           self.player.y + self.player.height // 2)
            block_center = (grid_x * TILE_SIZE + TILE_SIZE // 2,
                          grid_y * TILE_SIZE + TILE_SIZE // 2)
            distance = math.sqrt((player_center[0] - block_center[0])**2 +
                               (player_center[1] - block_center[1])**2)
            
            if distance < TILE_SIZE * 5:
                self.player.mine_block(self.world, (grid_x, grid_y))

    def update_time(self):
        self.time_of_day = (self.time_of_day + 0.1) % 100
        if self.time_of_day < 50:
            self.background_color = (135, 206, 235)  # Day
        else:
            self.background_color = (25, 25, 112)  # Night

    def update_camera(self):
        # Target camera position (center on player)
        target_x = self.player.x - WIDTH // 2 + self.player.width // 2
        target_y = self.player.y - HEIGHT // 2 + self.player.height // 2
        
        # Smooth camera movement
        self.camera_x += (target_x - self.camera_x) * 0.1
        self.camera_y += (target_y - self.camera_y) * 0.1
        
        # Camera bounds
        self.camera_x = max(0, min(self.camera_x, COLS * TILE_SIZE - WIDTH))
        self.camera_y = max(0, min(self.camera_y, ROWS * TILE_SIZE - HEIGHT))

    def draw(self):
        # Draw background
        self.screen.fill(self.background_color)
        
        # Draw parallax backgrounds
        for layer in PARALLAX_LAYERS:
            offset = -(self.camera_x * layer.speed) % WIDTH
            pygame.draw.polygon(self.screen, layer.color, 
                              [(x - offset, y) for x, y in layer.points])
            pygame.draw.polygon(self.screen, layer.color, 
                              [(x - offset + WIDTH, y) for x, y in layer.points])
        
        # Draw world blocks
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
                    
                    # Draw block texture
                    pygame.draw.rect(self.screen, block['texture'][0][0], (screen_x, screen_y, TILE_SIZE, TILE_SIZE))

                    # Draw mining progress
                    if (col, row) == self.player.mining_target:
                        progress = self.player.mining_progress / (BLOCK_TYPES[block['type']]['hardness'] * 20)
                        pygame.draw.rect(
                            self.screen, 
                            (255, 255, 255),
                            (screen_x, screen_y - 5, TILE_SIZE * progress, 3)
                        )

        # Draw player
        player_color = PLAYER_IDLE_COLOR if self.player.current_animation == 'idle' else (PLAYER_WALK1_COLOR if self.player.animation_frame == 0 else PLAYER_WALK2_COLOR)
        pygame.draw.rect(self.screen, player_color, (self.player.x - int(self.camera_x), 
                                                      self.player.y - int(self.camera_y), 
                                                      self.player.width, 
                                                      self.player.height))

        # Draw UI
        self.draw_ui()

    def draw_ui(self):
        # Health bar
        pygame.draw.rect(self.screen, (0, 0, 0), (10, 10, 204, 24))
        pygame.draw.rect(
            self.screen,
            HEALTH_BAR_COLOR,
            (12, 12, 200 * (self.player.health / self.player.max_health), 20)
        )
        
        # Inventory
        for i, (item, count) in enumerate(self.player.inventory.items()):
            pygame.draw.rect(
                self.screen,
                INVENTORY_BG,
                (10 + i * 60, HEIGHT - 60, 50, 50)
            )
            text = self.font.render(f"{item}:{count}", True, (255, 255, 255))
            self.screen.blit(text, (15 + i * 60, HEIGHT - 45))

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_f:
                        pygame.display.toggle_fullscreen()
            
            self.handle_input()
            self.player.update(self.world)
            self.update_time()
            self.update_camera()
            self.draw()
            
            pygame.display.flip()
            self.clock.tick(60)

if __name__ == "__main__":
    try:
        game = Game()
        game.run()  # Start the game
    finally:
        pygame.quit()
