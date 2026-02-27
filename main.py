from src.map import map_checker, map_loader, check_player_position
import pygame
import math
import sys

map_path = None
world_map = None
# take arguments from the command line
if len(sys.argv) != 2:
    sys.exit('Usage: python main.py map_file.map\n')
else:
    map_path = sys.argv[1]
    map_checker(map_path)
    world_map = map_loader(map_path)
    if not world_map:
        sys.exit('The map file is empty')

# window size clc
WIN_WIDTH, WIN_HEIGHT = 800, 600

# every tile size in the map, tile size is 80x80 pixels
TILE_SIZE = 80

# player position must check on wall
player_x, player_y = check_player_position(world_map, TILE_SIZE)

# player angle
player_angle = 0

# player view angle
FOV = math.pi / 3 # 60 degrees

# number of rays
NUM_RAYS = 240

# maximum depth
MAX_DEPTH = 800

# angle between two rays
DELTA_ANGLE = FOV / NUM_RAYS

# distance to projection plane
DISTANCE_PROJ_PLANE = (WIN_WIDTH // 2) / math.tan(FOV / 2)

# wall color (fallback if texture fails)
WALL_COLOR = (0, 255, 0)

# Color palette
SKY_COLOR_TOP = (135, 206, 235)      # Sky blue (top)
SKY_COLOR_BOTTOM = (255, 255, 255)    # White (horizon)
FLOOR_COLOR_TOP = (74, 10, 3)         # Dark red #4A0A03 (near horizon)
FLOOR_COLOR_BOTTOM = (20, 5, 2)       # Even darker red (near player)

# Initialize Pygame
pygame.init()

# Load wall texture
try:
    wall_texture = pygame.image.load('wallimage.jpg')
    wall_texture = pygame.transform.scale(wall_texture, (TILE_SIZE, TILE_SIZE))
    TEXTURE_WIDTH = wall_texture.get_width()
    TEXTURE_HEIGHT = wall_texture.get_height()
    use_texture = True
except:
    print("Warning: Could not load wallimage.jpg, using fallback color")
    use_texture = False
    TEXTURE_WIDTH = TILE_SIZE
    TEXTURE_HEIGHT = TILE_SIZE

# create window
screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))

# create clock
clock = pygame.time.Clock()

# wall check function
def is_wall(x, y):

    # x and y are the coordinates of the point we want to check
    map_x, map_y = int(x / TILE_SIZE), int(y / TILE_SIZE)

    # if the coordinates are within the map boundaries and there is a wall at that coordinate, return True
    if 0 <= map_x < len(world_map[0]) and 0 <= map_y < len(world_map):
        return world_map[map_y][map_x] == 1

    # if the coordinates are outside the map boundaries or there is no wall at that coordinate, return False
    return False

def lerp_color(color1, color2, t):
    """Linearly interpolate between two colors."""
    return (
        int(color1[0] + (color2[0] - color1[0]) * t),
        int(color1[1] + (color2[1] - color1[1]) * t),
        int(color1[2] + (color2[2] - color1[2]) * t)
    )

def draw_background(screen):
    """Draw sky and floor with gradient effects."""
    horizon_y = WIN_HEIGHT // 2
    
    # Draw sky gradient (top to horizon)
    for y in range(horizon_y):
        t = y / horizon_y  # 0 at top, 1 at horizon
        color = lerp_color(SKY_COLOR_TOP, SKY_COLOR_BOTTOM, t)
        pygame.draw.line(screen, color, (0, y), (WIN_WIDTH, y))
    
    # Draw floor gradient (horizon to bottom)
    for y in range(horizon_y, WIN_HEIGHT):
        t = (y - horizon_y) / (WIN_HEIGHT - horizon_y)  # 0 at horizon, 1 at bottom
        color = lerp_color(FLOOR_COLOR_TOP, FLOOR_COLOR_BOTTOM, t)
        pygame.draw.line(screen, color, (0, y), (WIN_WIDTH, y))

