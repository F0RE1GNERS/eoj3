DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'eoj',
        'CONN_MAX_AGE': 5,
        'HOST': '127.0.0.1',
        'PORT': 3306,
        'USER': 'root',
        'PASSWORD': 'root'
    }
}

SECRET_KEY = 'naive'
DEBUG = False

SITE_ID = 1

EMAIL_HOST = ""
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
SERVER_EMAIL = DEFAULT_FROM_EMAIL = ""
EMAIL_PORT = 25
EMAIL_USE_TLS = True
ADMINS = [('ultmaster', 'scottyugochang@hotmail.com'), ('zerol', 'zerolfx0@gmail.com')]
ADMIN_EMAIL = ""
IPWARE_PRIVATE_IP_PREFIX = ('202.120.88.',)

RUNNER_CONFIG = {
    "cpp": {
        "compiler_file": "/usr/bin/g++",
        "compiler_args": ["-O2", "-std=c++11", '-o', "foo", "foo.cc", "-DONLINE_JUDGE", "-lm",
                          "-fmax-errors=3"],
        "code_file": "foo.cc",
        "execute_file": "foo",
    },
    "java": {
        "compiler_file": "/usr/bin/javac",
        "compiler_args": ["-encoding", "utf8", "Main.java"],
        "code_file": "Main.java",
        "execute_file": "/usr/bin/java",
        "execute_args": ["-Xss1M", "-XX:MaxPermSize=16M", "-XX:PermSize=8M", "-Xms16M", "-Xmx{max_memory}M",
                         "-Dfile.encoding=UTF-8", "Main"],
    },
    "python": {
        "compiler_file": "/usr/bin/python3",
        "compiler_args": ["-m", "py_compile", "foo.py"],
        "code_file": "foo.py",
        "execute_file": "/usr/bin/python3",
        "execute_args": ["foo.py"]
    }
}
