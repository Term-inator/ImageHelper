from datetime import datetime

from PIL import Image, ImageDraw, ImageFont


def add_watermark(input_image_path, output_image_path, watermark_text, position, opacity=255):
    # Open the original image
    original = Image.open(input_image_path)

    # Create a transparent overlay
    transparent = Image.new(mode='RGBA', size=original.size)

    # Create an image to put the watermark on
    watermark = Image.new('RGBA', original.size, (255, 255, 255, 0))

    # Get a font
    font = ImageFont.truetype("arialbd.ttf", 72)  # You might need to adjust the path to a font

    # Get a drawing context
    draw = ImageDraw.Draw(watermark)

    # Set the opacity
    text_color = (0, 0, 0, opacity)  # Change the color and opacity

    # Draw the text
    text_width, text_height = draw.textsize(watermark_text, font=font)
    text_position = (position[0] - text_width // 2, position[1] - text_height // 2)
    draw.text(text_position, watermark_text, fill=text_color, font=font)

    # Combine the watermark with the transparent overlay
    transparent.paste(watermark, (0, 0), watermark)

    # Paste the watermark (with transparent overlay) onto the original image
    watermarked = Image.alpha_composite(original.convert('RGBA'), transparent)

    # Save the result
    watermarked.save(output_image_path, 'PNG')


currentTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
# Usage
add_watermark(r"D:\University\id2.jpg", 'id2.png', f'For Tara Energy Application\n{currentTime}', position=(600, 800), opacity=160)
