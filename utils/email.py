from django.core.mail import send_mail, EmailMultiAlternatives, get_connection


def send_mail_with_bcc(subject, html_message, recipient_list, fail_silently=False):
    connection = get_connection(
        username=None,
        password=None,
        fail_silently=fail_silently,
    )
    mail = EmailMultiAlternatives(subject, bcc=recipient_list, connection=connection)
    mail.attach_alternative(html_message, 'text/html')
    return mail.send()

