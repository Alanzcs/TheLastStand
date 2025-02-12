import pygame
import random
import sys
import os
import math
from PIL import Image  

pygame.init()

# SCREEN SETUP
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("The Last Stand")
clock = pygame.time.Clock()

# COLORS
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
ORANGE = (255, 165, 0)

IMAGE_DIR = "images"  
GIF_DIR = "gifs"  

# LOAD IMAGES
try:
    background_image = pygame.image.load(os.path.join(IMAGE_DIR, 'background.png'))
    player_image = pygame.image.load(os.path.join(IMAGE_DIR, 'player_image.png'))
    zombie_shooter_image = pygame.image.load(os.path.join(IMAGE_DIR, 'zombie_shooter.png'))
    barrel_image = pygame.image.load(os.path.join(IMAGE_DIR, 'image_barrel.png'))
    medkit_image = pygame.image.load(os.path.join(IMAGE_DIR, 'medkit.png'))
    boss_image = pygame.image.load(os.path.join(IMAGE_DIR, 'boss.png')) 
except pygame.error as message:
    print("Cannot load image:")
    raise SystemExit(message)

background_image = pygame.transform.scale(background_image, (WIDTH, HEIGHT))
player_image = pygame.transform.scale(player_image, (80, 80))
zombie_shooter_image = pygame.transform.scale(zombie_shooter_image, (80, 80))
barrel_image = pygame.transform.scale(barrel_image, (50, 50))
medkit_image = pygame.transform.scale(medkit_image, (30, 30))
boss_image = pygame.transform.scale(boss_image, (100, 100)) 

