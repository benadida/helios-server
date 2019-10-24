"""
Exception handler hook for RQ (http://python-rq.org/)

How to use: 

1. Instead of using the default "rqworker" script to run the worker, write your own short script
as shown in this example: 
https://github.com/nvie/rq/blob/master/examples/run_worker.py

2. In this script, initialize rollbar with `handler='blocking'`, for example:

rollbar.init('your access token', 'production', handler='blocking')

3. After constructing the worker but before calling `.work()`, add
`rollbar.contrib.rq.exception_handler` as an exception handler.

Full example:

```
import rollbar
from rq import Connection, Queue, Worker

if __name__ == '__main__':
    rollbar.init('your_access_token', 'production', handler='blocking')
    with Connection():
        q = Queue()
        worker = Worker(q)
        worker.push_exc_handler(rollbar.contrib.rq.exception_handler)
        worker.work()
```
"""

import rollbar


def exception_handler(job, *exc_info):
    """
    Called by RQ when there is a failure in a worker.

    NOTE: Make sure that in your RQ worker process, rollbar.init() has been called with
    handler='blocking'. The default handler, 'thread', does not work from inside an RQ worker.
    """
    # Report data about the job with the exception.
    job_info = job.to_dict()
    # job_info['data'] is the pickled representation of the job, and doesn't json-serialize well.
    # repr() works nicely.
    job_info['data'] = repr(job_info['data'])

    extra_data = {'job': job_info}
    payload_data = {'framework': 'rq'}
    
    rollbar.report_exc_info(exc_info, extra_data=extra_data, payload_data=payload_data)

    # continue to the next handler
    return True
