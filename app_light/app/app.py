from flask import Flask, jsonify
import time


#flask app ran on a container 
app = Flask (__name__)

#rest end point - default
@app.route('/')
def light():
    time.sleep(1)
    return jsonify({'message': 'Light job executed successfully!'})

if __name__ == '__main__' :
    app.run(debug=True, host='0.0.0.0', port=5000)