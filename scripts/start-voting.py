"""Supervise HTTP and database verifiers in one container.

Votes and jobs live in PostgreSQL, never in these child processes. If a child
dies, fail the container so its host restarts the whole service and recovers jobs.
"""
import os
import signal
import subprocess
import sys
import time


def positive_count(name, default, maximum):
    value = int(os.environ.get(name, str(default)))
    if not 1 <= value <= maximum:
        raise ValueError(f'{name} must be between 1 and {maximum}.')
    return value


def main():
    children = []
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    web_count = positive_count('WEB_CONCURRENCY', 2, 32)
    verifier_count = positive_count('VOTE_VERIFIER_CONCURRENCY', 2, 16)
    port = int(os.environ.get('PORT', '10000'))
    if not 1 <= port <= 65535:
        raise ValueError('PORT must be a valid TCP port.')
    commands = [[sys.executable, '-m', 'gunicorn',
        os.environ.get('VOTING_WSGI_MODULE', 'wsgi:application'),
        '--bind', f'0.0.0.0:{port}', '--workers', str(web_count),
        '--worker-class', 'sync', '--timeout', '180', '--error-logfile', '-']]
    commands.extend([[sys.executable, 'manage.py', 'run_vote_verifier']
                     for _ in range(verifier_count)])
    commands.append([sys.executable, 'manage.py', 'run_vote_confirmation_sender'])
    exit_code = 0
    try:
        for command in commands:
            children.append(subprocess.Popen(command, start_new_session=True))
        while not stopping:
            if any(child.poll() is not None for child in children):
                print('Voting subprocess exited; restarting the service is required.',
                      file=sys.stderr, flush=True)
                exit_code = 1
                break
            time.sleep(0.25)
    finally:
        for child in children:
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        deadline = time.monotonic() + 30
        for child in children:
            try:
                child.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
