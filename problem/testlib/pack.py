"""
This is used to pack testlib into a json
Then you can load into database by using:
    manage.py loaddata <fixturename>
    fixturename here is `testlib.json`
"""

import json
from os import path, listdir
category = ['checker', 'generator', 'validator', 'validator']
father_dir = path.dirname(__file__)
output_file = open(path.join(father_dir, 'testlib.json'), 'w')
data = []
for cat in category:
    for file in listdir(path.join(father_dir, cat)):
        if file.startswith('.'):
            continue
        with open(path.join(father_dir, cat, file)) as fs:
            code = fs.read()
        data.append(dict(model='problem.TrustedSubmission',
                         name=file.split('.')[0],
                         code=code,
                         lang='cpp',
                         category=cat))
json.dump(data, output_file)
output_file.close()