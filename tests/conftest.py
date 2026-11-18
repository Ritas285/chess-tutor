import os
import sys
from pathlib import Path

# I rami PDF sono opzionali (i PDF non stanno nel git): i test vedono SEMPRE solo i rami .md, anche se nel .env c'è RAMI_PDF=1.
# Va impostato prima che `config` venga importato (load_dotenv non sovrascrive una variabile già presente).
os.environ["RAMI_PDF"] = "0"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
