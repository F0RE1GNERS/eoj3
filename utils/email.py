import time
import traceback

from django.core.mail import send_mail, EmailMultiAlternatives, get_connection


def send_mail_with_bcc(subject, html_message, recipient_list, fail_silently=False):

    def divide_group(lst, k):
        return [lst[i:i+k] for i in range(0, len(lst), k)]

    for grp in divide_group(recipient_list, 100):
        try:
            connection = get_connection(
                username=None,
                password=None,
                fail_silently=fail_silently,
            )
            mail = EmailMultiAlternatives(subject, bcc=grp, connection=connection)
            mail.attach_alternative(html_message, 'text/html')
            mail.send()
        except:
            traceback.print_exc()
        time.sleep(3)
