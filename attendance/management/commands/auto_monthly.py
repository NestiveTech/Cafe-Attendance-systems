from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.test import RequestFactory
from attendance.views import trigger_monthly_report
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware

class Command(BaseCommand):
    help = 'Auto-send monthly report to Owner'

    def handle(self, *args, **kwargs):
        try:
            owner = User.objects.get(pk=1) 
            factory = RequestFactory()
            request = factory.get('/report/monthly/')
            request.user = owner
            
            middleware = SessionMiddleware(lambda x: None)
            middleware.process_request(request)
            request.session.save()
            MessageMiddleware(lambda x: None).process_request(request)
            
            trigger_monthly_report(request)
            self.stdout.write(f"Report sent to {owner.email}")
        except Exception as e:
            self.stdout.write(f"Error: {e}")