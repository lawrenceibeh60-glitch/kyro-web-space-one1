"""run.py - start KAE: python run.py  ->  http://127.0.0.1:5000"""
import config
from backend.app.application import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG, use_reloader=False)
