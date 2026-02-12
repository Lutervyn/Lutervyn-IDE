from PIL import Image
import os

def png_to_svg_simple(png_path, svg_path):
    """Convert PNG to simple SVG using PIL"""
    img = Image.open(png_path).convert('RGBA')
    img = img.resize((64, 64), Image.Resampling.LANCZOS)
    
    # Get pixel data
    pixels = img.load()
    width, height = img.size
    
    # Create SVG with rectangles for each black pixel
    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
<g id="logo">
'''
    
    # Add a rectangle for each non-transparent pixel
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a > 128:  # If pixel is visible
                # Convert to hex color
                color = f'#{r:02x}{g:02x}{b:02x}'
                svg_content += f'  <rect x="{x}" y="{y}" width="1" height="1" fill="{color}"/>\n'
    
    svg_content += '''</g>
</svg>'''
    
    with open(svg_path, 'w') as f:
        f.write(svg_content)
    
    print(f"Created SVG: {svg_path}")
    print("\nNEXT STEPS:")
    print("1. Go to https://icomoon.io/app/")
    print("2. Click 'Import Icons' and upload the SVG")
    print("3. Select the icon and click 'Generate Font'")
    print("4. In preferences, set the font name to 'icons'")
    print("5. Map the icon to character '5' (Unicode U+0035)")
    print("6. Download the font and extract icons.ttf")
    print("7. Replace data/fonts/icons.ttf with the new file")

if __name__ == "__main__":
    src = r"C:\Users\KING\.gemini\antigravity\brain\2d19dad9-e9ff-4a7f-be58-2566c58c2311\lutervyn_ide_icon_bw_v3_1769777985219.png"
    svg = r"f:\Luohino\Lutervyn\Lutervyn-IDE\lite-xl-source\logo_for_font.svg"
    
    png_to_svg_simple(src, svg)
