import hashlib


def case_hash(problem_id, case_input, case_output):
    hash1 = hashlib.sha256(str(problem_id).encode()).digest()
    hash2 = hashlib.sha256(case_input).digest()
    hash3 = hashlib.sha256(case_output).digest()
    return hashlib.sha256(hash1 + hash2 + hash3).hexdigest()


def file_hash(file, lang):
    hash1 = hashlib.sha256(open(file, 'rb').read()).digest()
    hash2 = hashlib.sha256(lang.encode()).digest()
    return hashlib.sha256(hash1 + hash2).hexdigest()
