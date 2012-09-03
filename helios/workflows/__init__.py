"""
Helios Election Workflows
"""

from helios.datatypes import LDObjectContainer

class WorkflowObject(LDObjectContainer):
    pass
 

def get_datatype(workflow_type, datatype_name):
    return get_workflow_module(workflow_type)[datatype_name]

def get_workflow_module(workflow_type):

  if workflow_type == "homomorphic":
    from helios.workflows import homomorphic
    return homomorphic

  if workflow_type == "mixnet":
    from helios.workflows import mixnet
    return mixnet

  raise Exception("Invalid workflow '%s'" % workflow_type)
