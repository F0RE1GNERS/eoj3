import zipfile
import os
import re

def sort_data_from_zipfile(file_path):
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError
        saved_file = zipfile.ZipFile(file_path)
        raw_namelist = list(filter(lambda x: os.path.split(x)[0] == '', saved_file.namelist()))
        print(raw_namelist)
        result = []
        file_set = set(raw_namelist)
        patterns = {'.in$': ['.out', '.ans'], 'input': ['output', 'answer']}

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

        return sorted(result)
    except Exception as e:
        return []
