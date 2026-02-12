from PIL import Image
import os

def convert_to_all_formats(png_path, resources_dir):
    if not os.path.exists(png_path):
        print(f"Error: {png_path} not found.")
        return

    img = Image.open(png_path)
    
    # 1. Save as .ico (Windows)
    ico_path = os.path.join(resources_dir, "icon.ico")
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, sizes=icon_sizes)
    print(f"Generated {ico_path}")

    # 2. Save as .icns (macOS)
    icns_path = os.path.join(resources_dir, "icon.icns")
    try:
        img.save(icns_path)
        print(f"Generated {icns_path}")
    except:
        print("Skipping .icns (possibly unsupported by this PIL version)")

    # 3. Save as icon.inl (C Header for Linux fallback)
    # This needs to be 64x64 RGBA
    inl_path = os.path.join(resources_dir, "icon.inl")
    img_64 = img.resize((64, 64), Image.Resampling.LANCZOS).convert("RGBA")
    data = list(img_64.getdata())
    
    with open(inl_path, "w") as f:
        f.write("static unsigned char icon_rgba[] = {\n")
        for i, (r, g, b, a) in enumerate(data):
            f.write(f"  0x{r:02x}, 0x{g:02x}, 0x{b:02x}, 0x{a:02x}")
            if i < len(data) - 1:
                f.write(",")
            if (i + 1) % 4 == 0:
                f.write("\n")
        f.write("};\n\n")
        f.write(f"static unsigned int icon_rgba_len = {len(data) * 4};\n")
    print(f"Generated {inl_path}")

if __name__ == "__main__":
    src = r"C:\Users\KING\.gemini\antigravity\brain\2d19dad9-e9ff-4a7f-be58-2566c58c2311\lutervyn_ide_icon_bw_v3_1769777985219.png"
    res = r"f:\Luohino\Lutervyn\Lutervyn-IDE\lite-xl-source\resources\icons"
    convert_to_all_formats(src, res)