# PLAYER
PLAYER_SIZE = 80
PLAYER_SPEED = 5
player = pygame.Rect(WIDTH // 2, HEIGHT // 2, PLAYER_SIZE, PLAYER_SIZE)
player_health = 100
player_max_health = 100 
player_score = 0
player_direction = [0, -1] 
player_facing_right = True  

# WEAPON
BULLET_SPEED = 10
BULLET_SIZE = 5
FIRE_RATE = 250 
last_shot_time = 0
bullets = []

# ZOMBIE
ZOMBIE_SPAWN_RATE = 1500 
last_zombie_spawn = 0
zombies = []

def load_gif_frames(gif_path, size):
    frames = []
    try:
        img = Image.open(gif_path)
        for i in range(img.n_frames):
            img.seek(i)
            frame = img.copy()
            if frame.mode != 'RGBA':
                frame = frame.convert('RGBA')  
            frame_surface = pygame.image.fromstring(frame.tobytes(), frame.size, frame.mode)
            frames.append(pygame.transform.scale(frame_surface, (size, size))) 
    except FileNotFoundError:
        print(f"Error: GIF file not found at {gif_path}")
        return None
    except Exception as e:
        print(f"Error loading GIF: {e}")
        return None
    return frames

zombie_basic_frames = load_gif_frames(os.path.join(GIF_DIR, 'zombie_gif.gif'), 80) 
zombie_fast_frames = load_gif_frames(os.path.join(GIF_DIR, 'fast_zombie_gif.gif'), 40)
zombie_tank_frames = load_gif_frames(os.path.join(GIF_DIR, 'tank_zombie_gif.gif'), 80)

if zombie_basic_frames is None:
    zombie_basic_frames = [pygame.Surface((80,80), pygame.SRCALPHA)] 

if zombie_fast_frames is None:
    zombie_fast_frames = [pygame.Surface((80,80), pygame.SRCALPHA)]

if zombie_tank_frames is None:
    zombie_tank_frames = [pygame.Surface((80,80), pygame.SRCALPHA)]

ZOMBIE_TYPES = {
    'basic': {'speed': 1.5, 'health': 1, 'damage': 10, 'points': 10, 'frames': zombie_basic_frames, 'facing_right': True},
    'fast': {'speed': 3, 'health': 1, 'damage': 20, 'points': 15, 'frames': zombie_fast_frames, 'facing_right': False},
    'tank': {'speed': 1, 'health': 3, 'damage': 30, 'points': 30, 'frames': zombie_tank_frames, 'facing_right': True},
    'shooter': {'speed': 1, 'health': 2, 'damage': 15, 'points': 25, 'shoot_cooldown': 2000, 'image': zombie_shooter_image, 'facing_right': True}
}

enemy_bullets = []
ENEMY_BULLET_SPEED = 3

# MEDKIT
medkit = None
last_medkit_spawn = 0
MEDKIT_SPAWN_INTERVAL = 10000  
MEDKIT_LIFETIME = 5000  

# BARREL
barrel = None  
last_barrel_spawn = 0
BARREL_SPAWN_INTERVAL = 7000  
BARREL_LIFETIME = 4000  

current_level = 1
LEVEL_SCORE = 100 
level_start_time = 0
LEVEL_DISPLAY_DURATION = 2000 

font = pygame.font.Font(None, 36)

class Zombie:
    def __init__(self, rect, zombie_type):
        self.rect = rect
        self.type = zombie_type
        self.health = ZOMBIE_TYPES[zombie_type]['health']
        self.speed = ZOMBIE_TYPES[zombie_type]['speed']
        self.damage = ZOMBIE_TYPES[zombie_type]['damage']
        self.last_shot = 0
        self.frames = None
        self.image = None
        self.facing_right = ZOMBIE_TYPES[zombie_type]['facing_right']

        if 'frames' in ZOMBIE_TYPES[zombie_type]:
            self.frames = ZOMBIE_TYPES[zombie_type]['frames']
            self.image_index = 0
            self.image = self.frames[self.image_index]
        elif 'image' in ZOMBIE_TYPES[zombie_type]:
            self.image = ZOMBIE_TYPES[zombie_type]['image']
            self.frames = None 

        self.animation_speed = 5  
        self.animation_timer = 0

    def update_animation(self):
        if self.frames:
            self.animation_timer += 1
            if self.animation_timer >= self.animation_speed:
                self.animation_timer = 0
                self.image_index = (self.image_index + 1) % len(self.frames)
                self.image = self.frames[self.image_index]

    def update(self, player):
        dx = player.x - self.rect.x
        if dx < 0 and self.facing_right:
            self.facing_right = False
        if dx > 0 and not self.facing_right:
            self.facing_right = True

        dy = player.y - self.rect.y
        distance = (dx ** 2 + dy ** 2) ** 0.5
        if distance > 0:
            self.rect.x += (dx / distance) * self.speed
            self.rect.y += (dy / distance) * self.speed

class Boss:
    def __init__(self, level):
        self.rect = boss_image.get_rect(center=(WIDTH // 2, 150))
        self.health = 50 + (level // 5) * 20  
        self.max_health = self.health 
        self.level = level
        self.shoot_cooldown = 2000 - (level // 5) * 200  
        self.bomb_cooldown = 5000  
        self.laser_cooldown = 3000 - (level // 5) * 200
        self.laser_duration = 1200
        self.laser_warning_duration = 300  
        self.is_laser_active = False
        self.is_laser_warning = False
        self.attack_pattern = ['shoot', 'laser', 'bomb', 'laser']
        self.attack_interval = 2200
        self.last_attack_time = 0  
        self.bomb_damage = 7  
        self.bullet_damage = 5  
        self.last_shot = 0
        self.last_bomb = 0
        self.last_laser = 0
        self.laser_angle = 0  
        self.bullet_speed = 2  
        self.bomb_speed = 3 
        self.laser_colliding = False

    def shoot(self):
        bullet = pygame.Rect(self.rect.centerx, self.rect.bottom, 10, 10)
        dx = player.x - self.rect.centerx
        dy = player.y - self.rect.bottom
        angle = math.atan2(dy, dx)  
        speed = self.bullet_speed
        direction = (speed * math.cos(angle), speed * math.sin(angle)) 
        enemy_bullets.append((bullet, direction, 'bullet'))  

    def throw_bomb(self):
        bomb = pygame.Rect(self.rect.centerx, self.rect.bottom, 20, 20)
        dx = player.x - self.rect.centerx
        dy = player.y - self.rect.bottom
        angle = math.atan2(dy, dx)  
        speed = self.bomb_speed
        direction = (speed * math.cos(angle), speed * math.sin(angle)) 
        enemy_bullets.append((bomb, direction, 'bomb'))  

    def activate_laser(self):
        self.is_laser_active = True
        self.is_laser_warning = True
        self.laser_start_time = pygame.time.get_ticks()
        self.laser_angle = math.atan2(player.y - self.rect.centery, player.x - self.rect.centerx)

    def perform_attack(self):
        current_time = pygame.time.get_ticks()

        if current_time - self.last_attack_time > self.attack_interval:
            attack_type = random.choice(self.attack_pattern)

            if attack_type == 'shoot' and current_time - self.last_shot > self.shoot_cooldown:
                self.shoot()
                self.last_shot = current_time
            elif attack_type == 'bomb' and current_time - self.last_bomb > self.bomb_cooldown:
                self.throw_bomb()
                self.last_bomb = current_time
            elif attack_type == 'laser' and current_time - self.last_laser > self.laser_cooldown:
                self.activate_laser()
                self.last_laser = current_time

            self.last_attack_time = current_time

def draw_laser(boss):
    laser_end_x = boss.rect.centerx + 500 * math.cos(boss.laser_angle)
    laser_end_y = boss.rect.centery + 500 * math.sin(boss.laser_angle)

    current_time = pygame.time.get_ticks()
    if boss.is_laser_warning:
        laser_color = ORANGE  
    else:
        laser_color = RED  

    pygame.draw.line(screen, laser_color, boss.rect.center, (laser_end_x, laser_end_y), 5)

def draw_player():
    if player_facing_right:
        screen.blit(player_image, player.topleft)
    else:
        screen.blit(pygame.transform.flip(player_image, True, False), player.topleft)

def draw_zombies():
    for zombie in zombies:
        image_to_draw = zombie.image
        if not zombie.facing_right and zombie.frames:
            image_to_draw = pygame.transform.flip(zombie.image, True, False)
        screen.blit(image_to_draw, zombie.rect.topleft)

def draw_bullets():
    for bullet, direction in bullets:
        pygame.draw.circle(screen, YELLOW, (int(bullet.x + bullet.width // 2), int(bullet.y + bullet.height // 2)), BULLET_SIZE)

def draw_enemy_bullets():
    for bullet, direction, attack_type in enemy_bullets:
        pygame.draw.circle(screen, RED, (int(bullet.x + bullet.width // 2), int(bullet.y + bullet.height // 2)), 5)

def draw_ui():
    health_text = font.render(f"Health: {player_health}/{player_max_health}", True, WHITE) 
    score_text = font.render(f"Score: {player_score}", True, WHITE)
    level_text = font.render(f"Level: {current_level}", True, WHITE)
    screen.blit(health_text, (10, 10))
    screen.blit(score_text, (10, 40))
    screen.blit(level_text, (WIDTH - 150, 10))
    if boss:
        boss_health_text = font.render(f"Boss Health: {boss.health}/{boss.max_health}", True, WHITE)
        screen.blit(boss_health_text, (WIDTH // 2 - 100, 10))  

def move_enemy_bullets():
    for i, (bullet, direction, attack_type) in enumerate(enemy_bullets):
        bullet.x += direction[0]
        bullet.y += direction[1]
        if bullet.x < 0 or bullet.x > WIDTH or bullet.y < 0 or bullet.y > HEIGHT:
            enemy_bullets.pop(i)

def move_zombies():
    for zombie in zombies:
        zombie.update(player)

        if zombie.type == 'shooter':
            current_time = pygame.time.get_ticks()
            shoot_cooldown = ZOMBIE_TYPES['shooter']['shoot_cooldown']
            if current_time - zombie.last_shot > shoot_cooldown:
                dx = player.x - zombie.rect.centerx
                dy = player.y - zombie.rect.centery
                distance = max(1, (dx ** 2 + dy ** 2) ** 0.5)
                direction = (dx / distance, dy / distance)
                bullet = pygame.Rect(zombie.rect.centerx, zombie.rect.centery, 5, 5)
                enemy_bullets.append((bullet, direction, 'shooter'))
                zombie.last_shot = current_time

def spawn_zombie():
    side = random.choice(["top", "bottom", "left", "right"])
    if side == "top":
        x, y = random.randint(0, WIDTH - PLAYER_SIZE), -PLAYER_SIZE
    elif side == "bottom":
        x, y = random.randint(0, WIDTH - PLAYER_SIZE), HEIGHT
    elif side == "left":
        x, y = -PLAYER_SIZE, random.randint(0, HEIGHT - PLAYER_SIZE)
    else:
        x, y = WIDTH, random.randint(0, HEIGHT - PLAYER_SIZE)

    possible_types = ['basic']
    if current_level >= 2:
        possible_types.append('fast')
    if current_level >= 3:
        possible_types.append('tank')
    if current_level >= 4:
        possible_types.append('shooter')

    zombie_type = random.choice(possible_types)
    new_zombie = Zombie(pygame.Rect(x, y, PLAYER_SIZE, PLAYER_SIZE), zombie_type)  
    zombies.append(new_zombie)

def draw_barrel():
    if barrel:
        screen.blit(barrel_image, barrel.topleft)

def spawn_barrel():
    global barrel, last_barrel_spawn
    current_time = pygame.time.get_ticks()
    if not barrel and current_time - last_barrel_spawn > BARREL_SPAWN_INTERVAL:
        barrel = pygame.Rect(random.randint(50, WIDTH - 100), random.randint(50, HEIGHT - 100), 50, 50)
        last_barrel_spawn = current_time

def update_barrel():
    global barrel
    if barrel and pygame.time.get_ticks() - last_barrel_spawn > BARREL_LIFETIME:
        barrel = None

def restart_screen():
    screen.fill(BLACK)
    restart_text = font.render("Press R to Restart or Q to Quit", True, WHITE)
    final_score_text = font.render(f"Final Score: {player_score}", True, WHITE)
    died_text = font.render("YOU DIED!", True, RED)

    restart_rect = restart_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
    final_score_rect = final_score_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    died_rect = died_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
    screen.blit(restart_text, restart_rect)
    screen.blit(final_score_text, final_score_rect)
    screen.blit(died_text, died_rect)

    pygame.display.flip()

def reset_game():
    global player_health, player_score, player_direction, bullets, zombies, enemy_bullets, current_level, level_start_time, player_max_health
    global barrel, last_barrel_spawn, zombie_spawn_rate, boss

    player_health = 100
    player_max_health = 100
    player_score = 0
    player_direction = [0, -1]
    bullets.clear()
    zombies.clear()
    enemy_bullets.clear()
    player.center = (WIDTH // 2, HEIGHT // 2)
    current_level = 1
    level_start_time = pygame.time.get_ticks()
    barrel = None
    last_barrel_spawn = 0
    zombie_spawn_rate = 1500
    boss = None
    show_level_screen()

def spawn_medkit():
    global medkit, last_medkit_spawn
    current_time = pygame.time.get_ticks()
    if not medkit and current_time - last_medkit_spawn > MEDKIT_SPAWN_INTERVAL:
        if random.random() < 0.2:
            medkit = pygame.Rect(random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 50), 30, 30)
            last_medkit_spawn = current_time

def check_medkit():
    global medkit, player_health
    if medkit and player.colliderect(medkit):
        player_health = min(player_max_health, player_health + 30)
        medkit = None

def check_level_up():
    global current_level, zombie_spawn_rate, level_start_time, zombies, enemy_bullets, boss, player_health, player_max_health, LEVEL_SCORE
    if player_score >= current_level * (LEVEL_SCORE + (current_level - 1) * 20):
        current_level += 1
        player_max_health += 10
        player_health = player_max_health

        zombies.clear()
        enemy_bullets.clear()

        zombie_spawn_rate = max(500, ZOMBIE_SPAWN_RATE - 100)
        level_start_time = pygame.time.get_ticks()
        show_level_screen()

        if current_level % 5 == 0:
            start_boss_fight()

def show_level_screen():
    level_text = font.render(f"LEVEL {current_level}", True, WHITE)
    level_rect = level_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.fill(BLACK)
    screen.blit(level_text, level_rect)
    pygame.display.flip()
    pygame.time.delay(LEVEL_DISPLAY_DURATION)

def update_enemy_bullets():
    global enemy_bullets, player_health
    bullets_to_keep = []
    for bullet_data in enemy_bullets:
        bullet, direction, attack_type = bullet_data
        bullet.x += direction[0]
        bullet.y += direction[1]
        
        if not screen.get_rect().colliderect(bullet):
            continue
        
        if player.colliderect(bullet):
            if attack_type == 'bomb' and boss is not None:
                player_health -= boss.bomb_damage
            elif attack_type == 'bullet' and boss is not None:
                player_health -= boss.bullet_damage
            elif attack_type == 'shooter':
                player_health -= ZOMBIE_TYPES['shooter']['damage']
            player_health = max(player_health, 0)
            continue
        
        bullets_to_keep.append(bullet_data)
    
    enemy_bullets = bullets_to_keep

def start_boss_fight():
    global boss, zombies, enemy_bullets
    zombies.clear()
    enemy_bullets.clear()
    boss = Boss(current_level)

def draw_boss():
    if boss:
        screen.blit(boss_image, boss.rect.topleft)

# MAIN
running = True
game_over = False
boss = None  

player_max_health = 100 + (current_level - 1) * 10
player_health = player_max_health

# IF YOU WANT TO START THE GAME WITH A BOSS FIGHT, UNCOMMENT THE TWO LINES BELOW AND SET current_level TO 5

current_level = 1
show_level_screen() 
#start_boss_fight()
#boss.last_attack_time = pygame.time.get_ticks()

while running:
    screen.fill(BLACK)
    screen.blit(background_image, (0, 0))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if game_over:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:  
                    reset_game()
                    game_over = False
                if event.key == pygame.K_q:  
                    running = False

    if not game_over:
        if pygame.time.get_ticks() - level_start_time < LEVEL_DISPLAY_DURATION:
            continue

        check_level_up()
        spawn_medkit()
        check_medkit()
        spawn_barrel()
        update_barrel()
        update_enemy_bullets()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_w] and player.top > 0:
            player.y -= PLAYER_SPEED
            player_direction = [0, -1]
        if keys[pygame.K_s] and player.bottom < HEIGHT:
            player.y += PLAYER_SPEED
            player_direction = [0, 1]
        if keys[pygame.K_a] and player.left > 0:
            player.x -= PLAYER_SPEED
            player_direction = [-1, 0]
            player_facing_right = False
        if keys[pygame.K_d] and player.right < WIDTH:
            player.x += PLAYER_SPEED
            player_direction = [1, 0]
            player_facing_right = True
        if keys[pygame.K_SPACE]:
            current_time = pygame.time.get_ticks()
            if current_time - last_shot_time > FIRE_RATE:
                last_shot_time = current_time
                bullet = pygame.Rect(player.centerx - BULLET_SIZE, player.centery - BULLET_SIZE,
                                     BULLET_SIZE * 2, BULLET_SIZE * 2)
                bullets.append((bullet, player_direction.copy()))

        for bullet, direction in bullets[:]:
            bullet.x += direction[0] * BULLET_SPEED
            bullet.y += direction[1] * BULLET_SPEED
            if bullet.bottom < 0 or bullet.top > HEIGHT or bullet.right < 0 or bullet.left > WIDTH:
                bullets.remove((bullet, direction))

        move_zombies()

        for zombie in zombies[:]:
            for bullet, direction in bullets[:]:
                if zombie.rect.colliderect(bullet):
                    player_score += ZOMBIE_TYPES[zombie.type]['points']
                    zombies.remove(zombie)
                    bullets.remove((bullet, direction))
                    break

        for zombie in zombies[:]:
            if player.colliderect(zombie.rect):
                player_health -= zombie.damage
                player_health = min(player_health, player_max_health)
                zombies.remove(zombie)

        current_time = pygame.time.get_ticks()
        if current_time - last_zombie_spawn > ZOMBIE_SPAWN_RATE and boss is None:
            last_zombie_spawn = current_time
            spawn_zombie()

        if barrel and player.colliderect(barrel):
            player_health -= 30
            barrel = None 
            player_health = max(player_health, 0) 
            if player_health <= 0:
                game_over = True

        if boss:
            boss.perform_attack()
            boss_current_time = pygame.time.get_ticks()

            if boss.is_laser_active:
                if boss.is_laser_warning:
                    if boss_current_time - boss.laser_start_time > boss.laser_warning_duration:
                        boss.is_laser_warning = False
                else:
                    if boss_current_time - boss.laser_start_time > boss.laser_duration:
                        boss.is_laser_active = False

            if boss.is_laser_active and not boss.is_laser_warning:
                laser_end_x = boss.rect.centerx + 500 * math.cos(boss.laser_angle)
                laser_end_y = boss.rect.centery + 500 * math.sin(boss.laser_angle)
                
                if player.clipline(boss.rect.center, (laser_end_x, laser_end_y)):
                    if not boss.laser_colliding:
                        player_health -= 5
                        boss.laser_colliding = True
                    else:
                        player_health -= 2
                else:
                    boss.laser_colliding = False
                
                player_health = max(player_health, 0)
                if player_health <= 0:
                    game_over = True

            for bullet, direction in bullets[:]:
                if boss.rect.colliderect(bullet):
                    boss.health -= 1
                    bullets.remove((bullet, direction))
                    if boss.health <= 0:
                        player_score += 500
                        boss = None
                        current_level += 1
                        player_max_health += 10
                        player_health = player_max_health
                        level_start_time = pygame.time.get_ticks()
                        show_level_screen()
                        zombies.clear()
                        enemy_bullets.clear()
                        last_zombie_spawn = pygame.time.get_ticks()
                        break

        if player_health <= 0:
            game_over = True

        for zombie in zombies:
            zombie.update_animation()

        draw_player()
        draw_zombies()
        draw_bullets()
        draw_enemy_bullets()
        draw_ui()
        draw_barrel()

        if medkit:
            screen.blit(medkit_image, medkit.topleft)

        if boss:
            draw_boss()
            draw_laser(boss)
    else:
        restart_screen()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()