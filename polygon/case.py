import io
import re
import chardet

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


def well_form_binary(binary):
    try:
        encoding = chardet.detect(binary).get('encoding', 'utf-8')
        return well_form_text(binary.decode(encoding))
    except:
        return ''
