from flask import Flask, jsonify
import time
import numpy as np

app = Flask(__name__)


@app.route('/')
def heavy():
    start_time = time.time()
    x = np.random.rand(10000, 10000)
    for i in range(100):
        x = np.dot(x, x)
    elapsed_time = time.time() - start_time
    return jsonify({'message': f'Heavy job executed successfully in {elapsed_time:.2f} seconds!'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)