import os

try:
    import plexapi
except:
    try: os.system("pip install plexapi")
    except: pass
