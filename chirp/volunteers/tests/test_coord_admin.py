
"""tests Volunteer Coordinator administration"""

import datetime
from datetime import timedelta
import unittest
from chirp.volunteers.admin import VolunteerAdminForm
from chirp.volunteers.models import (Event, Volunteer, Committee, Task,
                                     TaskType, TaskAssignment, TaskStatus)
from django import forms
from django.test import TestCase
from django.contrib.auth.models import User
from chirp.volunteers.tests.base import eq_, CoordinatorLoginTest

class TestVolunteerMgmt(CoordinatorLoginTest):

    fixtures = ['users.json', 'volunteers.json']
    def setUp(self):
        super(TestVolunteerMgmt, self).setUp()

    def tearDown(self):
        super(TestVolunteerMgmt, self).tearDown()
        for v in Volunteer.objects.all():
            v.delete()

    def test_index(self):
        resp = self.client.get('/')
        form = str(resp.context[0]['volunteer_activity_form'])
        first_date = (datetime.datetime.now() - timedelta(weeks=52)).date()
        last_date = datetime.datetime.now().date()
        assert '<option value="%s">' % (first_date.strftime("%Y-%m-01")) in form
        assert '<option value="%s">' % (last_date.strftime("%Y-%m-01")) in form

    def test_create_volunteer(self):

        vol_count = 3
        v = Volunteer.objects.all()
        eq_(v.count(), vol_count)

        user = User.objects.filter(username='volunteertest')[0].id
        committees = []
        committees.append(Committee.objects.filter(name='Music Department')[0].id)
        committees.append(Committee.objects.filter(name='Tech Committee')[0].id)

        resp = self.client.post('/volunteers/volunteer/add/', {
            'user': user,
            'committees': committees,
        })
        eq_(resp.status_code, 302)
        assert resp['Location'].endswith("/volunteers/volunteer/"), (
                                    "unexpected redirect: %s" % resp['Location'])

        v = Volunteer.objects.all()
        eq_(v.count(), vol_count + 1)
        vol = v[0]
        eq_(vol.user.username, 'volunteertest')
        eq_(sorted([c.name for c in vol.committees.all()]), [u'Music Department', u'Tech Committee'])

class TestVolunteerValidation(TestCase):

    fixtures = ['users.json']

    def test_user_must_be_volunteer(self):
        user = User.objects.filter(username='plainuser')[0]

        f = VolunteerAdminForm()
        f.cleaned_data= {'user': user}
        try:
            f.clean_user()
        except forms.ValidationError, err:
            eq_(err.messages[0], (
                "User plainuser cannot be a volunteer because he/she is not "
                "in the Volunteer group (You can fix this in Home > Auth > "
                "Users under the Groups section)"))
        else:
            raise AssertionError("Expected ValidationError")

    def test_user_must_be_staff(self):
        user = User.objects.filter(username='plainuser_not_staff')[0]

        f = VolunteerAdminForm()
        f.cleaned_data= {'user': user}
        try:
            f.clean_user()
        except forms.ValidationError, err:
            eq_(err.messages[0], (
                "User plainuser_not_staff cannot be a volunteer because he/she "
                "has not been marked with Staff status (you can fix this in Home > "
                "Auth > Users under the Permissions section)"))
        else:
            raise AssertionError("Expected ValidationError")

class TestTaskMgmt(CoordinatorLoginTest):

    fixtures = ['users.json', 'volunteers.json', 'tasks.json']

    def test_create_task(self):

        vol_id = Volunteer.objects.all()[0].id
        committee_id = Committee.objects.filter(name='Tech Committee')[0].id
        task_id = Task.objects.filter(description='Ears&Eyes Fest at Hideout')[0].id
        task_status_id = TaskStatus.objects.filter(status='Assigned')[0].id

        resp = self.client.post('/volunteers/taskassignment/add/', {
            'volunteer': vol_id,
            'points': 1,
            'task': task_id,
            'status': task_status_id
        })
        # print resp.content
        eq_(resp.status_code, 302)
        assert resp['Location'].endswith("/volunteers/taskassignment/"), (
                                    "unexpected redirect: %s" % resp['Location'])

        task_asn = TaskAssignment.objects.all()[0]
        eq_(task_asn.volunteer.id, vol_id)
        eq_(task_asn.points, 1)
        eq_(task_asn.task.id, task_id)
        eq_(task_asn.status.id, task_status_id)


class TestCloneEvent(CoordinatorLoginTest):
    fixtures = ['users.json', 'tasks_to_manage.json']

    def test_clone_event(self):
        event = Event.objects.get(name='CHIRP Record Fair')
        resp = self.client.post('/chirp/tasks/clone-event', {
            'existing_event': event.id,
            'new_start_date': '2011-03-01',
            'new_name': 'My Shiny New Event'
        }, follow=True)
        eq_(resp.status_code, 200)
        new_event = Event.objects.get(name='My Shiny New Event')
        eq_(new_event.tasks_can_be_claimed, False)
        assert len(new_event.task_set.all()) > 0, (
                    'Unexpected: %r' % new_event.task_set.all())
