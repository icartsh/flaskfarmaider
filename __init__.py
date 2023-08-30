import os

try:
    import plexapi
except:
    try:
        os.system("pip install plexapi")
    except:
        os.system('python3 pip install plexapi')
