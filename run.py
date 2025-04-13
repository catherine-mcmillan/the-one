import os
from app import create_app
from app.extensions import db

app = create_app()

if __name__ == '__main__':
    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    try:
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            print(f"Created data directory at {data_dir}")
    except Exception as e:
        print(f"Warning: Could not create or access data directory: {e}")

    app.run(debug=True)