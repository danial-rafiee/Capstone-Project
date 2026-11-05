# Flask application factory

from .demo_data import build_demo_dashboard


def create_app(test_config: dict | None = None):
    # Keep the OOP classes and console example usable without Flask installed.
    from flask import Flask, render_template

    app = Flask(__name__)
    if test_config is not None:
        app.config.update(test_config)

    @app.get("/")
    def home():
        return render_template("dashboard.html", **build_demo_dashboard())

    return app
