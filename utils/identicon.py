import io
from hashlib import md5

from PIL import Image, ImageDraw

GRID_SIZE = 9
BORDER_SIZE = 25
SQUARE_SIZE = 50


class Identicon(object):
  def __init__(self, str_, background='white'):
    """
    `str_` is the string used to generate the identicon.
    `background` is the background of the identicon.
    """
    w = h = BORDER_SIZE * 2 + SQUARE_SIZE * GRID_SIZE
    self.image = Image.new('RGB', (w, h), background)
    self.draw = ImageDraw.Draw(self.image)
    self.hash = self.digest(str_)

  def digest(self, str_):
    """
    Returns a md5 numeric hash
    """
    return int(md5(str_.encode('utf-8')).hexdigest(), 16)

  def calculate(self):
    """
    Creates the identicon.
    First three bytes are used to generate the color,
    remaining bytes are used to create the drawing
    """
    color = (self.hash & 0xff, self.hash >> 8 & 0xff, self.hash >> 16 & 0xff)
    self.hash >>= 24  # skip first three bytes
    square_x = square_y = 0  # init square position
    for x in range(GRID_SIZE * (GRID_SIZE + 1) // 2):
      if self.hash & 1:
        x = BORDER_SIZE + square_x * SQUARE_SIZE
        y = BORDER_SIZE + square_y * SQUARE_SIZE
        self.draw.rectangle(
          (x, y, x + SQUARE_SIZE, y + SQUARE_SIZE),
          fill=color,
          outline=color
        )
        # following is just for mirroring
        x = BORDER_SIZE + (GRID_SIZE - 1 - square_x) * SQUARE_SIZE
        self.draw.rectangle(
          (x, y, x + SQUARE_SIZE, y + SQUARE_SIZE),
          fill=color,
          outline=color
        )
      self.hash >>= 1  # shift to right
      square_y += 1
      if square_y == GRID_SIZE:  # done with first column
        square_y = 0
        square_x += 1

  def generate(self):
    """
    Save and show calculated identicon
    """
    self.calculate()
    with open('identicon.png', 'wb') as out:
      self.image.save(out, 'PNG')
    self.image.show()

  def get_bytes(self, format='PNG'):
    '''
    usage:  i = Identicon('xx')
            print(i.base64())
    return: this image's base64 code
    created by: liuzheng712
    bug report: https://github.com/liuzheng712/identicons/issues
    '''
    self.calculate()
    fp = io.BytesIO()
    self.image.encoderinfo = {}
    self.image.encoderconfig = ()

    if format.upper() not in Image.SAVE:
      Image.init()
    save_handler = Image.SAVE[format.upper()]
    try:
      save_handler(self.image, fp, '')
    finally:
      fp.seek(0)
    return fp
