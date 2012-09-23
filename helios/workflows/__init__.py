"""
Helios Election Workflows
"""

from helios.datatypes import LDObjectContainer


class WorkflowObject(LDObjectContainer):

    inject_params = True

    def __init__(self, *args, **kwargs):
        return super(WorkflowObject, self).__init__(self, *args,  **kwargs)

    def __new__(cls, *args, **kwargs):
        workflow = kwargs.pop('workflow', None)
        newcls = cls
        if workflow:
            datatype_name = cls.__name__.split(".")[-1]
            newcls = get_datatype(workflow, datatype_name)

        return object.__new__(newcls, *args, **kwargs)


def get_datatype(workflow_type, datatype_name):
    return getattr(get_workflow_module(workflow_type), datatype_name)


def get_workflow_module(workflow_type):

  if workflow_type == "homomorphic":
    from helios.workflows import homomorphic
    return homomorphic

  if workflow_type == "mixnet":
    from helios.workflows import mixnet
    return mixnet

  raise Exception("Invalid workflow '%s'" % workflow_type)


