import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

from config import config
from globals import  GlobalState
from signup import Signup, Interrupted
from verify_email import verify_email


def main():
    email_worker = threading.Thread(target=verify_email)
    email_worker.start()

    max_threads = config['signupWorkerNum']
    task_queue = Queue(max_threads)
    executor = ThreadPoolExecutor(max_threads)
    def worker(q, executor):
        while True:
            task = q.get()
            executor.submit(task)

    worker_thread = threading.Thread(target=worker, args=(task_queue, executor))
    worker_thread.start()

    def signup():
        s = Signup()
        s.sign_up()

    while True:
        if GlobalState.exception :
             raise GlobalState.exception
        task_queue.put(signup)

if __name__ == '__main__':
    main()