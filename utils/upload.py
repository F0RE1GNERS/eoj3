from os import path, makedirs


def save_uploaded_file_to(file, directory, filename=None, size_limit=None, keep_extension=False):
    """
    :param file: UploadedFile instance
    :param directory: the real dirname of your destination
    :param filename: file name by default
    :param size_limit: by megabytes, exceeding size_limit will raise ValueError
    :param keep_extension: True or False, if you rename your file and filename does not have an extension, the
                           original filename's extension will be used as the new extension. If the original file
                           does not have an extension, then nothing will happen.
    :return: new path
    """
    if size_limit and file.size > size_limit * 1024576:
        raise ValueError("File is too large")
    if keep_extension and filename:
        raw_ext = path.splitext(file.name)[1]
        filename_body, filename_ext = path.splitext(filename)
        if not filename_ext:
            filename = filename + raw_ext
    makedirs(directory, exist_ok=True)
    new_path = path.join(directory, filename if filename else file.name)
    with open(new_path, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    return new_path
