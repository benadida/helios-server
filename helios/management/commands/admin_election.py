"""
verify cast votes that have not yet been verified

Ben Adida
ben@adida.net
2010-05-22
"""
import csv, datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from helios import utils as helios_utils
from helios.models import *

def p(key, val):
  print "%s\t:\t %s" % (key, val)

def pt(title, lvl=0):
  lvl_str = ["=", "-", "*"][lvl]
  head_rpt = 5
  print "\n" * (1-lvl)
  print lvl_str*head_rpt + (" %s " % title) + lvl_str*head_rpt

class Command(BaseCommand):
    args = ''
    help = 'Show elections info'

    def handle(self, *args, **options):
      if not args:
        for e in Election.objects.all():
          p(e.name, e.uuid)

        return

      e = Election.objects.get(uuid=args[0])
      pt("Election info")
      p("Name", e.name)
      p("UUID", e.uuid)
      p("Faculty", e.faculty.name)

      pt("Admins")
      for a in e.admins.filter():
        p(a.info['name'], a.user_id)

      pt("Trustees info")
      for t in e.trustee_set.filter():
        pt(t.name, 2)
        p("Name", t.name)
        p("Email", t.email)
        p("Secret", t.secret)
        p("URL", t.get_login_url())
        if "dispostable" in t.email:
          p("AccessEmail", "http://www.dispostable.com/inbox/%s/" % t.email.split("@")[0])

      if len(args) > 1 and args[1] == "1":
        pt("Voters info")
        for v in e.voter_set.all():
          if "dispostable" in v.voter_email:
            p(v.voter_email, "http://www.dispostable.com/inbox/%s/" % v.voter_email.split("@")[0])
          else:
            p("Email", v.voter_email)

          print v.get_quick_login_url()
          print
