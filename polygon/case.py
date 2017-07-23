import io
import re

white_space_reg = re.compile(r'[\x00-\x20]+')


def read_by_formed_lines(fileobj):
    for line in fileobj:
        yield ' '.join(white_space_reg.split(line.strip()))


def well_form_text(text):
    stream = io.StringIO(text.strip())
    out_stream = io.StringIO()
    for line in read_by_formed_lines(stream):
        out_stream.writelines([line, '\n'])
    out_stream.seek(0)
    return out_stream.read()
