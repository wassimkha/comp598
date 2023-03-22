from flask import Flask, jsonify
import sys
import time
from PIL import Image
import numpy as np


app = Flask (__name__)

@app.route('/')
def medium():
     # Load image
    img_path = 'test_image.jpg'
    img = Image.open(img_path)

    # Rotate image by 45 degrees
    rotated_img = img.rotate(45)

    # Convert image to numpy array
    img_array = np.array(rotated_img)

    # Invert colors of image
    inverted_img = 255 - img_array

    # Convert back to PIL Image
    final_img = Image.fromarray(inverted_img)

    # Sleep for 10 seconds to simulate computation time
    time.sleep(10)

                            
    return 'Medium job completed successfully! Image transformation performed on image with size' + final_img.size

if __name__ == '__main__':
    app.run(debug = True, host='0.0.0.0', port=5000)