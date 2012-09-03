from helios.workflows.homomorphic import Tally as HomomorphicTally
from helios.workflows.homomorphic import *

TYPE = 'mixnet'

class Tally(HomomorphicTally):

  @property
  def datatype(self):
    return "legacy/MixedTally"
