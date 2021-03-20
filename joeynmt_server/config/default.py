import os
from pathlib import Path
import socket

DEBUG = False

SECRET_KEY = "asdkjhad321987u21oisnmlk8ud921jpnsöoilawkjdmöod821ue9p2jöolkj"

SQLALCHEMY_DATABASE_URI = 'sqlite:///{}'.format(
    (Path(os.path.dirname(__file__)) / '../joeynmt_server.db').resolve()
)
SQLALCHEMY_ECHO = False

JOEY_DIR = Path('/home/students/will/ma/joeynmt')

USE_CUDA_TRANSLATE = True
USE_CUDA_TRAIN = 'gpu' in socket.gethostname()

TRAIN_AFTER_FEEDBACK = False
