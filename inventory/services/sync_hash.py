import hashlib


def calculate_file_hash(filepath):

    sha256 = hashlib.sha256()

    with open(filepath, "rb") as file:

        while chunk := file.read(8192):

            sha256.update(chunk)


    return sha256.hexdigest()