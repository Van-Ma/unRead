from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from backend import auth, config, db, graph
from backend.api import bp


def create_app():
    db.init()
    graph.init()

    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    CORS(app, supports_credentials=True)
    auth.init(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(bp)

    @app.errorhandler(Exception)
    def handle_error(e):
        if isinstance(e, HTTPException):
            return jsonify(error=e.description), e.code
        if isinstance(e, (ValueError, FileNotFoundError)):
            return jsonify(error=str(e)), 400
        app.logger.exception(e)
        return jsonify(error=str(e)), 500

    return app


if __name__ == "__main__":
    create_app().run(port=5000, debug=True)
