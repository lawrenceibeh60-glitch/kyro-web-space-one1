"""backend/app/application.py - Flask app factory. Serves API under /api and frontend/ at /."""
from flask import Flask, send_from_directory

import config
from backend.app import middleware


def create_app():
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
    app.json.sort_keys = False

    from backend.api import (
        animations,
        ai_studio,
        audio,
        assets,
        cameras,
        characters,
        drawings,
        effects,
        exports,
        health,
        layers,
        projects,
        rendering,
        rigs,
        scenes,
        schemas,
        settings,
        timeline,
    )

    app.register_blueprint(health.bp, url_prefix="/api")
    app.register_blueprint(ai_studio.bp, url_prefix="/api")
    app.register_blueprint(projects.bp, url_prefix="/api/projects")
    app.register_blueprint(exports.bp, url_prefix="/api/exports")
    app.register_blueprint(scenes.bp, url_prefix="/api/projects")
    app.register_blueprint(layers.bp, url_prefix="/api/projects")
    app.register_blueprint(timeline.bp, url_prefix="/api/projects")
    app.register_blueprint(drawings.bp, url_prefix="/api/projects")
    app.register_blueprint(animations.bp, url_prefix="/api/projects")
    app.register_blueprint(audio.bp, url_prefix="/api/projects")
    app.register_blueprint(assets.bp, url_prefix="/api/projects")
    app.register_blueprint(cameras.bp, url_prefix="/api/projects")
    app.register_blueprint(characters.bp, url_prefix="/api/projects")
    app.register_blueprint(rigs.bp, url_prefix="/api/projects")
    app.register_blueprint(effects.bp, url_prefix="/api/projects")
    app.register_blueprint(rendering.bp, url_prefix="/api/projects")
    app.register_blueprint(schemas.bp, url_prefix="/api")
    app.register_blueprint(settings.bp, url_prefix="/api")

    middleware.install(app)

    @app.get("/")
    def index():
        return send_from_directory(config.FRONTEND_DIR, "index.html")

    @app.get("/<path:filename>")
    def frontend_files(filename):
        return send_from_directory(config.FRONTEND_DIR, filename)

    return app
