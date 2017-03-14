import os
import subprocess


def pandoc_execute(text):
    try:
        paths = os.environ.get('PATH').split(':')
        for path in paths:
            if path:
                file_path = os.path.join(path, 'pandoc')
                if os.path.exists(file_path):
                    process = subprocess.Popen(file_path, stdout=subprocess.PIPE)
    except Exception as e:
        raise OSError('Pandoc execution failure. Did you forget to install pandoc?')


def convert(text):
    pass