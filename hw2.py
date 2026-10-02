import os
import sys
import signal

jobs = {}
next_job_number = 1


def reap_background_jobs():
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)

            if pid == 0:
                break

            for job_number, job in jobs.items():
                if job["pid"] == pid:
                    if os.WIFEXITED(status):
                        job["status"] = "Done"
                    elif os.WIFSIGNALED(status):
                        job["status"] = "Terminated"
                    break

        except ChildProcessError:
            break


def show_jobs():
    reap_background_jobs()

    finished_jobs = []

    for job_number, job in jobs.items():
        print(
            f"[{job_number}] "
            f"{job['status']} "
            f"PID {job['pid']} "
            f"{job['command']}"
        )

        if job["status"] in ("Done", "Terminated"):
            finished_jobs.append(job_number)

    for job_number in finished_jobs:
        del jobs[job_number]


def bring_to_foreground(job_number):
    if job_number not in jobs:
        print("No such job")
        return

    job = jobs[job_number]

    print(job["command"])

    try:
        os.waitpid(job["pid"], 0)
    except ChildProcessError:
        pass

    del jobs[job_number]


def kill_job(job_number):
    if job_number not in jobs:
        print("No such job")
        return

    job = jobs[job_number]

    try:
        os.kill(job["pid"], signal.SIGTERM)
        os.waitpid(job["pid"], 0)
        print(f"[{job_number}] Terminated {job['command']}")

    except ProcessLookupError:
        print("Process already finished")

    except ChildProcessError:
        pass

    del jobs[job_number]


def run_external_command(args, command_text, background):
    global next_job_number

    pid = os.fork()

    if pid == 0:
        try:
            os.execvp(args[0], args)

        except FileNotFoundError:
            print(
                f"{args[0]}: command not found",
                file=sys.stderr,
                flush=True
            )
            os._exit(1)

        except OSError as error:
            print(
                f"Error executing command: {error}",
                file=sys.stderr,
                flush=True
            )
            os._exit(1)

    else:
        if background:
            job_number = next_job_number
            next_job_number += 1

            jobs[job_number] = {
                "pid": pid,
                "command": command_text,
                "status": "Running"
            }

            print(f"[{job_number}] {pid} {command_text}")

        else:
            os.waitpid(pid, 0)


def main():
    while True:
        reap_background_jobs()

        try:
            line = input("myshell> ")

        except EOFError:
            print()
            break

        line = line.strip()

        if not line:
            continue

        background = False

        if line.endswith("&"):
            background = True
            line = line[:-1].strip()

        if not line:
            continue

        args = line.split()
        command = args[0]

        if command == "exit":
            break

        elif command == "cd":
            try:
                if len(args) == 1:
                    os.chdir(os.environ["HOME"])
                else:
                    os.chdir(args[1])

            except OSError as error:
                print(f"cd: {error}")

        elif command == "jobs":
            show_jobs()

        elif command == "fg":
            if len(args) != 2:
                print("Usage: fg <job number>")
                continue

            try:
                job_number = int(args[1])
                bring_to_foreground(job_number)

            except ValueError:
                print("Invalid job number")

        elif command == "kill":
            if len(args) != 2:
                print("Usage: kill <job number>")
                continue

            try:
                job_number = int(args[1])
                kill_job(job_number)

            except ValueError:
                print("Invalid job number")

        else:
            run_external_command(args, line, background)


if __name__ == "__main__":
    main()
