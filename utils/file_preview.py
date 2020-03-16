import operator
import os
import re
from functools import cmp_to_key


def compare(a, b):
  x, y = a[0], b[0]
  try:
    cx = list(map(lambda x: int(x) if x.isdigit() else x, re.split(r'(\d+)', x)))
    cy = list(map(lambda x: int(x) if x.isdigit() else x, re.split(r'(\d+)', y)))
    if operator.eq(cx, cy):
      raise ArithmeticError
    return -1 if operator.lt(cx, cy) else 1
  except Exception:
    if x == y:
      return 0
    return -1 if x < y else 1


def special_sort(lst):
  return list(map(lambda x: x[0], sorted(map(lambda x: (x, 0), lst), key=cmp_to_key(compare))))


def sort_data_list_from_directory(directory):
  try:
    raw_namelist = list(filter(lambda x: os.path.split(x)[0] == '', os.listdir(directory)))
    result = []
    file_set = set(raw_namelist)
    patterns = {r'(.*)\.in$': [r'\1.out', r'\1.ans'], r'(.*)\.IN$': [r'\1.OUT', r'\1.ANS'],
                r'input(.*)': [r'output\1', r'answer\1'], r'INPUT(.*)': [r'OUTPUT\1', r'ANSWER\1'],
                r'(\d+)': [r'\1.a'], r'(.*)\.in(.*)$': [r'\1.out\2', r'\1.ans\2'], }

    for file in raw_namelist:
      for pattern_in, pattern_out in patterns.items():
        if re.search(pattern_in, file) is not None:
          for pattern in pattern_out:
            try_str = re.sub(pattern_in, pattern, file)
            if try_str in file_set:
              file_set.remove(try_str)
              file_set.remove(file)
              result.append((file, try_str))
              break

    return sorted(result, key=cmp_to_key(compare))
  except Exception:
    return []


def sort_data_from_zipfile(file_path):
  """
  Deprecated
  """
  return []


def get_file_list(file_path, prefix):
  try:
    if not os.path.exists(file_path):
      raise FileNotFoundError
    result = []
    for file in os.listdir(file_path):
      result.append(dict(
        filename=file,
        size="%dKB" % (os.path.getsize(os.path.join(file_path, file)) // 1024),
        path=os.path.join('/upload/', prefix, file)
      ))
    return result
  except:
    return []
