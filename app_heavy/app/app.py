from flask import Flask, jsonify
import time
import numpy as np

app = Flask(__name__)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    start_time = time.time()
    x = np.random.rand(3000, 3000)
    for i in range(100):
        x = np.dot(x, x)
    elapsed_time = time.time() - start_time
    print(f'Heavy job executed successfully in {elapsed_time:.2f} seconds!')
    return jsonify({'message': f'Heavy job executed successfully in {elapsed_time:.2f} seconds!'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
