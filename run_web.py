# Run: python3 run_web.py from the root folder

from smart_energy.web.app import create_app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
