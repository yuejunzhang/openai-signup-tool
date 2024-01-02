import threading

from config import config
from globals import  GlobalState
from signup import Signup
from pool_manager import ThreadPoolManager
from verify_email import verify_email



def main():
    email_worker = threading.Thread(target=verify_email)
    email_worker.start()

    max_threads = config['signupWorkerNum']

    pm = ThreadPoolManager(max_threads)


    def signup():

        s = Signup()
        s.sign_up()

    while True:
        if GlobalState.exception :
             raise GlobalState.exception
        pm.add_task(signup)

if __name__ == '__main__':
    main()