def raycasting(screen):
    # Define step size for higher precision ray casting
    STEP_SIZE = 0.5
    
    # a loop for each ray
    for ray in range(NUM_RAYS):
        # calculate the ray angle
        ray_angle = player_angle - FOV / 2 + ray * DELTA_ANGLE
        
        # Calculate ray direction
        ray_cos = math.cos(ray_angle)
        ray_sin = math.sin(ray_angle)
        
        # for each depth
        for depth in range(int(MAX_DEPTH / STEP_SIZE)):
            # calculate the target coordinates with smaller step size
            current_depth = depth * STEP_SIZE
            target_x = player_x + current_depth * ray_cos
            target_y = player_y + current_depth * ray_sin
            
            # if the target point is a wall
            if is_wall(target_x, target_y):
                # Backtrack to find the exact wall surface (just before entering the wall)
                # Move back by STEP_SIZE to find the point just outside the wall
                prev_depth = max(0, current_depth - STEP_SIZE)
                surface_x = player_x + prev_depth * ray_cos
                surface_y = player_y + prev_depth * ray_sin
                
                # Use the surface point for texture calculation
                # Get the tile coordinates of the wall we hit (using surface point)
                tile_x = int(surface_x / TILE_SIZE)
                tile_y = int(surface_y / TILE_SIZE)
                
                # Get position within the tile (using the surface point)
                local_x = surface_x - (tile_x * TILE_SIZE)
                local_y = surface_y - (tile_y * TILE_SIZE)
                
                # Determine which wall face was hit by checking which boundary is closest
                dist_to_left = local_x
                dist_to_right = TILE_SIZE - local_x
                dist_to_top = local_y
                dist_to_bottom = TILE_SIZE - local_y
                
                # Find the minimum distance to determine which face was hit
                min_dist = min(dist_to_left, dist_to_right, dist_to_top, dist_to_bottom)
                
                # Calculate the exact intersection point on the wall surface
                # Move from surface point to the wall boundary
                if min_dist == dist_to_left:
                    # Hit left face of wall
                    hit_offset = surface_y % TILE_SIZE
                elif min_dist == dist_to_right:
                    # Hit right face of wall
                    hit_offset = surface_y % TILE_SIZE
                elif min_dist == dist_to_top:
                    # Hit top face of wall
                    hit_offset = surface_x % TILE_SIZE
                else:  # dist_to_bottom
                    # Hit bottom face of wall
                    hit_offset = surface_x % TILE_SIZE
                
                # Use actual depth for distance calculations
                actual_depth = current_depth
                
                # Correct distance for fish-eye effect
                corrected_depth = actual_depth * math.cos(player_angle - ray_angle)
                
                # Calculate wall height
                wall_height = TILE_SIZE * WIN_HEIGHT / max(corrected_depth, 0.001)
                
                # Calculate wall top and bottom positions (theoretical, before clipping)
                wall_top_raw = WIN_HEIGHT // 2 - wall_height // 2
                wall_bottom_raw = WIN_HEIGHT // 2 + wall_height // 2
                
                # Calculate clipped wall positions (what's actually visible on screen)
                wall_top = max(0, wall_top_raw)
                wall_bottom = min(WIN_HEIGHT, wall_bottom_raw)
                visible_wall_height = wall_bottom - wall_top
                
                # Map offset to texture coordinate
                texture_x = int((hit_offset / TILE_SIZE) * TEXTURE_WIDTH)
                texture_x = max(0, min(TEXTURE_WIDTH - 1, texture_x))
                
                # Calculate fog/darkness based on distance
                fog_factor = min(1, actual_depth / MAX_DEPTH)
                
                # Draw the wall column with texture
                column_width = WIN_WIDTH / NUM_RAYS
                x_pos = ray * column_width
                
                if use_texture:
                    # Calculate how much of the wall is clipped at top and bottom
                    clip_top = max(0, -wall_top_raw)  # Amount clipped from top
                    clip_bottom = max(0, wall_bottom_raw - WIN_HEIGHT)  # Amount clipped from bottom
                    
                    # Calculate the visible portion of the texture
                    # The texture should be mapped to the full wall height
                    # We need to extract only the visible portion
                    texture_start_y = int((clip_top / wall_height) * TEXTURE_HEIGHT)
                    texture_end_y = int(((wall_height - clip_bottom) / wall_height) * TEXTURE_HEIGHT)
                    
                    # Ensure valid texture coordinates
                    texture_start_y = max(0, min(TEXTURE_HEIGHT - 1, texture_start_y))
                    texture_end_y = max(texture_start_y + 1, min(TEXTURE_HEIGHT, texture_end_y))
                    texture_slice_height = texture_end_y - texture_start_y
                    
                    # Get only the visible portion of the texture column
                    texture_column = pygame.Surface((1, texture_slice_height))
                    texture_column.blit(wall_texture, (0, 0), (texture_x, texture_start_y, 1, texture_slice_height))
                    
                    # Scale the texture slice to the visible wall height
                    scaled_column = pygame.transform.scale(texture_column, (int(column_width) + 1, int(visible_wall_height)))
                    
                    # Apply fog/darkness overlay
                    fog_overlay = pygame.Surface((int(column_width) + 1, int(visible_wall_height)), pygame.SRCALPHA)
                    darkness = int(255 * fog_factor * 0.85)  # 0.85 controls max darkness
                    fog_overlay.fill((0, 0, 0, darkness))
                    
                    # Draw wall column at the clipped position
                    screen.blit(scaled_column, (x_pos, wall_top))
                    
                    # Apply fog overlay
                    screen.blit(fog_overlay, (x_pos, wall_top))
                else:
                    # Fallback to colored lines
                    color_intensity = 1 - fog_factor
                    color = (WALL_COLOR[0] * color_intensity, WALL_COLOR[1] * color_intensity, WALL_COLOR[2] * color_intensity)
                    pygame.draw.line(screen, color,
                        (x_pos, wall_top),
                        (x_pos, wall_bottom), int(column_width) + 1)
                
                break

