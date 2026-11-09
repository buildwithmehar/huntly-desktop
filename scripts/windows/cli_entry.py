from multiprocessing import freeze_support

if __name__ == "__main__":
    freeze_support()
    from huntly.cli import main

    main()
