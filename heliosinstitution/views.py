from view_utils import *


def home(request):
    pass


def manage_users(request):
  if request.method == "GET":
    return render_template(request, "manage_users")
