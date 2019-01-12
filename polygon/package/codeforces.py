import io
import os
import random
import subprocess
import threading
import zipfile
from datetime import datetime
from xml.etree import ElementTree

from django.conf import settings

from account.models import User
from polygon.models import CodeforcesPackage


def create_task(problem_id: str, created_by: User):
  cf_settings = settings.CODEFORCES_POLYGON_CONFIG
  dst_dir = "cf_%s_%s" % (problem_id, "".join([random.choice("0123456789abcdef") for _ in range(6)]))
  dst_address = os.path.join(settings.REPO_DIR, dst_dir)

  def create_task_helper():
    package = CodeforcesPackage.objects.create(created_by=created_by, dir_name=dst_dir, remote_problem_id=problem_id)
    log_dir = os.path.join(dst_address, "logs")
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, "django.log"), "w") as stderr:
      subp = subprocess.run(["sudo", cf_settings["script"], cf_settings["key"], cf_settings["secret"], problem_id, dst_address],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=stderr)
    if subp.returncode:
      package.status = 1
    else:
      try:
        tree = ElementTree.parse(os.path.join(dst_address, "package", "problem.xml"))
        root = tree.getroot()
        package.short_name = root.attrib["short-name"]
        package.revision = root.attrib["revision"]
        package.status = 0
      except:
        package.status = 1
    package.running_time = (datetime.now() - package.create_time).total_seconds()
    package.status = 1 if subp.returncode else 0
    package.save()

  threading.Thread(target=create_task_helper).start()


def pack_log_files(package: CodeforcesPackage):
  bytes_io = io.BytesIO()
  logs_dir = os.path.join(settings.REPO_DIR, package.dir_name, "logs")
  with zipfile.ZipFile(bytes_io, "w") as zipFile:
    for file in os.listdir(logs_dir):
      zipFile.write(os.path.join(logs_dir, file), file)
  bytes_io.seek(0)
  return bytes_io.read()


