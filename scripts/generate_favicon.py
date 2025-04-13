import os
import argparse
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm

def create_favicon(output_dir: str, background_color: tuple = (13, 110, 253), 
                  text_color: tuple = (255, 255, 255), text: str = "1",
                  size: tuple = (32, 32)) -> None:
    """
    Generate a favicon with customizable parameters.
    
    Args:
        output_dir (str): Directory to save the favicon
        background_color (tuple): RGB color for the circle background
        text_color (tuple): RGB color for the text
        text (str): Text to display in the favicon
        size (tuple): Size of the favicon in pixels
    """
    # Create progress bar for the favicon generation steps
    steps = ['Creating base image', 'Drawing circle', 'Adding text', 'Saving favicon']
    progress_bar = tqdm(steps, desc='Generating favicon')

    # Create a new image with a transparent background
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    progress_bar.update(1)

    # Create a drawing object
    draw = ImageDraw.Draw(img)
    
    # Draw a circle
    circle_bbox = [0, 0, size[0]-1, size[1]-1]
    draw.ellipse(circle_bbox, fill=background_color)
    progress_bar.update(1)

    # Try to load Arial Bold font, fall back to default if not available
    try:
        font = ImageFont.truetype("Arial Bold.ttf", size[0]//2)
    except OSError:
        font = ImageFont.load_default()

    # Calculate text position to center it
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = (size[0] - text_width) // 2
    text_y = (size[1] - text_height) // 2

    # Draw the text
    draw.text((text_x, text_y), text, font=font, fill=text_color)
    progress_bar.update(1)

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the image
    output_path = os.path.join(output_dir, 'favicon.png')
    img.save(output_path)
    progress_bar.update(1)
    
    progress_bar.close()
    print(f"\nFavicon generated successfully at: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Generate a custom favicon')
    parser.add_argument('--output-dir', type=str, default='app/static/img',
                      help='Directory to save the favicon (default: app/static/img)')
    parser.add_argument('--bg-color', type=int, nargs=3, default=[13, 110, 253],
                      help='Background color in RGB (default: 13 110 253)')
    parser.add_argument('--text-color', type=int, nargs=3, default=[255, 255, 255],
                      help='Text color in RGB (default: 255 255 255)')
    parser.add_argument('--text', type=str, default='1',
                      help='Text to display in the favicon (default: 1)')
    parser.add_argument('--size', type=int, nargs=2, default=[32, 32],
                      help='Size of the favicon in pixels (default: 32 32)')

    args = parser.parse_args()

    create_favicon(
        output_dir=args.output_dir,
        background_color=tuple(args.bg_color),
        text_color=tuple(args.text_color),
        text=args.text,
        size=tuple(args.size)
    )

if __name__ == '__main__':
    main() 