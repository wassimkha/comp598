from flask import Flask
import tensorflow as tf
import time

app = Flask(__name__)


@app.route('/')
def heavy():
    print('Training a neural network model.')
    # Create a simple neural network model
    model = tf.keras.models.Sequential([
        tf.keras.layers.Dense(10, activation='relu', input_shape=(784,)),
        tf.keras.layers.Dense(10, activation='softmax')
    ])

    # Compile the model
    model.compile(optimizer='adam',
                  loss='categorical_crossentropy',
                  metrics=['accuracy'])

    # Generate some random input data
    x = tf.random.normal(shape=(1000, 784))
    y = tf.random.normal(shape=(1000, 10))

    # Train the model for 100 epochs
    start_time = time.time()
    model.fit(x, y, epochs=100)
    end_time = time.time()

    # Calculate the training time
    training_time = end_time - start_time

    return 'Training completed successfully! Training time: {} seconds'.format(training_time)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)