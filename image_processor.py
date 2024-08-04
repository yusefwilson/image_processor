import sys
import os
import requests
from PIL import Image
from io import BytesIO
import cv2
import numpy as np
from dotenv import load_dotenv

# Function to download image
def download_image(url: str) -> Image:
    response = requests.get(url)
    if response.status_code == 200:
        img = Image.open(BytesIO(response.content))
        return img
    else:
        raise Exception('Image could not be retrieved')

# Function to convert image to PNG
def convert_to_png(image: Image) -> Image:
    png_image = image.convert('RGBA')
    return png_image

# Function to remove background using removebg API
def remove_background(image_path: str, api_key: str) -> Image:
    with open(image_path, 'rb') as file:
        response = requests.post(
            'https://api.remove.bg/v1.0/removebg',
            files={'image_file': file},
            data={'size': 'auto'},
            headers={'X-Api-Key': api_key},
        )
        if response.status_code == requests.codes.ok:
            img = Image.open(BytesIO(response.content))
            return img
        else:
            raise Exception('Error:', response.status_code, response.text)
        
# Function to add a white outline
def add_white_outline(image: Image, outline_width: int=10, blur_radius: int=5) -> Image:
    # Convert image to numpy array
    np_image = np.array(image)
    
    # Create a mask of the alpha channel
    alpha = np_image[:, :, 3]
    
    # Find the edges of the alpha channel
    edges = cv2.Canny(alpha, 100, 200)
    
    # Dilate the edges to create the outline
    kernel = np.ones((outline_width, outline_width), np.uint8)
    outline = cv2.dilate(edges, kernel, iterations=1)
    
    # Apply morphological transformation to smooth and round the corners
    ellipse_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (outline_width, outline_width))
    outline = cv2.morphologyEx(outline, cv2.MORPH_CLOSE, ellipse_kernel)
    
    # Apply Gaussian blur to smooth the outline
    outline = cv2.GaussianBlur(outline, (blur_radius, blur_radius), 0)
    
    # Create an RGBA outline image with a white color
    outline_image = np.zeros_like(np_image)
    outline_image[:, :, :3] = 255  # Set color to white
    outline_image[:, :, 3] = outline  # Set alpha to the outline
    
    # Convert outline to PIL Image
    outline_pil = Image.fromarray(outline_image)
    
    # Composite the outline with the original image
    outlined_image = Image.alpha_composite(outline_pil, image)
    
    return outlined_image

# Function to rename image
def rename_image(image: Image, new_name: str) -> None:
    image.save(new_name)

# Main function
def process_image(url: str, api_key: str, new_name: str) -> None:

    # Download the image if it is an internet url, otherwise assume it is a local file
    image = None
    if url.startswith('http'):
        image = download_image(url)
    else:
        image = Image.open(url)
    
    # Convert to PNG
    png_image = convert_to_png(image)
    png_image.save('temp.png')  # Save temporarily for background removal
    
    # Remove background
    bg_removed_image = remove_background('temp.png', api_key)
    bg_removed_image.save('temp_no_bg.png')  # Save temporarily for outlining
    
    # Outline the image
    outlined_image = add_white_outline(bg_removed_image)
    
    # Rename and save the final image
    rename_image(outlined_image, new_name)
    print(f'Image saved as {new_name}')

    # delete the temporary files
    os.remove('temp.png')
    os.remove('temp_no_bg.png')

# Load environment variables from .env file
load_dotenv()

# Retrieve the API key from the environment variables
REMOVE_BG_API_KEY = os.getenv('REMOVE_BG_API_KEY')

def main() -> None:

    if len(sys.argv) != 3:
        print('Usage: python image_processor.py <image_url> <new_name>')
        sys.exit(1)

    # get the image url, and the new save name from the command line
    url = sys.argv[1]
    new_name = sys.argv[2]

    # make sure new name ends in .png, and if not, add it. also ensure it is named so that it ends up in the processed_images folder
    if not new_name.endswith('.png'):
        new_name += '.png'
    new_name = os.path.join('processed_images', new_name)

    # process the image
    process_image(url, REMOVE_BG_API_KEY, new_name)

if __name__ == '__main__':
    main()