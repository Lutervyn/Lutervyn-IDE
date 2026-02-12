from PIL import Image
import os

def png_to_svg_path(png_path, output_svg):
    """Convert PNG to SVG with traced paths"""
    # This is a simplified version - for production you'd use potrace or similar
    img = Image.open(png_path).convert('L')  # Convert to grayscale
    img = img.resize((64, 64), Image.Resampling.LANCZOS)
    
    # Threshold to black and white
    threshold = 128
    img = img.point(lambda p: 255 if p > threshold else 0)
    
    # Save as bitmap first
    bmp_path = output_svg.replace('.svg', '.bmp')
    img.save(bmp_path)
    
    print(f"Saved bitmap to {bmp_path}")
    print("\nNEXT STEPS:")
    print("1. Install potrace: https://potrace.sourceforge.net/")
    print(f"2. Run: potrace {bmp_path} -s -o {output_svg}")
    print("3. Then run this script with --step2 flag")
    
    return bmp_path

def svg_to_font(svg_path, font_path, output_font):
    """Convert SVG to font glyphs using fontforge"""
    try:
        import fontforge
    except ImportError:
        print("ERROR: fontforge not installed")
        print("Install with: pip install fontforge")
        print("Or download from: https://fontforge.org/")
        return False
    
    # Open existing font
    font = fontforge.open(font_path)
    
    # Import SVG into glyphs for characters '5', '6', '7', '8', '9'
    # For now, just import into character '5' as the main logo
    glyph = font.createChar(ord('5'))
    glyph.clear()
    glyph.importOutlines(svg_path)
    glyph.width = 1000  # Set glyph width
    
    # Save modified font
    font.generate(output_font)
    print(f"Generated new font: {output_font}")
    return True

if __name__ == "__main__":
    import sys
    
    src_png = r"C:\Users\KING\.gemini\antigravity\brain\2d19dad9-e9ff-4a7f-be58-2566c58c2311\lutervyn_ide_icon_bw_v3_1769777985219.png"
    svg_path = r"f:\Luohino\Lutervyn\Lutervyn-IDE\lite-xl-source\logo.svg"
    font_path = r"f:\Luohino\Lutervyn\Lutervyn-IDE\lite-xl-source\data\fonts\icons.ttf"
    output_font = r"f:\Luohino\Lutervyn\Lutervyn-IDE\lite-xl-source\data\fonts\icons_new.ttf"
    
    if "--step2" in sys.argv:
        # Step 2: Convert SVG to font
        if os.path.exists(svg_path):
            svg_to_font(svg_path, font_path, output_font)
        else:
            print(f"ERROR: {svg_path} not found. Run step 1 first.")
    else:
        # Step 1: Convert PNG to SVG
        png_to_svg_path(src_png, svg_path)
