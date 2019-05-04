import os
import pickle
from collections import defaultdict
from datetime import datetime

import progressbar

from submission.models import Submission
from problem.models import Problem
from submission.util import SubmissionStatus


def run(*args):
  export_dir = os.environ.get("EXPORT_DIR", ".")

  problem_list = {}
  print("Processing problems...")
  for problem in progressbar.progressbar(Problem.objects.all()):
    problem_list[problem.id] = {
      "tags": [tag.name for tag in problem.tags],
      "ac_user_count": problem.ac_user_count,
      "total_user_count": problem.total_user_count,
      "ac_count": problem.ac_count,
      "total_count": problem.total_count,
      "reward": problem.reward,
      "labeled_difficulty": problem.level
    }

  print("Processing submissions...")
  sub_list_unfiltered = {}
  submission_record = defaultdict(int)
  for submission in progressbar.progressbar(Submission.objects.all().order_by("create_time")):
    user_problem = (submission.author_id, submission.problem_id)
    if submission.status == SubmissionStatus.ACCEPTED:
      if submission.author_id not in sub_list_unfiltered:
        sub_list_unfiltered[submission.author_id] = []
      lst = sub_list_unfiltered[submission.author_id]
      if submission_record[user_problem] != -1:
        lst.append((datetime.timestamp(submission.create_time),   # time
                    submission_record[user_problem],              # attempts
                    submission.problem_id))                       # problem id
        submission_record[user_problem] = -1
    else:
      if submission_record[user_problem] != -1:
        submission_record[user_problem] += 1
  sub_list = {k: v for k, v in sub_list_unfiltered.items() if len(v) >= 10}

  with open(os.path.join(export_dir, "problems.pickle"), "wb") as f:
    pickle.dump(problem_list, f)
  with open(os.path.join(export_dir, "submissions.pickle"), "wb") as f:
    pickle.dump(sub_list, f)
