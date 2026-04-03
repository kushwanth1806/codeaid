#!/usr/bin/env python3
"""
Generate the CodeAid professional logo as PNG.
Based on the CodeAid brand identity.
"""

from PIL import Image, ImageDraw
import os

# Create directories if needed
os.makedirs('static', exist_ok=True)

# Create a high-quality logo image (300x300px at 72 DPI)
logo_size = 300
img = Image.new('RGBA', (logo_size, logo_size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Define colors
cyan = (23, 210, 255)  # #17d9ff
dark_blue = (15, 52, 96)  # #0f3460
red = (233, 69, 96)  # #e94560
gray = (100, 120, 140)
white = (255, 255, 255)

# Background circle (subtle)
draw.ellipse([10, 10, 290, 290], outline=cyan, width=2)

# Draw geometric nodes (hexagon pattern)
center_x, center_y = logo_size // 2, logo_size // 2
radius = 80

# Calculate positions for 6 nodes
import math
node_radius = 15
positions = []
for i in range(6):
    angle = (i * 60 - 90) * math.pi / 180
    x = center_x + radius * math.cos(angle)
    y = center_y + radius * math.sin(angle)
    positions.append((x, y))

# Colors alternating between cyan and red
colors = [cyan, red, cyan, red, cyan, red]

# Draw connecting lines
for i in range(len(positions)):
    x1, y1 = positions[i]
    x2, y2 = positions[(i + 1) % len(positions)]
    draw.line([(x1, y1), (x2, y2)], fill=cyan if i % 2 == 0 else red, width=3)
    # Lines to center
    draw.line([(x1, y1), (center_x, center_y)], fill=red if i % 2 == 0 else cyan, width=2)

# Draw nodes
for i, (x, y) in enumerate(positions):
    color = colors[i]
    # Node circle
    draw.ellipse(
        [x - node_radius, y - node_radius, x + node_radius, y + node_radius],
        fill=color,
        outline=white,
        width=2
    )

# Draw center node (larger)
center_node_radius = 20
draw.ellipse(
    [center_x - center_node_radius, center_y - center_node_radius,
     center_x + center_node_radius, center_y + center_node_radius],
    fill=cyan,
    outline=white,
    width=2
)

# Draw plus sign in center (repair/fix symbol)
plus_size = 8
draw.rectangle(
    [center_x - 2, center_y - plus_size, center_x + 2, center_y + plus_size],
    fill=dark_blue
)
draw.rectangle(
    [center_x - plus_size, center_y - 2, center_x + plus_size, center_y + 2],
    fill=dark_blue
)

# Save the logo
logo_path = 'static/logo.png'
img.save(logo_path, 'PNG', quality=95)
print(f"✅ Logo created: {logo_path}")
print(f"📊 Size: {os.path.getsize(logo_path)} bytes")

# Create a larger version for documentation
logo_lg_size = 512
img_lg = img.resize((logo_lg_size, logo_lg_size), Image.Resampling.LANCZOS)
logo_lg_path = 'static/logo-large.png'
img_lg.save(logo_lg_path, 'PNG', quality=95)
print(f"✅ Large logo created: {logo_lg_path}")
