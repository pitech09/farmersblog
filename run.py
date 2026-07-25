from app import create_app
from app.config import get_config

config_class = get_config()
app = create_app(config_class)

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'], port=5000)
