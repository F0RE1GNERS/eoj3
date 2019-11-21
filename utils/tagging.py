def edit_string_for_tags(tags):
  """
  Simplified version of comma separated tags
  """
  names = []
  for tag in tags:
    name = tag.name
    if ',' in name:
      names.append('"%s"' % name)
      continue
    names.append(name)
  return ','.join(names)
