from flask import Flask, jsonify
import time
import numpy as np


app = Flask (__name__)

# @app.route('/')
# def medium():
#     # Simulating medium job
#     start_time = time.time()
#     x = np.random.rand(1000, 1000)
#     for i in range(10):
#         x = np.sqrt(x)
#     elapsed_time = time.time() - start_time
#     return jsonify({'message': f'Medium job executed successfully in {elapsed_time:.2f} seconds!'})

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    # Simulating medium job
    start_time = time.time()
    x = np.random.rand(1000, 1000)
    for i in range(10):
        x = np.sqrt(x)
    elapsed_time = time.time() - start_time
    return jsonify({'message': f'Medium job executed successfully in {elapsed_time:.2f} seconds!'})

                            

if __name__ == '__main__':
    app.run(debug = True, host='0.0.0.0', port=5000)