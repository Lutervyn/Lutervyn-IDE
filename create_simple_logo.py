from PIL import Image, ImageDraw
import os

def create_simple_logo_svg(png_path, svg_path):
    """Create a simplified single-path SVG from the logo"""
    img = Image.open(png_path).convert('L')  # Grayscale
    img = img.resize((32, 32), Image.Resampling.LANCZOS)  # Smaller = simpler
    
    # Threshold to pure black and white
    threshold = 128
    img = img.point(lambda p: 255 if p > threshold else 0)
    
    # Create a simple SVG with a single path
    # For now, just create a placeholder "L<>" text-based logo
    svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <g id="logo">
    <!-- L shape -->
    <rect x="20" y="20" width="10" height="60" fill="#000"/>
    <rect x="20" y="70" width="30" height="10" fill="#000"/>
    
    <!-- < symbol -->
    <polygon points="60,35 55,50 60,65" fill="#000"/>
    
    <!-- > symbol -->
    <polygon points="70,35 75,50 70,65" fill="#000"/>
  </g>
</svg>'''
    
    with open(svg_path, 'w') as f:
        f.write(svg_content)
    
    print(f"Created simplified SVG: {svg_path}")
    print("\nThis is a SIMPLE placeholder logo (L<>)")
    print("Go back to IcoMoon and:")
    print("1. Remove the old icon")
    print("2. Import this new simplified SVG")
    print("3. Set character code to: 35 (for '5')")
    print("4. Download and test again")

if __name__ == "__main__":
    src = r"C:\Users\KING\.gemini\antigravity\brain\2d19dad9-e9ff-4a7f-be58-2566c58c2311\lutervyn_ide_icon_bw_v3_1769777985219.png"
    svg = r"f:\Luohino\Lutervyn\Lutervyn-IDE\lite-xl-source\logo_simple.svg"
    
    create_simple_logo_svg(src, svg)
