import hashlib

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import six
from django.utils import timezone
from django.utils.crypto import salted_hmac, constant_time_compare
from django.utils.http import int_to_base36, base36_to_int


def case_hash(problem_id, case_input, case_output):
  hash1 = hashlib.sha256(str(problem_id).encode()).digest()
  hash2 = hashlib.sha256(case_input).digest()
  hash3 = hashlib.sha256(case_output).digest()
  return hashlib.sha256(hash1 + hash2 + hash3).hexdigest()


def file_hash(file, lang):
  hash1 = hashlib.sha256(open(file, 'rb').read()).digest()
  hash2 = hashlib.sha256(lang.encode()).digest()
  return hashlib.sha256(hash1 + hash2).hexdigest()


def sha_hash(x):
  if not isinstance(x, bytes):
    x = str(x).encode()
  return hashlib.sha256(x).hexdigest()


# similar to django.contrib.auth.tokens.PasswordResetTokenGenerator
class TokenGenerator(object):
  def make_token(self, user, obj):
    content_type_id = ContentType.objects.get_for_model(obj).pk
    object_id = obj.pk
    return self._make_hash(user, self._num_minutes(), content_type_id, object_id)

  def check_token(self, user, token, expire_minutes=-1):
    try:
      (timestamp, content_type_id, object_id, _) = token.split("-")
      timestamp = base36_to_int(timestamp)
      content_type_id = base36_to_int(content_type_id)
      object_id = base36_to_int(object_id)
    except ValueError:
      return None
    if not constant_time_compare(self._make_hash(user, timestamp, content_type_id, object_id), token):
      return None
    if self._num_minutes() - timestamp > expire_minutes > 0:
      return None
    return ContentType.objects.get_for_id(content_type_id).get_object_for_this_type(pk=object_id)

  def _make_hash(self, user, timestamp, content_type_id, object_id):
    content = "%s-%s-%s" % (int_to_base36(timestamp), int_to_base36(content_type_id), int_to_base36(object_id))

    Hash = salted_hmac(
      settings.SECRET_KEY[::2],
      content + six.text_type(user.pk) + user.password
    ).hexdigest()[::2]

    return "%s-%s" % (content, Hash)

  def _num_minutes(self):
    return int(timezone.now().timestamp()) // 60


token_generator = TokenGenerator()
