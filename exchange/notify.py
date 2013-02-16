__author__ = 'aviraldg'

from google.appengine.api import mail
from google.appengine.api.app_identity import get_application_id

def notify(conversation, message, sender):
    to = [p.email for p in conversation.participants if p != sender]
    sender = '%s <conversation-%s@%s.appspotmail.com>' % (sender.name, conversation.key.id(), get_application_id())
    mail.send_mail(sender=sender, to=to, subject=conversation.readable_subject, body=message.content)
