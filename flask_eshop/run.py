import os

from eshop import create_app

app = create_app()

if __name__ == '__main__':
    # Debug mode only for local development: FLASK_DEBUG=1 python run.py
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