# movement function
def movement():
    global player_x, player_y, player_angle
    keys = pygame.key.get_pressed()

    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        # rotate the player to the left
        player_angle -= 0.05

    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        player_angle += 0.05

    # Handle forward/backward movement with sliding collision
    move_speed = 5
    move_x = 0
    move_y = 0
    
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        # Moving forward
        move_x = move_speed * math.cos(player_angle)
        move_y = move_speed * math.sin(player_angle)
    elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
        # Moving backward
        move_x = -move_speed * math.cos(player_angle)
        move_y = -move_speed * math.sin(player_angle)
    
    # Apply sliding movement if there's any movement input
    if move_x != 0 or move_y != 0:
        player_x, player_y = slide_move(player_x, player_y, move_x, move_y)

    if keys[pygame.K_ESCAPE]:
        pygame.quit()
        sys.exit(0)

def slide_move(x, y, move_x, move_y):
    """
    Attempt to move the player with sliding collision.
    If full movement causes collision, try sliding along walls.
    """
    # Try full movement first
    new_x = x + move_x
    new_y = y + move_y
    
    if not is_wall(new_x, new_y):
        # Full movement is possible, no collision
        return new_x, new_y
    
    # Collision detected - try sliding
    # Try moving only in X direction (horizontal slide)
    if move_x != 0 and not is_wall(x + move_x, y):
        return x + move_x, y
    
    # Try moving only in Y direction (vertical slide)
    if move_y != 0 and not is_wall(x, y + move_y):
        return x, y + move_y
    
    # Both directions blocked, can't move
    return x, y

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    draw_background(screen)
    movement()
    raycasting(screen)
    pygame.display.flip()
    clock.tick(30)

pygame.quit()

if __name__ == "__main__":
    pass
