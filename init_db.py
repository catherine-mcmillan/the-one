from app import create_app
import os
import sqlite3

def init_database():
    """Initialize the database file and directory with proper permissions"""
    app = create_app()
    
    with app.app_context():
        try:
            # Get database path from config
            db_path = app.config['SQLITE_DB']
            db_dir = os.path.dirname(db_path)
            
            # Create directory if it doesn't exist
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                print(f"Created database directory: {db_dir}")
                # Set permissions to allow read/write for all users
                os.chmod(db_dir, 0o777)
            
            # Create database file if it doesn't exist
            if not os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.close()
                os.chmod(db_path, 0o666)
                print(f"Created database file: {db_path}")
            
            print("Database initialization completed successfully")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            raise

if __name__ == '__main__':
    init_database() 