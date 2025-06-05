from src.ui.main_window import MainWindow

def main():
    app = MainWindow()
    try:
        app.run()
    finally:
        app.cleanup()

if __name__ == "__main__":
    main()